"""Lead 3: how the Redwood Control Leaderboard's monitor board combines datasets, what each dataset's
positive class is, and how far monitor rankings move when a dataset is dropped or when only attacks
with a recorded side-task success are kept. Uses only the board's own published JSON
(monitors.json, monitor-plots/pooled.json), which carries per-trajectory monitor scores.
Writes pooling_checks.json."""
import json, sys, hashlib, itertools, collections
import numpy as np
API = sys.argv[1]; OUT = sys.argv[2]
rng = np.random.default_rng(0)
NBOOT = 1000
mon = json.load(open(API + '/monitors.json'))
pool = json.load(open(API + '/monitor-plots_pooled.json'))['combos']
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
fp2ds = {r['traj_fingerprint']: r['dataset'] for r in mon['rows']}
ROWS = {(r['dataset'], r['monitor_kind'], r['monitor'], r['monitor_variant']): r for r in mon['rows']}

def score(s, kind):
    if kind == 'trajectory': return s['trajectory']
    a = [x for x in (s['actions'] or []) if x is not None]
    return max(a) if a else None  # "peak suspicion"

def auc(h, a):
    h = np.sort(np.asarray(h, float)); a = np.asarray(a, float)
    lo = np.searchsorted(h, a, 'left'); hi = np.searchsorted(h, a, 'right')
    return float((lo + 0.5 * (hi - lo)).sum() / (len(h) * len(a)))

def table(ds, kind, monitors, keep_attack=None):
    """Score matrix over the trajectories every listed monitor scored (the board's 'same scored trajectories')."""
    out = {}
    for cls in ('honest', 'attack'):
        per = []
        for (m, v) in monitors:
            r = ROWS[(ds, kind, m, v)]
            per.append({s['trajectory_id']: (score(s, kind), s['side_task_success']) for s in r['score_samples'][cls]})
        ids = set.intersection(*[{k for k, x in p.items() if x[0] is not None} for p in per])
        if cls == 'attack' and keep_attack is not None:
            ids = {i for i in ids if keep_attack(per[0][i][1])}
        ids = sorted(ids)
        out[cls] = np.array([[p[i][0] for p in per] for i in ids], float).reshape(len(ids), len(monitors))
    return out

def board_auc(tabs):
    """Mean over datasets of per-dataset AUROC, for each monitor column."""
    return np.mean([[auc(t['honest'][:, j], t['attack'][:, j]) for j in range(t['honest'].shape[1])] for t in tabs], axis=0)

def boot(tabs):
    res = []
    for _ in range(NBOOT):
        bt = []
        for t in tabs:
            bt.append({c: t[c][rng.integers(0, len(t[c]), len(t[c]))] for c in ('honest', 'attack')})
        res.append(board_auc(bt))
    return np.array(res)

def kendall(x, y):
    n = len(x); c = d = 0
    for i, j in itertools.combinations(range(n), 2):
        s = np.sign(x[i] - x[j]) * np.sign(y[i] - y[j])
        c += s > 0; d += s < 0
    return float((c - d) / (n * (n - 1) / 2))

