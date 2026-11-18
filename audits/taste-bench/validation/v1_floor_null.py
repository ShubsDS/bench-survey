"""V1, V3, V4: null for the construction-aware floor rule; fair comparison with models; split check."""
import csv
from collections import defaultdict

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v_common import AUD, CELLS, SEED, average, features, load, save, summaries

rows = load()
F = features(rows)
cell = np.array([f["cell"] for f in F])
task = np.array([f["task"] for f in F])
y = np.array([1 if f["ans"] == 1 else -1 for f in F])
N = {c: int((cell == c).sum()) for c in CELLS}
FIXED = {"parallel_engineering": 1, "parallel_research": 1, "detour_engineering": -1, "detour_research": -1}
rng = np.random.default_rng(SEED)


def dvec(name):
    return np.array([f[name][1] - f[name][0] for f in F])


def acc(d, yy, sign, mask):
    s = d[mask] * yy[mask] * sign
    return float((s > 0).mean()) if mask.any() else float("nan")


def split_tasks():
    test = np.zeros(len(F), bool)
    for c in CELLS:
        ts = np.unique(task[cell == c])
        rng.shuffle(ts)
        held = set(ts[: len(ts) // 2])
        test |= (cell == c) & np.isin(task, list(held))
    return test


def heldout_average(d, yy, test, fitted=True):
    accs, ns = {}, {}
    for c in CELLS:
        tr = (cell == c) & ~test
        te = (cell == c) & test
        if fitted:
            sign = 1 if acc(d, yy, 1, tr) >= acc(d, yy, -1, tr) else -1
        else:
            sign = FIXED[c]
        accs[c] = acc(d, yy, sign, te)
        ns[c] = int(te.sum())
    return average(accs, ns)[0]


out = {"n_by_cell": N}
for name in ("cont", "ground"):
    d = dvec(name)
    full = {c: {"higher": round(acc(d, y, 1, cell == c), 4), "lower": round(acc(d, y, -1, cell == c), 4),
                "ties": int(((d == 0) & (cell == c)).sum())} for c in CELLS}
    fixed_full = average({c: acc(d, y, FIXED[c], cell == c) for c in CELLS}, N)[0]
    real_fit, real_fix = [], []
    for _ in range(1000):
        te = split_tasks()
        real_fit.append(heldout_average(d, y, te, True))
        real_fix.append(heldout_average(d, y, te, False))
    plac_fit, plac_fix, flip_fit, flip_fix = [], [], [], []
    for _ in range(1000):
        te = split_tasks()
        dp = d.copy()
        for c in CELLS:
            idx = np.where(cell == c)[0]
            dp[idx] = d[rng.permutation(idx)]
        plac_fit.append(heldout_average(dp, y, te, True))
        plac_fix.append(heldout_average(dp, y, te, False))
        flips = {t: rng.random() < 0.5 for t in np.unique(task)}
        yf = y * np.array([-1 if flips[t] else 1 for t in task])
        flip_fit.append(heldout_average(d, yf, te, True))
        flip_fix.append(heldout_average(d, yf, te, False))

    def q(a):
        a = np.array(a) * 100
        return {"median": round(float(np.median(a)), 1), "p2.5": round(float(np.percentile(a, 2.5)), 1),
                "p97.5": round(float(np.percentile(a, 97.5)), 1), "p99": round(float(np.percentile(a, 99)), 1),
                "max": round(float(a.max()), 1)}

    def pct(v, a):
        return round(float((np.array(a) * 100 >= v).mean()), 4)

    med_real = float(np.median(real_fit)) * 100
    out[name] = {
        "full_set_by_cell": full,
        "full_set_fixed_sign_average": round(fixed_full * 100, 1),
        "real_heldout_fitted_signs": q(real_fit),
        "real_heldout_fixed_signs": q(real_fix),
        "placebo_feature_fitted_signs": q(plac_fit),
        "placebo_feature_fixed_signs": q(plac_fix),
        "task_flip_fitted_signs": q(flip_fit),
        "task_flip_fixed_signs": q(flip_fix),
        "share_null_ge_61.4": {"placebo_fitted": pct(61.4, plac_fit), "flip_fitted": pct(61.4, flip_fit),
                                "placebo_fixed": pct(61.4, plac_fix), "flip_fixed": pct(61.4, flip_fix)},
        "share_null_ge_real_median": {"placebo_fitted": pct(med_real, plac_fit), "flip_fitted": pct(med_real, flip_fit)},
    }

# V3: single-order and paired Averages of published models
S = summaries()
models = {}
for m, s in S.items():
    pc = s["per_cell"]
    nn = {c: pc[c]["seeded"]["n"] for c in CELLS}
    single = average({c: pc[c]["two_order_mean_accuracy"] for c in CELLS}, nn)[0] * 100
    paired = average({c: pc[c]["both_correct_rate"] for c in CELLS}, nn)[0] * 100
    parsed_single = average({c: (pc[c]["seeded"]["correct"] + pc[c]["reversed"]["correct"]) /
                             max(1, pc[c]["seeded"]["parsed"] + pc[c]["reversed"]["parsed"]) for c in CELLS}, nn)[0] * 100
    models[m] = {"paired_average": round(paired, 1), "single_order_average": round(single, 1),
                 "single_order_average_parsed_only": round(parsed_single, 1)}
out["models"] = models
for thr in (60.4, 61.4):
    out[f"models_single_order_above_{thr}"] = sorted(m for m, v in models.items() if v["single_order_average"] > thr)
    out[f"models_paired_above_{thr}"] = sorted(m for m, v in models.items() if v["paired_average"] > thr)

# V4: does the auditor's held-out split separate tasks?
fp = AUD / "data/features.csv"
with fp.open() as fh:
    rd = list(csv.DictReader(fh))
cols = list(rd[0].keys())
out["auditor_features_columns"] = cols
halfcol = [c for c in cols if "half" in c.lower() or "split" in c.lower() or "held" in c.lower()]
out["auditor_half_columns"] = halfcol
if halfcol:
    hc = halfcol[0]
    tid = {f["id"]: f["task"] for f in F}
    by_task = defaultdict(set)
    for r in rd:
        by_task[(r.get("cell"), tid.get(r["id"], r.get("task_id")))].add(r[hc])
    out["tasks_in_both_halves"] = sum(len(v) > 1 for v in by_task.values())
    out["tasks_total"] = len(by_task)
    out["heldout_n_by_cell"] = {c: sum(1 for r in rd if r.get("cell") == c and r[hc] in ("2", "1", "test", "True"))
                               for c in CELLS}
save("v1_floor_null.json", out)
print(json_dump := __import__("json").dumps(out, indent=1)[:6000])
