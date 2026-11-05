import datetime as dt
import json
import math
from pathlib import Path

def read_rows(path):
    rows=[]
    if Path(path).exists():
        for line in Path(path).read_text(encoding='utf-8').splitlines():
            try:rows.append(json.loads(line))
            except json.JSONDecodeError:rows.append({'ok':False,'error':'incomplete JSONL record'})
    return rows

def percentile(values,p):
    if not values:return None
    values=sorted(values)
    return round(values[max(0,math.ceil(len(values)*p)-1)],3)

def stats(rows,key):
    values=[r[key] for r in rows if r.get('ok') and isinstance(r.get(key),(int,float))]
    failed=sum(not r.get('ok',False) for r in rows)
    return {'samples':len(rows),'valid_timings':len(values),'p50_ms':percentile(values,.5),
            'p95_ms':percentile(values,.95),'failed':failed,'failure_rate':failed/len(rows) if rows else None}

def create(out):
    out=Path(out)
    monitor=read_rows(out/'monitor.jsonl')
    browser=read_rows(out/'browser.jsonl')
    http=read_rows(out/'performance-http.jsonl')
    events=read_rows(out/'production/events.jsonl')
    result=json.loads((out/'result.json').read_text(encoding='utf-8')) if (out/'result.json').exists() else {}
    metrics={}
    for phase in ['before','after']:
        b=[r for r in browser if r.get('phase')==phase]
        metrics[phase]={'initial_ready':stats(b,'initial_ready_ms'),'search':stats(b,'search_ms'),
                        'http':{p:stats([r for r in http if r.get('phase')==phase and r.get('path')==p],'elapsed_ms') for p in sorted({r.get('path','') for r in http})}}
    gaps={}
    for path in sorted({r.get('path','unknown') for r in monitor}):
        rows=sorted([r for r in monitor if r.get('path')==path],key=lambda r:r.get('started_ns',0))
        gaps[path]={**stats(rows,'elapsed_ms'),
            'first_start':rows[0].get('started_at') if rows else None,
            'last_end':rows[-1].get('ended_at') if rows else None,
            'actual_interval_p50_ms':percentile([r['actual_start_interval_ms'] for r in rows if r.get('actual_start_interval_ms') is not None],.5),
            'max_start_interval_ms':max([r.get('actual_start_interval_ms') or 0 for r in rows],default=None),
            'max_unobserved_gap_ms':max([r.get('unobserved_gap_ms') or 0 for r in rows],default=None),
            'missed_interval_count':sum((r.get('actual_start_interval_ms') or 0)>750 for r in rows)}
        finished=result.get('deployment_finished_at')
        if finished and rows:
            tail=(dt.datetime.fromisoformat(rows[-1]['ended_at'])-dt.datetime.fromisoformat(finished)).total_seconds()
            gaps[path]['last_sample_seconds_after_deployment']=round(tail,3)
            gaps[path]['unverified_tail_ms']=round(max(0,result.get('post_observation_seconds',0)-tail)*1000,3)
    transitions=[]
    for row in sorted([r for r in monitor if r.get('path')=='/api/health' and r.get('ok')],key=lambda r:r['started_ns']):
        version=row.get('version')
        if not transitions or transitions[-1]['version']!=version:
            transitions.append({'at':row['ended_at'],'version':version})
    fingerprints={r.get('data_sha256') for r in browser if r.get('ok')}
    complete_comparison=all(sum(r.get('phase')==phase and r.get('ok',False) for r in browser)==20 for phase in ['before','after'])
    record_times=sorted(r.get('recorded_ns',r.get('ended_ns',0)) for r in monitor if r.get('ended_ns'))
    max_record_gap=max([(b-a)/1e6 for a,b in zip(record_times,record_times[1:])],default=None)
    report={'metrics':metrics,'monitor':gaps,'version_transitions':transitions,'data_identical':len(fingerprints)==1 if complete_comparison else None,
            'data_fingerprints':sorted(x for x in fingerprints if x),'result':result,
            'failed_monitor_requests':sum(not r.get('ok',False) for r in monitor),'monitor_samples':len(monitor),
            'max_record_gap_ms':max_record_gap,
            'limits':['Sampling cannot prove continuous availability. Every gap between completed request and next start is unverified.',
                      'Timeouts and scheduling delays enlarge actual sample intervals; no synthetic observations are inserted.',
                      'Legacy responses without SHA are unknown, not inferred from image tags.',
                      'Cold browser contexts, same Chromium/data/proxy/CPU limits and alternating batches; OS cache and unrelated host load are uncontrolled.',
                      'Initial-ready timing includes browser automation round trips and a two-frame UI readiness check; search is input-to-two-animation-frames, not raw CPU duration.',
                      'p95 uses nearest rank; planned 20 samples per phase, actual counts are reported. Exploratory local benchmark, not a production load test.',
                      'First listener migration can interrupt access. nginx reload reduces subsequent listener gaps but zero downtime is not claimed.',
                      'Forced runner/machine termination can prevent final upload or 30-second observation; missing evidence must be treated as unverified.']}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 본초록 배포 검증','',f"결과: **{result.get('status','검증되지 않음')}** · 모니터 요청 {len(monitor)}건 · 실패 {report['failed_monitor_requests']}건",
           f"복구 시험: **{result.get('rollback',{}).get('verified',False)}** · 동일 데이터: **{report['data_identical']}**",
           f"배포 후 관측: {result.get('post_observation_seconds','미확인')}초 · 모니터 종료 코드: {result.get('monitor_exit','미확인')}",'',
           f"브라우저 표본 전/후: {metrics['before']['initial_ready']['samples']} / {metrics['after']['initial_ready']['samples']} · 전체 로그 최대 기록 공백: {max_record_gap} ms",'',
           '| 지표 (ms) | 변경 전 p50 / p95 | 변경 후 p50 / p95 | 실패율 전 / 후 |','|---|---:|---:|---:|']
    pairs=[('초기 로딩 → UI 준비','initial_ready'),('검색 입력 → 화면 갱신','search')]
    for title,key in pairs:
        a,b=metrics['before'][key],metrics['after'][key]
        lines.append(f"| {title} | {a['p50_ms']} / {a['p95_ms']} | {b['p50_ms']} / {b['p95_ms']} | {a['failure_rate']} / {b['failure_rate']} |")
    for p in metrics['before']['http']:
        a,b=metrics['before']['http'][p],metrics['after']['http'][p]
        lines.append(f"| HTTP {p} | {a['p50_ms']} / {a['p95_ms']} | {b['p50_ms']} / {b['p95_ms']} | {a['failure_rate']} / {b['failure_rate']} |")
    lines+=['','**관측된 응답 버전 전환**']+[f"- {t['at']}: `{t['version'] or 'unknown (SHA 없는 기존 응답)'}`" for t in transitions]
    lines+=['','| 모니터 경로 | 실제 간격 p50 / 최대 (ms) | 최대 미관측 공백 (ms) | 실패 |','|---|---:|---:|---:|']
    for p,g in gaps.items():
        lines.append(f"| {p} | {g['actual_interval_p50_ms']} / {g['max_start_interval_ms']} | {g['max_unobserved_gap_ms']} | {g['failed']} |")
    lines+=['','**검증 한계:** 요청 사이의 모든 구간은 미관측이며 무중단을 증명하지 않습니다. 기존 SHA 없는 응답은 버전 미확인입니다. 동일 데이터·Chromium·프록시·CPU 제한으로 전후 각 20회 교차 측정하되 OS 캐시와 외부 부하는 통제하지 못했습니다. 초기 로딩은 자동화 왕복과 UI 준비 조건을 포함하고, 검색은 두 프레임 대기까지 포함합니다. 성능 향상은 표의 측정값으로만 판단하세요. 원본 타임스탬프·오류·환경·복구 이벤트는 Artifacts에 있습니다.']
    (out/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return report

if __name__=='__main__':
    import sys
    create(sys.argv[1])