def compare(name, monitors, kind, base_sets, alt_sets):
    """base_sets / alt_sets: list of (dataset, keep_attack)"""
    tb = [table(ds, kind, monitors, k) for ds, k in base_sets]
    ta = [table(ds, kind, monitors, k) for ds, k in alt_sets]
    A = board_auc(tb); B = board_auc(ta)
    bb = boot(tb); ba = boot(ta)
    labels = [v for _, v in monitors]
    flips = []; resolved = 0
    for i, j in itertools.combinations(range(len(labels)), 2):
        if np.sign(A[i] - A[j]) * np.sign(B[i] - B[j]) < 0:
            # a flip is 'resolved' if the paired bootstrap interval of the difference excludes 0 under either definition
            ci_a = np.percentile(bb[:, i] - bb[:, j], [2.5, 97.5]); ci_b = np.percentile(ba[:, i] - ba[:, j], [2.5, 97.5])
            res = bool((ci_a[0] > 0 or ci_a[1] < 0) or (ci_b[0] > 0 or ci_b[1] < 0))
            resolved += res
            flips.append({'pair': [labels[i], labels[j]], 'base': [round(A[i], 4), round(A[j], 4)], 'alt': [round(B[i], 4), round(B[j], 4)], 'resolved_by_bootstrap': res})
    rank = lambda v: [labels[k] for k in np.argsort(-v)]
    return {'comparison': name, 'kind': kind, 'n_monitors': len(labels),
            'base': [ds + ('' if k is None else ' (success only)') for ds, k in base_sets],
            'alt': [ds + ('' if k is None else ' (success only)') for ds, k in alt_sets],
            'n_traj_base': [[len(t['honest']), len(t['attack'])] for t in tb], 'n_traj_alt': [[len(t['honest']), len(t['attack'])] for t in ta],
            'auroc_base': dict(zip(labels, np.round(A, 4).tolist())), 'auroc_alt': dict(zip(labels, np.round(B, 4).tolist())),
            'top_base': rank(A)[0], 'top_alt': rank(B)[0], 'rank_base': rank(A), 'rank_alt': rank(B),
            'kendall_tau': round(kendall(A, B), 3), 'max_abs_auroc_change': round(float(np.max(np.abs(A - B))), 4),
            'pairs_flipped': len(flips), 'pairs_total': len(labels) * (len(labels) - 1) // 2,
            'flips_resolved_by_bootstrap': resolved, 'flips': flips}

out = {'pins': {'monitors.json_sha256': sha(API + '/monitors.json'), 'pooled.json_sha256': sha(API + '/monitor-plots_pooled.json'),
                'generated_at': mon['generated_at'], 'default_dataset': mon['default_dataset']}}

# 1. reproduce the board's AUROC: single datasets and pooled selections
repro = []
for combo, v in pool.items():
    dss = [fp2ds[f] for f in combo.split(' + ')]
    for kind in ('action', 'trajectory'):
        prs = [p for p in v['rows'] if p['monitor_kind'] == kind]
        if not prs: continue
        mons = [(p['monitor'], p['monitor_variant']) for p in prs]
        tabs = [table(ds, kind, mons) for ds in dss]
        mean_auc = board_auc(tabs)
        # alternative: one pooled AUROC over concatenated trajectories
        H = np.concatenate([t['honest'] for t in tabs]); Aa = np.concatenate([t['attack'] for t in tabs])
        cat_auc = [auc(H[:, j], Aa[:, j]) for j in range(len(mons))]
        for p, m1, m2 in zip(prs, mean_auc, cat_auc):
            repro.append({'datasets': dss, 'kind': kind, 'monitor': p['monitor_variant'], 'published': p['auroc'], 'mean_of_dataset_aurocs': m1, 'concatenated': m2})
single = [r for r in repro if len(r['datasets']) == 1]
multi = [r for r in repro if len(r['datasets']) > 1]
out['aggregation'] = {
    'rule_stated_on_page': 'AUROC column tooltip: "Selected datasets have equal weight." Board note: ranking metrics "use the same scored trajectories for every monitor of a given type, including unsuccessful attacks, and give each dataset equal weight. Stepwise monitors use peak suspicion".',
    'default_view': 'one dataset (default_dataset = %s); several datasets are pooled only when a viewer selects them' % mon['default_dataset'],
    'n_single_rows': len(single), 'single_max_abs_err': max(abs(r['published'] - r['mean_of_dataset_aurocs']) for r in single),
    'n_pooled_rows': len(multi),
    'pooled_max_abs_err_mean_rule': max(abs(r['published'] - r['mean_of_dataset_aurocs']) for r in multi),
    'pooled_max_abs_err_concatenation_rule': max(abs(r['published'] - r['concatenated']) for r in multi),
    'poolable_selections': sorted({' + '.join(r['datasets']) + ' [' + r['kind'] + ']' for r in multi}),
    'selections_with_no_shared_monitor': sorted(' + '.join(fp2ds[f] for f in k.split(' + ')) for k, v in pool.items() if not v['rows']),
}
# 2. positive class per dataset
pos = {}
for ds in mon['datasets']:
    rr = [r for r in mon['rows'] if r['dataset'] == ds]
    if not rr: pos[ds] = {'rows': 0}; continue
    a = rr[0]['score_samples']['attack']
    pos[ds] = {'author': mon['datasets'][ds]['author_label'], 'n_attack_in_scores': len(a),
               'side_task_success': {str(k): v for k, v in collections.Counter(s['side_task_success'] for s in a).items()},
               'monitor_kinds': sorted({r['monitor_kind'] + '/' + r['monitor'] for r in rr})}
