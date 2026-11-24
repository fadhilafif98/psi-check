"""Run PageSpeed Insights API v5 (mobile + desktop) for detailed metrics & issues.

Usage: python psi_api.py <urls_file> <raw_dir> [--key-file /path/to/key] [--workers 6]
API key: $PSI_API_KEY, or --key-file.
Saves one slim JSON per url+strategy into raw_dir (resumable: files with data are skipped, errors are retried).
"""
import argparse, gzip, hashlib, http.client, json, os, sys, threading, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
API_HOST = 'www.googleapis.com'
API_PATH = '/pagespeedonline/v5/runPagespeed'
# Partial response: skips fullPageScreenshot, i18n, categories, stackPacks... (fields wildcards are not supported)
FIELDS = 'loadingExperience,lighthouseResult(finalUrl,finalDisplayedUrl,runtimeError,audits)'
# Per-audit keys kept on disk (drops "details": screenshots/thumbnails are ~80% of the payload)
KEEP = ('title', 'score', 'scoreDisplayMode', 'numericValue', 'displayValue')
ATTEMPTS = 4


def raw_path(raw_dir, url, strategy):
    return os.path.join(raw_dir, hashlib.md5((url + strategy).encode(), usedforsecurity=False).hexdigest() + '.json')


def read_json(fn):
    try:
        with open(fn) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def write_json(fn, obj):
    tmp = fn + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(obj, f, separators=(',', ':'))
    os.replace(tmp, fn)  # atomic: an interrupted run never leaves a half-written file


def slim(d):
    lr = d.get('lighthouseResult') or {}
    lr['audits'] = {k: {f: v[f] for f in KEEP if f in v} for k, v in (lr.get('audits') or {}).items()}
    return d


class ApiHttpError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


def fetch(url, strat, key):
    q = urllib.parse.urlencode({'url': url, 'strategy': strat, 'category': 'performance', 'fields': FIELDS})
    conn = http.client.HTTPSConnection(API_HOST, timeout=180)
    try:
        conn.request('GET', f'{API_PATH}?{q}', headers={'Accept-Encoding': 'gzip', 'X-Goog-Api-Key': key})
        r = conn.getresponse()
        body = r.read()
        if r.getheader('Content-Encoding') == 'gzip':
            body = gzip.decompress(body)
        if r.status >= 400:
            try:
                msg = f'HTTP {r.status}: ' + json.loads(body)['error']['message']
            except Exception:
                msg = f'HTTP {r.status}'
            raise ApiHttpError(r.status, msg)
        return json.loads(body)
    finally:
        conn.close()


def resolve_api_key(key_file):
    if os.environ.get('PSI_API_KEY'):
        return os.environ['PSI_API_KEY'].strip()
    if key_file and os.path.isfile(key_file):
        key = open(key_file).read().strip()
        if key:
            return key
    raise SystemExit('API key missing: set PSI_API_KEY or pass --key-file')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('urls')
    ap.add_argument('raw_dir')
    ap.add_argument('--key-file', default=None)
    ap.add_argument('--workers', type=int, default=6)
    a = ap.parse_args()
    key = resolve_api_key(a.key_file)
    os.makedirs(a.raw_dir, exist_ok=True)
    with open(a.urls) as f:
        urls = list(dict.fromkeys(l.strip() for l in f if l.strip()))

    jobs = [(u, s) for u in urls for s in ('mobile', 'desktop')]
    todo = [j for j in jobs if 'data' not in (read_json(raw_path(a.raw_dir, *j)) or {})]
    print(f'{len(todo)} API calls to run, {len(jobs) - len(todo)} already done', flush=True)
    abort = threading.Event()
    stats, lock = {'ok': 0, 'fail': 0}, threading.Lock()

    def count(k):
        with lock:
            stats[k] += 1

    def run(job):
        url, strat = job
        if abort.is_set():
            return
        err = ''
        for attempt in range(1, ATTEMPTS + 1):
            try:
                d = fetch(url, strat, key)
                write_json(raw_path(a.raw_dir, url, strat), {'url': url, 'strategy': strat, 'data': slim(d)})
                count('ok')
                print('ok', strat, url, flush=True)
                return
            except ApiHttpError as e:
                err = str(e)
                if e.code in (401, 403):  # bad key / API disabled / quota: no point continuing
                    abort.set()
                    print('ABORT', err, flush=True)
                    return
                if e.code == 400:  # invalid URL etc.: retrying won't help
                    break
                wait = 30 * attempt if e.code == 429 else 5 * attempt
            except Exception as e:  # network error / timeout
                err, wait = str(e), 5 * attempt
            if attempt < ATTEMPTS:
                time.sleep(wait)
        write_json(raw_path(a.raw_dir, url, strat), {'url': url, 'strategy': strat, 'error': err})
        count('fail')
        print('FAIL', strat, url, err, flush=True)

    with ThreadPoolExecutor(max(1, a.workers)) as ex:
        list(ex.map(run, todo))
    print(f"API done: {stats['ok']} ok, {stats['fail']} failed", flush=True)
    sys.exit(1 if abort.is_set() else 0)


if __name__ == '__main__':
    main()
