"""Windows/Linux Docker blue-green deployment with a stable nginx listener."""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path
from monitor import request, utc

LABEL = 'io.bonchorok.managed=true'

class Deployment:
    def __init__(self, prefix, port, out):
        self.prefix, self.port, self.out = prefix, port, Path(out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.proxy = prefix + '-local'
        self.network = prefix + '-net'
        self.events = self.out / 'events.jsonl'
        self.log = self.out / 'docker.log'

    def event(self, kind, **data):
        with self.events.open('a', encoding='utf-8') as f:
            f.write(json.dumps(dict(at=utc(), monotonic_ns=time.perf_counter_ns(), event=kind, **data), ensure_ascii=False)+'\n')

    def docker(self, *args, check=True):
        p = subprocess.run(['docker', *map(str,args)], capture_output=True, encoding='utf-8', errors='replace', timeout=300)
        with self.log.open('a', encoding='utf-8') as f:
            f.write(f'[{utc()}] docker {" ".join(map(str,args))}\n{p.stdout}{p.stderr}\n')
        if check and p.returncode:
            raise RuntimeError(f'docker {args[0]} exited {p.returncode}: {p.stderr[-1500:]}')
        return p.stdout.strip()

    def info(self, name):
        result = self.docker('inspect', name, check=False)
        items = json.loads(result) if result else []
        return items[0] if items else None

    def managed(self, name):
        info = self.info(name)
        if info and info['Config'].get('Labels',{}).get('io.bonchorok.managed')!='true':
            raise RuntimeError('Refusing to modify unmanaged container '+name)
        return info

    def ensure_network(self):
        if self.network not in self.docker('network','ls','--format','{{.Name}}').splitlines():
            self.docker('network','create',self.network)

    def backend(self, image, suffix):
        name = self.prefix+'-app-'+suffix
        self.docker('run','-d','--name',name,'--label',LABEL,'--label','io.bonchorok.role=backend',
                    '--restart','unless-stopped','--cpus','2','--memory','1g','--network',self.network,'-p','127.0.0.1::8000',image)
        return name

    def check(self, base, version=None):
        rows = [request(base,p) for p in ['/api/health','/?herb=sophorae-flos','/herbs.json','/app-v2.js']]
        for row in rows:
            with (self.out/'checks.jsonl').open('a',encoding='utf-8') as f:
                f.write(json.dumps(row,ensure_ascii=False)+'\n')
        if not all(r['ok'] for r in rows):
            raise RuntimeError('HTTP/content check failed at '+base)
        if version and any(r['version']!=version for r in rows):
            raise RuntimeError('Response deployment version mismatch at '+base)
        return rows

    def wait_backend(self, name, version=None):
        for _ in range(60):
            info=self.info(name)
            if not info or not info['State']['Running']:
                raise RuntimeError('Backend is not running: '+name)
            port=info['NetworkSettings']['Ports']['8000/tcp'][0]['HostPort']
            row=request('http://127.0.0.1:'+port,'/api/health')
            if row['ok'] and (not version or row['version']==version):
                self.check('http://127.0.0.1:'+port,version)
                self.event('candidate_validated',container=name,version=row['version'])
                return
            time.sleep(1)
        raise RuntimeError('Backend readiness timeout')

    def config(self, backend):
        if not re.fullmatch(r'[a-z0-9-]+',backend):
            raise ValueError('Invalid backend name')
        return '''worker_processes auto;
pid /var/run/nginx.pid;
error_log /dev/stderr notice;
events { worker_connections 1024; }
http {
 include /etc/nginx/mime.types;
 access_log /dev/stdout;
 upstream app { server BACKEND:8000; keepalive 32; }
 server {
  listen 8000;
  location / {
   proxy_pass http://app;
   proxy_http_version 1.1;
   proxy_set_header Connection "";
   proxy_set_header Host $host;
   proxy_connect_timeout 2s;
   proxy_read_timeout 10s;
  }
 }
}
'''.replace('BACKEND',backend)

    def copy_config(self, container, text, destination='/etc/nginx/nginx.conf'):
        path=self.out/('nginx-'+uuid.uuid4().hex+'.conf')
        path.write_text(text,encoding='utf-8')
        self.docker('cp',str(path.resolve()),container+':'+destination)

    def switch(self, text):
        self.copy_config(self.proxy,text,'/etc/nginx/nginx.next.conf')
        self.docker('exec',self.proxy,'nginx','-t','-c','/etc/nginx/nginx.next.conf')
        self.docker('exec',self.proxy,'mv','/etc/nginx/nginx.next.conf','/etc/nginx/nginx.conf')
        self.docker('exec',self.proxy,'nginx','-s','reload')

    def wait_route(self, version=None):
        last=None
        for _ in range(30):
            try:
                rows=self.check('http://127.0.0.1:'+str(self.port),version)
                if rows[0]['version'] != version:
                    raise RuntimeError('Old nginx worker still served the preceding version')
                return
            except Exception as exc:
                last=exc;time.sleep(.25)
        raise last

    def deploy(self, image, version, fault=False):
        # Fault injection is restricted to an isolated namespace and port.
        if fault and (not self.prefix.startswith('bonchorok-test-') or self.port==8000):
            raise ValueError('Fault injection is forbidden on production')
        self.ensure_network()
        previous=self.managed(self.proxy)
        old_config=None
        if previous and previous['Config'].get('Labels',{}).get('io.bonchorok.role')=='proxy':
            old_config=self.docker('exec',self.proxy,'cat','/etc/nginx/nginx.conf')
        old_version=request('http://127.0.0.1:'+str(self.port),'/api/health')['version'] if previous else None
        new=self.backend(image,uuid.uuid4().hex[:12])
        legacy=self.prefix+'-legacy-'+uuid.uuid4().hex[:8]
        pending=self.prefix+'-pending-'+uuid.uuid4().hex[:8]
        switched=False
        renamed=False
        legacy_stopped=False
        self.event('deploy_started',version=version,old_version=old_version,image=image)
        try:
            self.wait_backend(new,version)
            config=self.config(new)
            if old_config:
                self.event('traffic_switch_started',version=version,method='nginx_graceful_reload')
                switched=True
                self.switch(config)
            else:
                # Only the first migration needs to transfer ownership of port 8000.
                self.docker('create','--name',pending,'--network',self.network,'--label',LABEL,
                            '--label','io.bonchorok.role=proxy','--restart','unless-stopped',
                            '--health-cmd','wget -q -O - http://127.0.0.1:8000/api/health || exit 1',
                            '--health-interval','5s','--health-timeout','4s','--health-retries','3',
                            '-p',f'127.0.0.1:{self.port}:8000','nginx:1.28-alpine')
                self.copy_config(pending,config)
                self.event('traffic_switch_started',version=version,method='initial_listener_migration',uninterrupted=False)
                if previous:
                    self.docker('stop','--time','10',self.proxy)
                    legacy_stopped=True
                    self.docker('rename',self.proxy,legacy);renamed=True
                self.docker('rename',pending,self.proxy);switched=True
                self.docker('start',self.proxy)
            self.wait_route(version)
            self.event('traffic_switch_observed',version=version)
            if fault:
                # Simulate a backend crash AFTER live traffic has moved in the sandbox.
                self.docker('stop','--time','1',new)
                self.check('http://127.0.0.1:'+str(self.port),version)
                raise RuntimeError('Fault injection did not cause expected failure')
            self.event('deployment_completed',version=version)
            # Keep the previous backend available for reload drain/rollback.
            return dict(ok=True,version=version,previous_version=old_version,new_backend=new,
                        proxy=self.proxy,completed_at=utc(),legacy=legacy if renamed else None,
                        previous_config=old_config)
        except Exception as exc:
            self.event('deployment_failed',error=str(exc))
            rollback=False
            try:
                if old_config and switched:
                    self.switch(old_config);self.wait_route(old_version);rollback=True
                elif renamed:
                    if switched:self.docker('rm','-f',self.proxy,check=False)
                    self.docker('rename',legacy,self.proxy)
                    self.docker('start',self.proxy)
                    self.wait_route(old_version);rollback=True
                elif switched:
                    self.docker('rm','-f',self.proxy,check=False)
                elif previous and legacy_stopped:
                    self.docker('start',self.proxy)
                    self.wait_route(old_version);rollback=True
                self.event('rollback_completed',ok=rollback,version=old_version)
            except Exception as rollback_exc:
                self.event('rollback_failed',error=str(rollback_exc))
            for container in [new,self.proxy]:
                self.docker('logs','--tail','100',container,check=False)
            if rollback or not switched:self.docker('rm','-f',new,check=False)
            self.docker('rm','-f',pending,check=False)
            return dict(ok=False,error=str(exc),rollback_ok=rollback,previous_version=old_version,completed_at=utc())

    def restore(self, deployed):
        if deployed.get('previous_config'):
            self.switch(deployed['previous_config'])
        elif deployed.get('legacy'):
            self.docker('rm','-f',self.proxy)
            self.docker('rename',deployed['legacy'],self.proxy)
            self.docker('start',self.proxy)
        else:
            raise RuntimeError('No preceding service available to restore')
        self.wait_route(deployed['previous_version'])
        self.event('postcheck_rollback_completed',version=deployed['previous_version'])

    def cleanup_sandbox(self):
        if not self.prefix.startswith('bonchorok-test-'):
            raise ValueError('Only isolated validation environments can be cleaned')
        names=self.docker('ps','-a','--filter','label='+LABEL,'--format','{{.Names}}').splitlines()
        for name in names:
            if name.startswith(self.prefix+'-'):self.docker('rm','-f',name,check=False)
        self.docker('network','rm',self.network,check=False)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--image',required=True);ap.add_argument('--sha',required=True)
    ap.add_argument('--out',required=True);args=ap.parse_args()
    d=Deployment('bonchorok',8000,args.out)
    result=d.deploy(args.image,args.sha)
    (Path(args.out)/'deployment.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    sys.exit(0 if result['ok'] else 1)
