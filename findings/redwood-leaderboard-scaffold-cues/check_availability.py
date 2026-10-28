"""Lead 0: which sources behind the Redwood Control Leaderboard's imported datasets can be downloaded
without an account, and what share of the monitor rankings rests on the ones that cannot.
Probes status codes only (no redirect followed, no body read). Writes availability_checks.json."""
import json, sys, http.client, urllib.parse, hashlib, datetime
API = sys.argv[1]; OUT = sys.argv[2]
HOSTS = ['data.linuxarena.ai', 'equistamp.linuxarena.ai']

def status(host, path):
    try:
        c = http.client.HTTPSConnection(host, timeout=30)
        c.request('HEAD', path, headers={'User-Agent': 'audit-probe'})
        r = c.getresponse(); s = r.status; c.close()
        if s == 405:  # HEAD not allowed: fall back to GET without reading the body
            c = http.client.HTTPSConnection(host, timeout=30)
            c.request('GET', path, headers={'User-Agent': 'audit-probe', 'Range': 'bytes=0-0'})
            r = c.getresponse(); s = r.status; c.close()
        return s
    except Exception as e:
        return f'error:{type(e).__name__}'

cat = json.load(open(API + '/../../data_catalog.json'))
mon = json.load(open(API + '/monitors.json'))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
out = {'probed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
       'pins': {'data_catalog.json': sha(API + '/../../data_catalog.json'), 'monitors.json': sha(API + '/monitors.json'),
                'monitors_generated_at': mon['generated_at']},
       'datasets': {}}
for dsid, d in mon['datasets'].items():
    runs = {'honest_raw': (d.get('honest_eval') or {}).get('run_id'), 'attack_raw': (d.get('attack_eval') or {}).get('run_id'),
            'honest_monitored': d.get('honest_monitor_run_id'), 'attack_monitored': d.get('attack_monitor_run_id')}
    linked_host = {}
    for l in d.get('source_links', []):
        u = urllib.parse.urlparse(l['url'])
        if u.netloc in HOSTS: linked_host[u.path.rstrip('/').split('/')[-1]] = u.netloc
    res = {}
    for role, rid in runs.items():
        if not rid: continue
        st = {h: status(h, f'/api/runs/{rid}/eval') for h in HOSTS}
        res[role] = {'run_id': rid, 'status': st, 'public_download': any(v in (200, 206, 302) for v in st.values())}
    cat_entry = next((c for c in cat['datasets'] if c['id'] == dsid), None)
    out['datasets'][dsid] = {'visibility_field': d.get('visibility'), 'catalog_withheld': (cat_entry or {}).get('withheld_populations'),
                             'catalog_files': len((cat_entry or {}).get('files', [])), 'runs': res,
                             'n_honest': d.get('honest_trajectories'), 'n_attack': d.get('attack_trajectories')}
# share of ranking rows
rows = mon['rows']
def ok(ds, role): return out['datasets'][ds]['runs'].get(role, {}).get('public_download', False)
summary = {}
for r in rows:
    ds = r['dataset']; s = summary.setdefault(ds, {'rows': 0})
    s['rows'] += 1
tot_rows = len(rows)
blocked_raw = [ds for ds in summary if not (ok(ds, 'honest_raw') and ok(ds, 'attack_raw'))]
blocked_scores = [ds for ds in summary if not (ok(ds, 'honest_monitored') and ok(ds, 'attack_monitored'))]
traj = {ds: out['datasets'][ds]['n_honest'] + out['datasets'][ds]['n_attack'] for ds in summary}
# distinct trajectories: the two LinuxArena sets share one honest run
distinct_total = sum(traj.values()) - out['datasets']['linuxarena-paper-strategies']['n_honest']
out['ranking_share'] = {
    'rows_total': tot_rows, 'rows_per_dataset': {k: v['rows'] for k, v in summary.items()},
    'datasets_with_a_raw_run_not_public': blocked_raw,
    'rows_on_those': sum(summary[d]['rows'] for d in blocked_raw),
    'datasets_with_a_monitored_run_not_public': blocked_scores,
    'rows_on_those_monitored': sum(summary[d]['rows'] for d in blocked_scores),
    'datasets_fully_unverifiable': [d for d in blocked_raw if d in blocked_scores],
    'rows_fully_unverifiable': sum(summary[d]['rows'] for d in blocked_raw if d in blocked_scores),
    'equal_weight_share_note': 'The board gives each selected dataset equal weight, so in any pooled selection a blocked dataset counts 1/k of the score regardless of its size.',
}
# raw attack runs not public, by trajectories
blk_attack = [d for d in summary if not ok(d, 'attack_raw')]
out['ranking_share']['attack_trajectories_total'] = sum(out['datasets'][d]['n_attack'] for d in summary)
out['ranking_share']['attack_trajectories_raw_not_public'] = sum(out['datasets'][d]['n_attack'] for d in blk_attack)
json.dump(out, open(OUT, 'w'), indent=1)
for k, v in out['datasets'].items():
    print(k, v['visibility_field'], {r: (x['status'], x['public_download']) for r, x in v['runs'].items()})
print(json.dumps(out['ranking_share'], indent=1))
