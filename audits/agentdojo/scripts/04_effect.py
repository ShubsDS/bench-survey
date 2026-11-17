"""Effect test (prereg.md): ASR conditional on exposure, ability and follow; ranking, trend, defences.

Run: data/.venv/bin/python -I scripts/04_effect.py
Writes results/per_model.csv, results/defences.csv, results/pairs.csv and the 'effect' block of results.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr

from common import DEFENCES, MODELS, RESULTS, ROOT, load, load_injection_as_user

B = 2000
SEED = 0
PIPES = MODELS + DEFENCES

att = load()
att = att[att.pipeline.isin(PIPES)].copy()
none = load("none")
none = none[none.pipeline.isin(PIPES)].copy()
ab = load_injection_as_user()
ab = ab[ab.pipeline.isin(PIPES)]
ability = {(r.pipeline, r.it): bool(r.utility) for r in ab.itertuples()}
att["able"] = [ability.get((p, i), np.nan) for p, i in zip(att.pipeline, att.it)]
assert att.able.notna().all(), "missing ability runs"
att["able"] = att.able.astype(bool)
att["reached"] = att.exposed | (att.redacted > 0)
att["follow"] = att.follow_exec.astype(bool)
att["sec_noerr"] = att.security & ~att.error

# case grid aligned across pipelines
grid = att[att.pipeline == PIPES[0]][["ut", "it"]].sort_values(["ut", "it"]).reset_index(drop=True)
key = grid.ut + "|" + grid.it
pos = {k: i for i, k in enumerate(key)}
N = len(grid)
P = len(PIPES)


def mat(col):
    M = np.full((P, N), np.nan)
    for pi, p in enumerate(PIPES):
        sub = att[att.pipeline == p]
        idx = [pos[u + "|" + i] for u, i in zip(sub.ut, sub.it)]
        M[pi, idx] = sub[col].astype(float).values
    assert not np.isnan(M).any(), col
    return M


SEC, EXP, ABLE, FOL, REACH, SNE = (mat(c) for c in ["security", "exposed", "able", "follow", "reached", "sec_noerr"])
grid_ut = grid.ut.values
grid_it = grid.it.values
uts = np.unique(grid_ut)
its = np.unique(grid_it)
ut_idx = np.searchsorted(uts, grid_ut)
it_idx = np.searchsorted(its, grid_it)

none_ut = sorted(none.ut.unique())
assert len(none_ut) == 97
UM = np.full((P, 97), np.nan)
for pi, p in enumerate(PIPES):
    sub = none[none.pipeline == p].set_index("ut").utility
    UM[pi] = sub.reindex(none_ut).astype(float).values
assert not np.isnan(UM).any()
none_ut_idx = np.searchsorted(uts, np.array(none_ut))


def stats(w_case, w_ut):
    """Per-pipeline statistics under case weights w_case (N,) and user-task weights (97,)."""
    def cm(num, den):
        d = (den * w_case).sum(1)
        with np.errstate(invalid="ignore", divide="ignore"):
            return (num * den * w_case).sum(1) / d
    one = np.ones_like(SEC)
    return dict(
        S0=cm(SEC, one), S1=cm(SEC, EXP), S2=cm(SEC, EXP * ABLE), S3=cm(FOL, EXP), S4=cm(SNE, one),
        E=cm(EXP, one), R=cm(REACH, one), S1R=cm(SEC, REACH), F0=cm(FOL, one),
        U=(UM * w_ut).sum(1) / w_ut.sum(),
    )


point = stats(np.ones(N), np.ones(97))
rng = np.random.default_rng(SEED)
draws = {k: [] for k in point}
for b in range(B):
    cu = np.bincount(rng.integers(0, len(uts), len(uts)), minlength=len(uts))
    ci_ = np.bincount(rng.integers(0, len(its), len(its)), minlength=len(its))
    w = cu[ut_idx] * ci_[it_idx]
    s = stats(w.astype(float), cu[none_ut_idx].astype(float))
    for k in s:
        draws[k].append(s[k])
draws = {k: np.array(v) for k, v in draws.items()}  # (B, P)


def pci(a):
    a = a[~np.isnan(a)]
    return [round(float(np.percentile(a, 2.5)), 4), round(float(np.percentile(a, 97.5)), 4)]


# ---- per-pipeline table
rows = []
for pi, p in enumerate(PIPES):
    r = dict(pipeline=p)
    for k in point:
        r[k] = round(float(point[k][pi]), 4)
        r[k + "_ci"] = pci(draws[k][:, pi])
    sub = att[att.pipeline == p]
    r["n_exposed"] = int(sub.exposed.sum())
    r["n_exposed_able"] = int((sub.exposed & sub.able).sum())
    r["n_able_injection_tasks"] = int(ab[ab.pipeline == p].utility.sum())
    r["n_errors"] = int(sub.error.sum())
    rows.append(r)
pm = pd.DataFrame(rows)
os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
pm.drop(columns=[c for c in pm.columns if c.endswith("_ci")]).to_csv(os.path.join(ROOT, "results", "per_model.csv"), index=False)

mi = [PIPES.index(m) for m in MODELS]


# ---- C1: ranking
def separated_pairs(stat):
    out = {}
    for a in range(len(mi)):
        for b in range(a + 1, len(mi)):
            d = draws[stat][:, mi[a]] - draws[stat][:, mi[b]]
            d = d[~np.isnan(d)]
            lo, hi = np.percentile(d, [2.5, 97.5])
            pt = point[stat][mi[a]] - point[stat][mi[b]]
            sign = 1 if lo > 0 else (-1 if hi < 0 else 0)
            p2 = 2 * min((d <= 0).mean(), (d >= 0).mean())
            out[(MODELS[a], MODELS[b])] = (sign, float(pt), float(p2))
    return out


sep = {s: separated_pairs(s) for s in ["S0", "S1", "S2", "S3"]}
pair_rows = []
for k in sep["S0"]:
    pair_rows.append(dict(a=k[0], b=k[1], **{f"{s}_sign": sep[s][k][0] for s in sep},
                          **{f"{s}_diff": round(sep[s][k][1], 4) for s in sep},
                          **{f"{s}_p": round(sep[s][k][2], 4) for s in sep}))
pairs = pd.DataFrame(pair_rows)
pairs.to_csv(os.path.join(ROOT, "results", "pairs.csv"), index=False)
c1 = {}
for s in ["S1", "S2", "S3"]:
    x0, x1 = point["S0"][mi], point[s][mi]
    rev = pairs[(pairs.S0_sign != 0) & (pairs[f"{s}_sign"] == -pairs.S0_sign)]
    flip_any = pairs[(pairs.S0_sign != 0) & (np.sign(pairs[f"{s}_diff"]) == -pairs.S0_sign)]
    sp = np.array([spearmanr(draws["S0"][b, mi], draws[s][b, mi]).statistic for b in range(B)])
    c1[s] = dict(spearman=round(float(spearmanr(x0, x1).statistic), 3), spearman_ci=pci(sp),
                 kendall=round(float(kendalltau(x0, x1).statistic), 3),
                 n_pairs=len(pairs), n_sep_S0=int((pairs.S0_sign != 0).sum()),
                 n_sep_stat=int((pairs[f"{s}_sign"] != 0).sum()),
                 n_sep_S0_reversed_separated=len(rev), reversed_pairs=[f"{a} vs {b}" for a, b in zip(rev.a, rev.b)],
                 n_sep_S0_point_reversed=len(flip_any))


# ---- C2: trend with capability
def trend(stat, idx=mi):
    pt = spearmanr(point["U"][idx], point[stat][idx]).statistic
    bs = np.array([spearmanr(draws["U"][b, idx], draws[stat][b, idx]).statistic for b in range(B)])
    return dict(spearman=round(float(pt), 3), ci=pci(bs))


c2 = {s: trend(s) for s in ["S0", "S1", "S2", "S3", "S4", "E"]}

# ---- C3: defences
base = PIPES.index("gpt-4o-2024-05-13")
dres = []
for d in DEFENCES:
    di = PIPES.index(d)
    ekey, ckey = ("R", "S1R") if "pi_detector" in d else ("E", "S1")
    tot = np.log(point["S0"][di] / point["S0"][base])
    expo = np.log(point[ekey][di] / point[ekey][base])
    tot_b = np.log(draws["S0"][:, di] / draws["S0"][:, base])
    expo_b = np.log(draws[ekey][:, di] / draws[ekey][:, base])
    share_b = expo_b / tot_b
    dcond = draws[ckey][:, di] - draws[ckey][:, base]
    dres.append(dict(defence=d, ASR=round(float(point["S0"][di]), 4), ASR_0=round(float(point["S0"][base]), 4),
                     exposure=round(float(point[ekey][di]), 4), exposure_0=round(float(point[ekey][base]), 4),
                     cond_ASR=round(float(point[ckey][di]), 4), cond_ASR_ci=pci(draws[ckey][:, di]),
                     cond_ASR_0=round(float(point[ckey][base]), 4),
                     cond_diff_ci=pci(dcond), exposure_share=round(float(expo / tot), 3),
                     exposure_share_ci=pci(share_b),
                     follow_given_exposed=round(float(point["S3"][di]), 4), follow_given_exposed_0=round(float(point["S3"][base]), 4)))
# tool filter: attacker tool in the filtered list
ATTACKER_TOOL = {"workspace": {"injection_task_0": "send_email", "injection_task_1": "delete_file",
                               "injection_task_2": "create_calendar_event", "injection_task_3": "send_email",
                               "injection_task_4": "send_email", "injection_task_5": "send_email"},
                 "travel": {"injection_task_0": "reserve_hotel", "injection_task_1": "send_email",
                            "injection_task_2": "create_calendar_event", "injection_task_3": "send_email",
                            "injection_task_4": "reserve_hotel", "injection_task_5": "send_email", "injection_task_6": None},
                 "banking": {**{f"injection_task_{i}": "send_money" for i in (0, 1, 2, 3, 5, 6, 8)},
                             "injection_task_4": "update_scheduled_transaction", "injection_task_7": "update_password"},
                 "slack": {"injection_task_1": "send_direct_message", "injection_task_2": "post_webpage",
                           "injection_task_3": "get_webpage", "injection_task_4": "post_webpage",
                           "injection_task_5": "invite_user_to_slack"}}
tf = att[att.pipeline == "gpt-4o-2024-05-13-tool_filter"].copy()


def has_tool(r):
    t = ATTACKER_TOOL[r.suite][r.injection_task]
    if t is None:
        return True  # text-only task needs no tool
    return t in (r.tool_filter_list or "")  # substring, as the pipeline does


tf["tool_avail"] = tf.apply(has_tool, axis=1)
g = tf[tf.exposed]
tool_filter_extra = dict(
    n_cases=len(tf), share_attacker_tool_available=round(float(tf.tool_avail.mean()), 4),
    n_exposed_tool_available=int(g.tool_avail.sum()),
    asr_exposed_tool_available=round(float(g[g.tool_avail].security.mean()), 4),
    asr_exposed_tool_missing=round(float(g[~g.tool_avail].security.mean()), 4),
    n_success_with_tool_missing=int(g[~g.tool_avail].security.sum()),
    follow_exposed_tool_available=round(float(g[g.tool_avail].follow.mean()), 4),
    undefended_S1=round(float(point["S1"][base]), 4),
)
# CI for asr_exposed_tool_available by two-way bootstrap
tfk = tf.set_index(tf.ut + "|" + tf.it).reindex(key)
avail = tfk.tool_avail.values.astype(float)
num = (SEC[PIPES.index("gpt-4o-2024-05-13-tool_filter")] * EXP[PIPES.index("gpt-4o-2024-05-13-tool_filter")] * avail)
den = (EXP[PIPES.index("gpt-4o-2024-05-13-tool_filter")] * avail)
rng2 = np.random.default_rng(SEED + 1)
bs = []
for b in range(B):
    cu = np.bincount(rng2.integers(0, len(uts), len(uts)), minlength=len(uts))
    ci_ = np.bincount(rng2.integers(0, len(its), len(its)), minlength=len(its))
    w = cu[ut_idx] * ci_[it_idx]
    bs.append((num * w).sum() / (den * w).sum())
tool_filter_extra["asr_exposed_tool_available_ci"] = pci(np.array(bs))
pd.DataFrame(dres).to_csv(os.path.join(ROOT, "results", "defences.csv"), index=False)

res = json.load(open(RESULTS)) if os.path.exists(RESULTS) else {}
res["effect"] = dict(B=B, seed=SEED, per_pipeline=pm.to_dict("records"), C1_ranking=c1, C2_trend=c2,
                     C3_defences=dres, C3_tool_filter=tool_filter_extra)
json.dump(res, open(RESULTS, "w"), indent=1)

pd.set_option("display.width", 250)
print(pm[["pipeline", "U", "S0", "S0_ci", "E", "S1", "S1_ci", "S2", "S3", "S3_ci", "S4", "n_exposed", "n_exposed_able", "n_able_injection_tasks"]].to_string())
print(json.dumps(c1, indent=1))
print(json.dumps(c2, indent=1))
print(pd.DataFrame(dres).to_string())
print(json.dumps(tool_filter_extra, indent=1))
