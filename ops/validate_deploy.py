"""Measure, inject an isolated failure, deploy, and retain 30s of observations."""
import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
import traceback
import uuid
from pathlib import Path
from deploy import Deployment
from monitor import PATHS, request, utc
from report import create, read_rows

ROOT=Path(__file__).resolve().parents[1]

def run(args,out):
    result=subprocess.run(args,cwd=ROOT,capture_output=True,encoding='utf-8',errors='replace',timeout=600)
    with Path(out).open('a',encoding='utf-8') as f:
        f.write(f'[{utc()}] {args[0]}\n{result.stdout}{result.stderr}\n')
    if result.returncode:raise RuntimeError(f'Command failed ({result.returncode}): {args[0]}: {result.stderr[-1000:]}')
    return result.stdout

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--image',required=True);ap.add_argument('--sha',required=True)
    ap.add_argument('--out',required=True);args=ap.parse_args()
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    for name in ['stop','ready']:
        (out/name).unlink(missing_ok=True)
    result={'status':'failed','started_at':utc(),'expected_version':args.sha}
    prod=Deployment('bonchorok',8000,out/'production')
    sandbox=Deployment('bonchorok-test-'+uuid.uuid4().hex[:8],18080,out/'sandbox')
    monitor_log=(out/'monitor-process.log').open('w',encoding='utf-8')
    proc=subprocess.Popen([sys.executable,str(ROOT/'ops/monitor.py'),'--out',str(out/'monitor.jsonl'),
        '--stop',str(out/'stop'),'--ready',str(out/'ready')],stdout=monitor_log,stderr=monitor_log)
    completion=None
    try:
        for _ in range(100):
            if proc.poll() is not None:raise RuntimeError('Independent monitor exited before readiness')
            if (out/'ready').exists():break
            time.sleep(.1)
        else:raise RuntimeError('Independent monitor did not record all endpoints')
        result['monitor_ready_at']=(out/'ready').read_text(encoding='utf-8')
        initial=prod.info(prod.proxy)
        if not initial:raise RuntimeError('Existing service required for a measured before/after comparison')
        if initial['Config'].get('Labels',{}).get('io.bonchorok.role')=='proxy':
            config=prod.docker('exec',prod.proxy,'cat','/etc/nginx/nginx.conf')
            old_name=re.search(r'upstream app \{ server ([a-z0-9-]+):8000;',config)[1]
            old=prod.info(old_name)
        else:old=initial
        old_image=old['Image']
        result['before_image_id']=old_image
        result['before_observed_version']=request('http://127.0.0.1:8000','/api/health')['version']
        prod.docker('pull',args.image)
        prod.docker('pull','nginx:1.28-alpine')
        new_image=prod.docker('image','inspect','--format','{{.Id}}',args.image)
        environment={'at':utc(),'os':platform.platform(),'python':platform.python_version(),
            'node':run(['node','--version'],out/'tools.log').strip(),'docker':prod.docker('version'),
            'docker_info':prod.docker('info'),'before_image':old_image,'after_image':new_image,
            'scenario':'ABAB batches 10, fresh contexts, 1440x1000, ko-KR, 2 CPU/1GiB per backend',
            'data_policy':'Compare JSON.stringify canonical browser fingerprints; whitespace is not data'}
        (out/'environment.json').write_text(json.dumps(environment,ensure_ascii=False,indent=2),encoding='utf-8')
        sandbox.ensure_network()
        before=sandbox.deploy(old_image,result['before_observed_version'])
        if not before['ok']:raise RuntimeError('Cannot prepare benchmark baseline')
        old_backend=before['new_backend']
        new_backend=sandbox.backend(new_image,uuid.uuid4().hex[:12])
        sandbox.wait_backend(new_backend,args.sha)
        for phase,backend in [('before',old_backend),('after',new_backend),('before',old_backend),('after',new_backend)]:
            sandbox.switch(sandbox.config(backend))
            sandbox.wait_route(args.sha if phase=='after' else result['before_observed_version'])
            time.sleep(1)
            run(['node',str(ROOT/'ops/browser/measure.cjs'),'http://127.0.0.1:18080',str(out/'browser.jsonl'),phase,'10'],out/'browser-process.log')
            for _ in range(10):
                for path in PATHS:
                    row=request('http://127.0.0.1:18080',path);row['phase']=phase
                    with (out/'performance-http.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
        fingerprints={r.get('data_sha256') for r in read_rows(out/'browser.jsonl') if r.get('ok')}
        if len(fingerprints)!=1:raise RuntimeError('Before/after dataset mismatch')
        sandbox.switch(sandbox.config(old_backend));sandbox.wait_route(result['before_observed_version'])
        config_before=sandbox.docker('exec',sandbox.proxy,'cat','/etc/nginx/nginx.conf')
        failure=sandbox.deploy(new_image,args.sha,fault=True)
        recovered=request('http://127.0.0.1:18080','/api/health')
        failure['verified']=not failure['ok'] and failure.get('rollback_ok') and recovered['ok'] and recovered['version']==result['before_observed_version'] and config_before==sandbox.docker('exec',sandbox.proxy,'cat','/etc/nginx/nginx.conf')
        result['rollback']=failure
        if not failure['verified']:raise RuntimeError('Isolated post-switch failure recovery was not verified')
        if proc.poll() is not None:raise RuntimeError('Monitor is not running; production change refused')
        result['deployment']=prod.deploy(new_image,args.sha)
        completion=time.monotonic();result['deployment_finished_at']=utc()
        if not result['deployment']['ok']:raise RuntimeError('Production deployment failed; see rollback events')
        # Real service browser functional verification, kept separate from perf samples.
        run(['node',str(ROOT/'ops/browser/measure.cjs'),'http://127.0.0.1:8000',str(out/'production-browser.jsonl'),'production','1'],out/'browser-process.log')
        result['status']='success'
    except Exception as exc:
        result['error']=str(exc)
        (out/'failure.log').write_text(traceback.format_exc(),encoding='utf-8')
        if result.get('deployment',{}).get('ok'):
            try:
                prod.restore(result['deployment'])
                result['postcheck_rollback_ok']=True
            except Exception as restore_exc:
                result['postcheck_rollback_ok']=False
                result['postcheck_rollback_error']=str(restore_exc)
        completion=time.monotonic();result['deployment_finished_at']=utc()
    finally:
        # Even a failed deployment remains independently observed for at least 30s.
        completion=completion or time.monotonic()
        result.setdefault('deployment_finished_at',utc())
        while time.monotonic()-completion<30:time.sleep(.25)
        result['post_observation_seconds']=round(time.monotonic()-completion,3)
        result['monitor_alive_at_end']=proc.poll() is None
        (out/'stop').write_text(utc(),encoding='utf-8')
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10)
        result['monitor_exit']=proc.returncode
        monitor_log.close()
        if not result['monitor_alive_at_end'] or proc.returncode!=0:result['status']='failed';result['monitor_coverage']='unverified'
        result['finished_at']=utc()
        (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        try:sandbox.cleanup_sandbox()
        except Exception as exc:(out/'cleanup-error.log').write_text(str(exc),encoding='utf-8')
        for name in prod.docker('ps','-a','--filter','label=io.bonchorok.managed=true','--format','{{.Names}}',check=False).splitlines():
            prod.docker('logs','--tail','100',name,check=False)
        create(out)
    return 0 if result['status']=='success' else 1

if __name__=='__main__':
    sys.exit(main())