out['positive_class'] = pos

succ = lambda x: x == 1.0
cmp = []
# 3a. three-dataset action pool (the only pool spanning three label definitions)
m3 = [('simple', v) for v in ('gpt-4.1-nano-none', 'gpt-5-nano-minimal', 'gpt-5.4-nano-none')]
full3 = [('basharena', None), ('monitoringbench', None), ('sleight', None)]
for drop in range(3):
    cmp.append(compare('bash+mb+sleight drop ' + full3[drop][0], m3, 'action', full3, [x for k, x in enumerate(full3) if k != drop]))
cmp.append(compare('bash+mb+sleight -> success-only positives (SLEIGHT has no outcome, so it drops out)', m3, 'action', full3, [('basharena', succ), ('monitoringbench', succ)]))
# 3b. bash + sleight, 10 shared monitors
m10 = [('simple', v) for v in ('gpt-4o-mini-none', 'gpt-4.1-nano-none', 'gpt-5-nano-minimal', 'glm-4.6-none', 'claude-haiku-4-5-none', 'deepseek-v3.2-none', 'gpt-5.4-nano-none', 'gpt-5.4-nano-low', 'gpt-5.4-nano-medium', 'gpt-5.4-nano-high')]
cmp.append(compare('bash+sleight vs bash alone', m10, 'action', [('basharena', None), ('sleight', None)], [('basharena', None)]))
cmp.append(compare('bash+sleight vs sleight alone', m10, 'action', [('basharena', None), ('sleight', None)], [('sleight', None)]))
cmp.append(compare('bash+sleight vs bash success-only', m10, 'action', [('basharena', None), ('sleight', None)], [('basharena', succ)]))
cmp.append(compare('bash all attacks vs success-only', m10, 'action', [('basharena', None)], [('basharena', succ)]))
# 3c. SHADE (MRT) alone: its attacks carry an outcome on the board
mS = [('trajectory', v) for v in ('gpt-4o-mini-none', 'gpt-4.1-nano-none', 'gpt-5-nano-minimal', 'glm-4.6-none', 'claude-haiku-4-5-none', 'deepseek-v3.2-none', 'gpt-5.4-nano-none', 'gpt-5.4-nano-low', 'gpt-5.4-nano-medium', 'gpt-5.4-nano-high')]
cmp.append(compare('shade all attacks vs success-only', mS, 'trajectory', [('shade-arena', None)], [('shade-arena', succ)]))
# 3d. LinuxArena pair
for kind, prefix in (('action', 'mean-action'), ('trajectory', 'mean-quick')):
    pr = [p for p in pool['411e7f303b51 + d34d3e2c3a50']['rows'] if p['monitor_kind'] == kind]
    ms = [(p['monitor'], p['monitor_variant']) for p in pr]
    both = [('linuxarena-paper', None), ('linuxarena-paper-strategies', None)]
    cmp.append(compare('linuxarena pair drop strategies [' + kind + ']', ms, kind, both, both[:1]))
    cmp.append(compare('linuxarena pair drop paper [' + kind + ']', ms, kind, both, both[1:]))
    cmp.append(compare('linuxarena pair success-only [' + kind + ']', ms, kind, both, [(d, succ) for d, _ in both]))
out['rank_sensitivity'] = cmp
json.dump(out, open(OUT, 'w'), indent=1, default=float)
print(json.dumps(out['aggregation'], indent=1, default=float))
print(json.dumps(out['positive_class'], indent=1))
for c in cmp:
    print(f"{c['comparison']:<75} tau {c['kendall_tau']:+.3f} flips {c['pairs_flipped']}/{c['pairs_total']} resolved {c['flips_resolved_by_bootstrap']} top {c['top_base']} -> {c['top_alt']} maxdAUC {c['max_abs_auroc_change']}")
