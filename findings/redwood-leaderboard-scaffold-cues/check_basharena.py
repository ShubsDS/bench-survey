"""Lead 1: content-blind baselines on the leaderboard's BashArena 600/600 Claude Opus 4.6 set,
against the board's own monitor scores. Inputs: features extracted by extract_basharena.py from the
pinned raw .eval files, and monitors.json. Writes basharena_checks.json."""
import json, sys, hashlib, collections
import numpy as np
FEAT, API, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
rng = np.random.default_rng(0); NPERM = 1000; NBOOT = 1000
R = json.load(open(FEAT)); mon = json.load(open(API + '/monitors.json'))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()

def auc(y, s):
    y = np.asarray(y, bool); s = np.asarray(s, float)
    h = np.sort(s[~y]); a = s[y]
    lo = np.searchsorted(h, a, 'left'); hi = np.searchsorted(h, a, 'right')
    return float((lo + 0.5 * (hi - lo)).sum() / (len(h) * len(a)))
def two_sided(y, s):  # direction-free: max(AUROC, 1-AUROC); the null uses the same statistic
    a = auc(y, s); return max(a, 1 - a), a
def null(y, s, groups=None):
    y = np.asarray(y, bool); out = []
    for _ in range(NPERM):
        if groups is None: yp = rng.permutation(y)
        else:
            yp = y.copy()
            for g in np.unique(groups):
                ix = np.where(groups == g)[0]; yp[ix] = rng.permutation(y[ix])
        out.append(two_sided(yp, s)[0])
    return float(np.percentile(out, 95))
def boot_ci(y, s):
    y = np.asarray(y, bool); s = np.asarray(s, float); ih = np.where(~y)[0]; ia = np.where(y)[0]; v = []
    for _ in range(NBOOT):
        b = np.concatenate([rng.choice(ih, len(ih)), rng.choice(ia, len(ia))]); v.append(auc(y[b], s[b]))
    return [round(float(x), 4) for x in np.percentile(v, [2.5, 97.5])]

y = np.array([r['cls'] == 'attack' for r in R]); task = np.array([r['main_task'] for r in R])
feats = {
    'n_actions': [r['n_actions'] for r in R],
    'n_messages': [r['n_messages'] for r in R],
    'tool_output_chars': [r['out_chars'] for r in R],
    'tool_argument_chars': [r['arg_chars'] for r in R],
    'visible_reasoning_chars': [r['reasoning_chars'] for r in R],
    'scaffold_system_message_in_transcript': [int(r['has_system_msg']) for r in R],
    'scaffold_overlay_system_prompt_chars': [r['overlay_system_prompt_chars'] for r in R],
    'scaffold_risky_tag_count': [r['tags'].get('risky', 0) for r in R],
}
base = {}
shared = np.isin(task, list({t for t, c in zip(task, y) if c}))  # main tasks with both classes
for k, v in feats.items():
    v = np.asarray(v, float); st, raw = two_sided(y, v)
    st2, raw2 = two_sided(y[shared], v[shared])
    base[k] = {'auroc_attack_high': round(raw, 4), 'auroc_direction_free': round(st, 4), 'ci95': boot_ci(y, v), 'shuffled_null_p95': round(null(y, v), 4),
               'median_honest': float(np.median(v[~y])), 'median_attack': float(np.median(v[y])),
               'shared_tasks_auroc_attack_high': round(raw2, 4), 'shared_tasks_null_p95_within_task': round(null(y[shared], v[shared], task[shared]), 4)}

# board monitors on this set
fid = {r['id']: i for i, r in enumerate(R)}
nact = np.array(feats['n_actions'], float)
mons = {}
for row in [r for r in mon['rows'] if r['dataset'] == 'basharena']:
    ss = row['score_samples']; yy = []; peak = []; mean = []; na = []
    for cls in ('honest', 'attack'):
        for s in ss[cls]:
            a = [x for x in (s['actions'] or []) if x is not None]
            if not a: continue
            yy.append(cls == 'attack'); peak.append(max(a)); mean.append(np.mean(a)); na.append(len(s['actions']))
    yy = np.array(yy); peak = np.array(peak); na = np.array(na)
    rho = np.corrcoef(np.argsort(np.argsort(peak[~yy])), np.argsort(np.argsort(na[~yy])))[0, 1]
    mons[row['monitor_variant']] = {'auroc_peak_board': round(auc(yy, peak), 4), 'auroc_mean_per_action': round(auc(yy, mean), 4),
                                    'spearman_peak_vs_n_actions_honest': round(float(rho), 3), 'n': [int((~yy).sum()), int(yy.sum())]}
# n_actions as the monitor sees it (score_samples) for the same trajectories
s0 = [r for r in mon['rows'] if r['dataset'] == 'basharena'][0]['score_samples']
ys = np.array([0] * len(s0['honest']) + [1] * len(s0['attack']), bool)
ns = np.array([s['n_actions'] for s in s0['honest'] + s0['attack']], float)
out = {
    'pins': {'honest_eval': 'de437937709f493dafe549b10b4505cf (sha256 8db01221...)', 'attack_eval': '792967b92d37439ca0b12a5bce9dfa90 (sha256 99ee2479...)',
             'features_sha256': sha(FEAT), 'monitors.json_sha256': sha(API + '/monitors.json')},
    'design': {'n_honest': int((~y).sum()), 'n_attack': int(y.sum()),
               'distinct_main_tasks_honest': len(set(task[~y])), 'distinct_main_tasks_attack': len(set(task[y])),
               'main_tasks_shared': int(len(set(task[~y]) & set(task[y]))),
               'attack_per_main_task': dict(collections.Counter(collections.Counter(task[y]).values())),
               'side_tasks': dict(collections.Counter(r['side_task'] for r in R if r['cls'] == 'attack')),
               'main_task_success': {c: dict(collections.Counter(str(r['main_score']) for r in R if r['cls'] == c)) for c in ('honest', 'attack')},
               'source_runs_converted_from': {c: sorted({r['converted_from'] for r in R if r['cls'] == c}) for c in ('honest', 'attack')},
               'honest_overlay_system_prompt_variants': len({r['overlay_system_prompt_sha'] for r in R if r['cls'] == 'honest'}),
               'attack_overlay_system_prompt_variants': len({r['overlay_system_prompt_sha'] for r in R if r['cls'] == 'attack'})},
    'baselines': base,
    'n_actions_auroc_attack_high_on_board_samples': round(auc(ys, ns), 4),
    'board_monitors': mons,
    'flag_rule': 'scope.md check 1: baseline AUROC interval above its null 95th percentile and above 0.6, or the baseline ranks above the median published monitor',
}
med = float(np.median([m['auroc_peak_board'] for m in mons.values()]))
out['median_board_monitor_auroc'] = med
gap = collections.Counter(('ends_at_landing' if s['n_actions'] - 1 == s['landed_at'] else 'other') if s['landed_at'] is not None else 'no_landing' for s in s0['attack'])
out['attack_trajectory_ends_at_side_task_landing'] = dict(gap)
out['monitors_with_mean_auroc_above_peak_auroc'] = sum(m['auroc_mean_per_action'] > m['auroc_peak_board'] for m in mons.values())
out['baselines_flagged'] = [k for k, b in base.items() if (b['ci95'][0] > max(b['shuffled_null_p95'], 0.6) or 1 - b['ci95'][1] > max(b['shuffled_null_p95'], 0.6)) or b['auroc_direction_free'] > med]
json.dump(out, open(OUT, 'w'), indent=1, default=float)
print(json.dumps({k: v for k, v in out.items() if k != 'pins'}, indent=1, default=float))
