"""Independent HTTP sampler. UTF-8 JSONL is flushed after every observation."""
import argparse
import concurrent.futures
import datetime as dt
import gzip
import hashlib
import json
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

PATHS = ['/api/health', '/?herb=sophorae-flos', '/herbs.json', '/app-v2.js']

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='microseconds')

def request(base, path, timeout=4):
    start, start_ns = utc(), time.perf_counter_ns()
    result = dict(path=path, started_at=start, started_ns=start_ns, status=None,
                  valid=False, version=None, error=None)
    try:
        req = urllib.request.Request(base + path, headers={'Accept-Encoding': 'gzip', 'Connection': 'close'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read()
            result['status'] = response.status
            result['wire_bytes'] = len(body)
            result['encoding'] = response.headers.get('Content-Encoding', 'identity')
            result['version'] = response.headers.get('X-Deployment-SHA')
            if result['encoding'] == 'gzip':
                body = gzip.decompress(body)
            result['body_sha256'] = hashlib.sha256(body).hexdigest()
            if path == '/api/health':
                data = json.loads(body)
                result['version'] = data.get('deployment_sha') or result['version']
                result['valid'] = data.get('status') == 'ok' and data.get('herb_count') == 601
            elif path == '/herbs.json':
                data = json.loads(body)
                result['valid'] = len(data) == 601 and any(r['id'] == 'sophorae-flos' for r in data)
            elif path.startswith('/?'):
                result['valid'] = b'app-v2.js' in body and b'details.js' in body
            else:
                result['valid'] = b'bonchorok-bookmarks' in body
    except urllib.error.HTTPError as exc:
        result['status'] = exc.code
        result['error'] = str(exc)
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    result['ended_ns'] = time.perf_counter_ns()
    result['ended_at'] = utc()
    result['elapsed_ms'] = (result['ended_ns'] - start_ns) / 1e6
    result['ok'] = result['status'] == 200 and result['valid']
    result['version_evidence'] = 'response' if result['version'] else 'unavailable'
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://127.0.0.1:8000')
    ap.add_argument('--out', required=True)
    ap.add_argument('--stop', required=True)
    ap.add_argument('--interval', type=float, default=0.5)
    ap.add_argument('--ready', required=True)
    ap.add_argument('--max-seconds', type=float, default=7200)
    args = ap.parse_args()
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    begun = time.monotonic()
    seen = set()
    with target.open('a', encoding='utf-8', buffering=1) as log:
        def worker(path):
            previous_start = previous_end = None
            while not Path(args.stop).exists() and time.monotonic() - begun < args.max_seconds:
                row = request(args.base, path)
                row['target_interval_ms'] = args.interval * 1000
                row['actual_start_interval_ms'] = None if previous_start is None else (row['started_ns']-previous_start)/1e6
                row['unobserved_gap_ms'] = None if previous_end is None else max(0, (row['started_ns']-previous_end)/1e6)
                row['gap_verified'] = False
                previous_start, previous_end = row['started_ns'], row['ended_ns']
                with lock:
                    log.write(json.dumps(row, ensure_ascii=False) + '\n')
                    log.flush()
                    seen.add(path)
                    if len(seen) == len(PATHS):
                        Path(args.ready).write_text(utc(), encoding='utf-8')
                # No fabricated samples for missed deadlines; actual interval is recorded.
                remaining = args.interval - (time.perf_counter_ns()-row['started_ns'])/1e9
                if remaining > 0:
                    time.sleep(remaining)
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(PATHS)) as pool:
            list(pool.map(worker, PATHS))

if __name__ == '__main__':
    main()
