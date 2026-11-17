"""Validator step 2: independent re-derivation of claims 2 (ranking), 3 (capability trend) and 5
(error coding), plus per-model ASR/rank changes under conditioning and where each model's
"secure" cases come from. Reads only ../data/validation_cases.json (from v1_extract.py).

Run: ../data/.venv/bin/python -I v2_claims.py
Writes blocks 'rederive', 'per_model', 'security_sources', 'trend', 'error_coding' of validation.json.
Two-way crossed bootstrap over user tasks and injection tasks, B = 2000, seed 20261117.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.stats import kendalltau, pearsonr, spearmanr

from common_v import AUDIT, GPT4O, MODELS20, PAPER10, save

B, SEED = 2000, 20261117
D = json.load(open(os.path.join(AUDIT, "data", "validation_cases.json")))
cases = [r for r in D["cases"] if r["pipeline"] in MODELS20]
keys = sorted({(r["suite"], r["ut"], r["inj"]) for r in cases})
assert len(keys) == 629
kpos = {k: i for i, k in enumerate(keys)}
uts = sorted({(k[0], k[1]) for k in keys})
its = sorted({(k[0], k[2]) for k in keys})
ui = np.array([uts.index((k[0], k[1])) for k in keys])
ii = np.array([its.index((k[0], k[2])) for k in keys])
M = len(MODELS20)


def mat(field, pipes=MODELS20, src=cases):
    X = np.full((len(pipes), 629), np.nan)
    pi = {p: j for j, p in enumerate(pipes)}
    for r in src:
        if r["pipeline"] in pi:
            X[pi[r["pipeline"]], kpos[(r["suite"], r["ut"], r["inj"])]] = float(r[field])
    assert not np.isnan(X).any()
    return X


SEC, ERR, EXP, ACT, NM = (mat(f) for f in ("security", "error", "exposed", "acted", "n_msgs"))
ABLE = np.array([[float(D["ability"][p][f"{k[0]}/{k[2]}"]) for k in keys] for p in MODELS20])
# utility over the 97 benign user tasks, aligned to uts
U97 = np.array([[float(D["benign"][p][f"{s}/{u}"]) for (s, u) in uts] for p in MODELS20])
TRACED = (NM > 0).astype(float)


def rate(num, den, w):
    d = (den * w).sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (num * den * w).sum(1) / d


def stats(w, wu):
    one = np.ones_like(SEC)
    sne = SEC * (1 - ERR)
    return dict(
        S0=rate(SEC, one, w),                 # published ASR
        S0e=rate(sne, one, w),                # errors as not attacked
        E=rate(EXP, TRACED, w),               # exposure among traced cases
        S1=rate(SEC, EXP, w),                 # ASR | exposed
        S1e=rate(sne, EXP, w),
        S2=rate(SEC, EXP * ABLE, w),          # ASR | exposed, able
        S3=rate(ACT, EXP, w),                 # acted | exposed
        A=rate(ABLE, one, w),
        U=(U97 * wu).sum(1) / wu.sum(),
    )


pt = stats(np.ones(629), np.ones(len(uts)))
rng = np.random.default_rng(SEED)
draws = {k: [] for k in pt}
for _ in range(B):
    cu = np.bincount(rng.integers(0, len(uts), len(uts)), minlength=len(uts)).astype(float)
    ci = np.bincount(rng.integers(0, len(its), len(its)), minlength=len(its)).astype(float)
    st = stats(cu[ui] * ci[ii], cu)
    for k in st:
        draws[k].append(st[k])
draws = {k: np.array(v) for k, v in draws.items()}


def q(a):
    a = np.asarray(a, float)
    a = a[~np.isnan(a)]
    return [round(float(np.percentile(a, 2.5)), 4), round(float(np.percentile(a, 97.5)), 4)]


def ranks(x):  # rank 1 = highest ASR, ties averaged
    from scipy.stats import rankdata
    return rankdata(-np.asarray(x))


# ---------------- Claim 2: ranking
rank_block = {}
for s in ("S1", "S2", "S3", "S1e"):
    sp_b = [spearmanr(draws["S0"][b], draws[s][b]).statistic for b in range(B)]
    sep_rev, sep, pt_rev = 0, 0, []
    for a in range(M):
        for c in range(a + 1, M):
            d0 = draws["S0"][:, a] - draws["S0"][:, c]
            lo, hi = np.percentile(d0, [2.5, 97.5])
            if lo > 0 or hi < 0:
                sep += 1
                sgn = 1 if lo > 0 else -1
                d1 = draws[s][:, a] - draws[s][:, c]
                l1, h1 = np.nanpercentile(d1, [2.5, 97.5])
                if (sgn == 1 and h1 < 0) or (sgn == -1 and l1 > 0):
                    sep_rev += 1
                if np.sign(pt[s][a] - pt[s][c]) == -sgn:
                    pt_rev.append(f"{MODELS20[a]} vs {MODELS20[c]}")
    rank_block[s] = dict(spearman=round(float(spearmanr(pt["S0"], pt[s]).statistic), 3), spearman_ci=q(sp_b),
                         kendall=round(float(kendalltau(pt["S0"], pt[s]).statistic), 3),
                         n_pairs_separated_S0=sep, n_separated_reversed_separated=sep_rev,
                         separated_pairs_reversed_at_point=pt_rev)

# per-model changes in ASR and rank with bootstrap intervals
pm = []
r0 = ranks(pt["S0"])
for j, p in enumerate(MODELS20):
    row = dict(model=p, U=round(float(pt["U"][j]), 4), S0=round(float(pt["S0"][j]), 4), S0_ci=q(draws["S0"][:, j]),
               E=round(float(pt["E"][j]), 4), E_ci=q(draws["E"][:, j]), A_share_able=round(float(pt["A"][j]), 4),
               n_traced=int(TRACED[j].sum()), n_errors=int(ERR[j].sum()), rank_S0=float(r0[j]))
    for s in ("S1", "S2", "S3"):
        row[s] = round(float(pt[s][j]), 4)
        row[s + "_ci"] = q(draws[s][:, j])
        row[s + "_minus_S0_pp"] = round(100 * float(pt[s][j] - pt["S0"][j]), 2)
        row[s + "_minus_S0_ci_pp"] = [round(100 * v, 2) for v in q(draws[s][:, j] - draws["S0"][:, j])]
        rk = ranks(pt[s])
        rb = np.array([ranks(draws[s][b])[j] - ranks(draws["S0"][b])[j] for b in range(B)])
        row["rank_" + s] = float(rk[j])
        row["rank_change_" + s] = float(r0[j] - rk[j])  # positive = moves toward "more attackable"
        row["rank_change_" + s + "_ci"] = [float(np.percentile(-rb, 2.5)), float(np.percentile(-rb, 97.5))]
    pm.append(row)

# ---------------- where "secure" comes from
src = []
for j, p in enumerate(MODELS20):
    secure = SEC[j] == 0
    tr = TRACED[j] == 1
    n_sec = int(secure.sum())
    not_exp = int((secure & tr & (EXP[j] == 0)).sum())
    untraced = int((secure & ~tr).sum())
    exp_unable = int((secure & (EXP[j] == 1) & (ABLE[j] == 0)).sum())
    exp_able = int((secure & (EXP[j] == 1) & (ABLE[j] == 1)).sum())
    exp_able_noact = int((secure & (EXP[j] == 1) & (ABLE[j] == 1) & (ACT[j] == 0)).sum())
    src.append(dict(model=p, S0=round(float(pt["S0"][j]), 4), n_secure=n_sec, untraced=untraced,
                    not_exposed=not_exp, exposed_unable=exp_unable, exposed_able=exp_able,
                    exposed_able_no_action=exp_able_noact,
                    share_not_exposed_or_untraced=round((not_exp + untraced) / n_sec, 4),
                    share_not_exposed_or_unable=round((not_exp + untraced + exp_unable) / n_sec, 4)))

# ---------------- Claim 3: trend
perm_rng = np.random.default_rng(SEED + 1)


def trend(idx, s):
    x, y = pt["U"][idx], pt[s][idx]
    rho = spearmanr(x, y).statistic
    perm = np.array([spearmanr(perm_rng.permutation(x), y).statistic for _ in range(10000)])
    bs = [spearmanr(draws["U"][b, idx], draws[s][b, idx]).statistic for b in range(B)]
    return dict(n_models=len(idx), spearman=round(float(rho), 3), boot_ci_models_fixed=q(bs),
                perm_p_two_sided=round(float((np.abs(perm) >= abs(rho) - 1e-12).mean()), 4),
                pearson=round(float(pearsonr(x, y).statistic), 3))


all_idx = np.arange(M)
p10 = np.array([MODELS20.index(m) for m in PAPER10])
non_anth = np.array([j for j, m in enumerate(MODELS20) if not m.startswith("claude")])
trend_block = {
    "all20": {s: trend(all_idx, s) for s in ("S0", "S0e", "S1", "S2", "S3", "E")},
    "paper10": {s: trend(p10, s) for s in ("S0", "S0e", "S1", "S3", "E")},
    "no_anthropic": {s: trend(non_anth, s) for s in ("S0", "S1")},
}
# models that are strictly June-2024 paper models but use the paper's own numbers (errors as not attacked)
trend_block["paper10_note"] = "paper10 = the ten models of paper Table 3; S0e reproduces Table 3's ASR"

# ---------------- Claim 5: error coding, from stored labels
err = []
for j, p in enumerate(MODELS20):
    err.append(dict(model=p, n_err=int(ERR[j].sum()), n_err_security_true=int((ERR[j] * SEC[j]).sum()),
                    n_err_utility_true=int((ERR[j] * (1 - 0)).sum() and 0),
                    asr_table=round(100 * float(pt["S0"][j]), 2), asr_errors_not_attack=round(100 * float(pt["S0e"][j]), 2),
                    n_err_exposed=int((ERR[j] * EXP[j]).sum())))
rk_t, rk_e = ranks(pt["S0"]), ranks(pt["S0e"])
for j, e in enumerate(err):
    e["rank_table"], e["rank_errors_not_attack"] = float(rk_t[j]), float(rk_e[j])

save("rederive", dict(B=B, seed=SEED, ranking=rank_block))
save("per_model", pm)
save("security_sources", src)
save("trend", trend_block)
save("error_coding_validator", err)

print(json.dumps(rank_block, indent=1))
print(json.dumps(trend_block, indent=1))
hdr = ["model", "S0", "E", "S1", "S1_minus_S0_pp", "rank_S0", "rank_S1", "rank_change_S1", "rank_change_S1_ci", "S3", "rank_change_S3"]
for r in sorted(pm, key=lambda r: r["S0"]):
    print({k: r[k] for k in hdr})
for r in sorted(src, key=lambda r: r["S0"]):
    print(r)
for e in err:
    if e["n_err"]:
        print(e)
