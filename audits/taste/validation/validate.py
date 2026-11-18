"""Validator's desk re-derivation for the TASTE audit (claims T0-T3, T7 and the magnet-free placebo).

Inputs:
- validation/redigitised_raw.json (validator's own reading of the critic's Fig. 2, redigitise.py);
- paper Table 5 and Fig. 19, re-transcribed by the validator from data/paper/taste.txt and p-36.png
  (checked against the auditor's scripts/published.py only after transcription: identical);
- data/eci/eci_scores.csv (Epoch, fetched 2026-11-17).
No auditor code is imported. Seed 20261117. Output: validation/validation_desk.json.

Every per-model accuracy here is READ FROM A CHART and snapped to the grid of possible values
(k/80 on 40 pairs, k/104 on 52 pairs: one verdict per pair, half credit at p = 0.5).
"""
import csv, json
from pathlib import Path
import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent.parent
rng = np.random.default_rng(20261117)

# --- Epoch ECI ---------------------------------------------------------------------------
ECI, ECI_LO, ECI_HI = {}, {}, {}
for row in csv.DictReader(open(HERE / "data/eci/eci_scores.csv")):
    n = row["Display name"]
    ECI[n] = float(row["eci"]); ECI_LO[n] = float(row["eci_ci_low"] or row["eci"]); ECI_HI[n] = float(row["eci_ci_high"] or row["eci"])

# model: (epoch name, family, release group, paper model?)
M = {
 "Haiku 4.5": ("Claude Haiku 4.5", "A", "a-haiku45", 1), "Opus 4.5": ("Claude Opus 4.5", "A", "a-opus45", 1),
 "Sonnet 4.6": ("Claude Sonnet 4.6", "A", "a-son46", 1), "Opus 4.6": ("Claude Opus 4.6", "A", "a-opus46", 1),
 "Sonnet 5": ("Claude Sonnet 5", "A", "a-son5", 1), "Opus 4.7": ("Claude Opus 4.7", "A", "a-opus47", 1),
 "Opus 4.8": ("Claude Opus 4.8", "A", "a-opus48", 1), "Fable 5": ("Claude Fable 5", "A", "a-fable5", 1),
 "Opus 5": ("Claude Opus 5", "A", "a-opus5", 1), "Fable 5.1": ("Claude Fable 5.1", "A", "a-fable51", 0),
 "Opus 5.5": ("Claude Opus 5.5", "A", "a-opus55", 0), "Fable 5.2": ("Claude Fable 5.2", "A", "a-fable52", 0),
 "GPT-5.6-luna": ("GPT-5.6 Luna", "O", "o-5.6", 1), "GPT-5.6-terra": ("GPT-5.6 Terra", "O", "o-5.6", 1),
 "GPT-5.6-sol": ("GPT-5.6 Sol", "O", "o-5.6", 1), "GPT-5.5": ("GPT-5.5", "O", "o-5.5", 0),
 "GPT-6 Luna": ("GPT-6 Luna", "O", "o-6", 0), "GPT-6 Sol": ("GPT-6 Sol", "O", "o-6", 0),
 "GPT-6 Astra": ("GPT-6 Astra", "O", "o-6", 0), "GPT-6.1 Sol": ("GPT-6.1 Sol", "O", "o-6.1", 0),
 "GPT-6.1 Terra": ("GPT-6.1 Terra", "O", "o-6.1", 0),
 "GLM 5.2": ("GLM-5.2", "X", "x-glm", 1), "Qwen3.7-Max": ("Qwen3.7-Max", "X", "x-qwen", 1),
 "Muse Spark 1.1": ("Muse Spark 1.1", "X", "x-muse", 1), "Grok 4.5": ("Grok 4.5", "X", "x-grok", 1),
 "Gemini 3.5 Flash": ("Gemini 3.5 Flash", "X", "x-gem", 1), "Gemini 3.1 Pro": ("Gemini 3.1 Pro", "X", "x-gem", 1),
 "Kimi K3": ("Kimi K3", "X", "x-kimi", 1),
}
names = list(M)
eci = np.array([ECI[M[m][0]] for m in names])
fam = np.array([M[m][1] for m in names])
grp = np.array([M[m][2] for m in names])
paper = np.array([M[m][3] for m in names], bool)

# --- match markers to models: per panel and colour class, by nearest ECI with one-to-one order --
raw = json.loads((HERE / "validation/redigitised_raw.json").read_text())
CLS = {"A": "blue", "O": "orange", "X": "green"}

def match(panel, step):
    out, xres = {}, {}
    for f, c in CLS.items():
        mk = [dict(m) for m in raw[panel]["markers"] if m["cls"] == c]
        for k in mk:  # crescent (Luna) markers: the coloured mask's box sits left of the marker
            if c == "orange" and k["h"] == 33:  # centre; shift +0.35 ECI. The opposite assignment
                k["eci"] += 0.35                # contradicts Table 5 by 3-4 points (checked in T0).
        ms = sorted([m for m in names if M[m][1] == f], key=lambda m: ECI[M[m][0]])
        # greedy nearest with one-to-one assignment
        pairs = sorted(((abs(k["eci"] - ECI[M[m][0]]), i, m) for i, k in enumerate(mk) for m in ms))
        used_k, used_m = set(), set()
        for dist, i, m in pairs:
            if i in used_k or m in used_m or dist > 0.6:
                continue
            used_k.add(i); used_m.add(m)
            a = mk[i]["acc"]
            out[m] = {"raw": a, "snap": round(round(a / step) * step, 2), "h": mk[i]["h"]}
            xres[m] = round(mk[i]["eci"] - ECI[M[m][0]], 2)
    return out, xres

dec, xres_dec = match("rubric_40_decided", 100 / 80)
tie, xres_tie = match("rubric_52_ties", 100 / 104)

# Table 5 (validator transcription): distinct Q shown, distinct Q hidden, within Q shown, within Q hidden
T5 = {"Fable 5": (69, 61, 31, 47), "Kimi K3": (66, 65, 33, 53), "Grok 4.5": (57, 56, 28, 50),
      "Gemini 3.5 Flash": (44, 63, 56, 67), "Sonnet 4.6": (57, 60, 22, 44), "Haiku 4.5": (60, 51, 67, 50),
      "Opus 4.8": (59, 61, 33, 44), "Opus 4.5": (49, 50, 50, 47), "Sonnet 5": (54, 52, 33, 42),
      "Qwen3.7-Max": (52, 55, 36, 50), "Opus 5": (52, 59, 22, 39), "Muse Spark 1.1": (52, 54, 35, 56),
      "Opus 4.7": (55, 55, 25, 36), "GPT-5.6-luna": (54, 47, 28, 53), "GPT-5.6-terra": (51, 51, 22, 44),
      "GPT-5.6-sol": (49, 49, 28, 50), "GLM 5.2": (49, 51, 33, 39), "Opus 4.6": (51, 51, 31, 31),
      "Gemini 3.1 Pro": (47, 43, 22, 56)}
T3 = {"Fable 5": 60, "Kimi K3": 59, "Grok 4.5": 58, "Gemini 3.5 Flash": 56, "Sonnet 4.6": 56, "Haiku 4.5": 56,
      "Opus 4.8": 55, "Opus 4.5": 54, "Sonnet 5": 52, "Qwen3.7-Max": 52, "Opus 5": 51, "Muse Spark 1.1": 51,
      "Opus 4.7": 49, "GPT-5.6-luna": 48, "GPT-5.6-terra": 48, "GPT-5.6-sol": 48, "GLM 5.2": 46,
      "Opus 4.6": 45, "Gemini 3.1 Pro": 41}
MF = {"Fable 5": 62, "Opus 5": 56, "Opus 4.8": 50, "Sonnet 5": 47, "Haiku 4.5": 40, "Sonnet 4.6": 51,
      "Opus 4.5": 44, "Opus 4.6": 29, "Opus 4.7": 52, "GPT-5.6-sol": 44, "GPT-5.6-terra": 35,
      "GPT-5.6-luna": 40, "Grok 4.5": 45, "Kimi K3": 52, "Qwen3.7-Max": 42, "GLM 5.2": 36,
      "Muse Spark 1.1": 42, "Gemini 3.1 Pro": 27, "Gemini 3.5 Flash": 47}
qs = {m: (74 * v[0] + 18 * v[2]) / 92 for m, v in T5.items()}
qh = {m: (74 * v[1] + 18 * v[3]) / 92 for m, v in T5.items()}

res = {"marker_x_minus_epoch_eci": {"decided": xres_dec, "ties": xres_tie}}
res["unmatched"] = {"decided": [m for m in names if m not in dec], "ties": [m for m in names if m not in tie]}

# T0: reproduction; fill the occluded tie marker(s) from Table 5
t0 = {}
for m in T5:
    if m in dec and m in tie:
        t0[m] = round((40 * dec[m]["snap"] + 52 * tie[m]["snap"]) / 92 - qs[m], 2)
res["T0_qshown_from_fig_minus_table5"] = t0
d = np.abs(list(t0.values()))
res["T0_summary"] = {"n": len(d), "median_abs": round(float(np.median(d)), 2), "max_abs": round(float(d.max()), 2)}
ties = {}
for m in names:
    if m in tie and tie[m]["h"] >= 15:
        ties[m] = tie[m]["snap"]
for m in names:
    if m not in ties and m in T5 and m in dec:
        ties[m] = round((92 * qs[m] - 40 * dec[m]["snap"]) / 52, 2)  # derived; +-0.9 from Table 5 rounding
        res.setdefault("filled_from_table5", {})[m] = {"derived": ties[m], "chart_partial": tie.get(m, {}).get("raw")}
y = np.array([ties[m] for m in names])

def pr(x, yy):
    r, p = stats.pearsonr(x, yy)
    z, se = np.arctanh(r), 1 / np.sqrt(len(x) - 3)
    return {"r": round(float(r), 3), "ci": [round(float(np.tanh(z - 1.96 * se)), 3), round(float(np.tanh(z + 1.96 * se)), 3)],
            "p": round(float(p), 4), "n": int(len(x))}

def perm_p(x, yy, n=10000, within=None):
    r0 = np.corrcoef(x, yy)[0, 1]; c = 0
    for _ in range(n):
        if within is None:
            yp = rng.permutation(yy)
        else:
            yp = yy.copy()
            for gname in np.unique(within):
                idx = np.where(within == gname)[0]; yp[idx] = rng.permutation(yy[idx])
        c += abs(np.corrcoef(x, yp)[0, 1]) >= abs(r0) - 1e-12
    return round(c / n, 4)

def fe_slope(x, yy, g):
    xd, yd = x.copy(), yy.copy()
    for gname in np.unique(g):
        i = g == gname; xd[i] -= x[i].mean(); yd[i] -= yy[i].mean()
    return float((xd * yd).sum() / (xd ** 2).sum())

def fe_perm(x, yy, g, n=10000):
    b0 = fe_slope(x, yy, g); c = 0
    for _ in range(n):
        yp = yy.copy()
        for gname in np.unique(g):
            idx = np.where(g == gname)[0]; yp[idx] = rng.permutation(yy[idx])
        c += abs(fe_slope(x, yp, g)) >= abs(b0) - 1e-12
    return {"slope": round(b0, 3), "p_within_family_perm": round(c / n, 4)}

T = {}
haiku = np.array([m == "Haiku 4.5" for m in names])
T["all28"] = pr(eci, y); T["all28"]["perm_p"] = perm_p(eci, y)
T["no_haiku"] = pr(eci[~haiku], y[~haiku])
for f in "AOX":
    T[f"within_{f}"] = pr(eci[fam == f], y[fam == f])
    T[f"drop_{f}"] = pr(eci[fam != f], y[fam != f])
s = (fam != "O") & ~haiku
T["drop_O_and_haiku"] = pr(eci[s], y[s])
s = (fam == "A") & ~haiku
T["within_A_no_haiku"] = pr(eci[s], y[s])
T["fe"] = fe_perm(eci, y, fam)
T["fe_no_haiku"] = fe_perm(eci[~haiku], y[~haiku], fam[~haiku])
loo = {m: round(float(np.corrcoef(np.delete(eci, i), np.delete(y, i))[0, 1]), 3) for i, m in enumerate(names)}
T["leave_one_out"] = {"min": min(loo.values()), "max": max(loo.values()),
                      "argmin": min(loo, key=loo.get), "argmax": max(loo, key=loo.get), "all": loo}
# leave-two-out over models (all pairs)
l2 = [np.corrcoef(np.delete(eci, [i, j]), np.delete(y, [i, j]))[0, 1] for i in range(28) for j in range(i + 1, 28)]
T["leave_two_out"] = {"min": round(float(min(l2)), 3), "max": round(float(max(l2)), 3), "share_p_lt_05": None}
ps = [stats.pearsonr(np.delete(eci, [i, j]), np.delete(y, [i, j]))[1] for i in range(28) for j in range(i + 1, 28)]
T["leave_two_out"]["share_p_lt_05"] = round(float(np.mean(np.array(ps) < 0.05)), 3)
# release-group cluster bootstrap (models of one OpenAI generation resampled together)
G = np.unique(grp); bs = []
for _ in range(5000):
    pick = rng.choice(G, len(G))
    idx = np.concatenate([np.where(grp == gg)[0] for gg in pick])
    if np.std(eci[idx]) > 0 and np.std(y[idx]) > 0:
        bs.append(np.corrcoef(eci[idx], y[idx])[0, 1])
T["release_cluster_bootstrap"] = {"n_clusters": int(len(G)), "ci95": [round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)]}
fb = []
fams = np.array(["A", "O", "X"])
for _ in range(5000):
    pick = rng.choice(fams, 3)
    idx = np.concatenate([rng.choice(np.where(fam == f)[0], (fam == f).sum()) for f in pick])
    if np.std(eci[idx]) > 0 and np.std(y[idx]) > 0:
        fb.append(np.corrcoef(eci[idx], y[idx])[0, 1])
T["two_stage_family_bootstrap"] = {"ci95": [round(float(np.percentile(fb, 2.5)), 3), round(float(np.percentile(fb, 97.5)), 3)],
                                   "share_r_ge_0": round(float(np.mean(np.array(fb) >= 0)), 3)}

# Reading error and ECI error propagation
def counts(yy, ee):
    strong = ee > 158
    return int(strong.sum()), int((yy[strong] < 50).sum())
mc = {"reading_uniform_pm0.5": [], "eci_epoch_ci": [], "both": []}
sd_eci = np.array([(ECI_HI[M[m][0]] - ECI_LO[M[m][0]]) / 3.92 for m in names])
for _ in range(5000):
    yr = y + rng.uniform(-0.5, 0.5, 28)
    er = eci + rng.normal(0, sd_eci)
    for k, (yy, ee) in {"reading_uniform_pm0.5": (yr, eci), "eci_epoch_ci": (y, er), "both": (yr, er)}.items():
        mc[k].append((np.corrcoef(ee, yy)[0, 1], fe_slope(ee, yy, fam), *counts(yy, ee)))
prop = {}
for k, v in mc.items():
    v = np.array(v)
    prop[k] = {"r_2.5_50_97.5": [round(float(q), 3) for q in np.percentile(v[:, 0], [2.5, 50, 97.5])],
               "fe_slope_2.5_97.5": [round(float(q), 3) for q in np.percentile(v[:, 1], [2.5, 97.5])],
               "share_all_strong_below50": round(float(np.mean(v[:, 2] == v[:, 3])), 3),
               "n_strong_range": [int(v[:, 2].min()), int(v[:, 2].max())]}
T["error_propagation"] = prop
n_s, n_b = counts(y, eci)
T["strong_gt158"] = {"n": n_s, "below50": n_b, "max_acc": float(y[eci > 158].max()),
                     "models_157_158": {m: ties[m] for m in names if 157 <= ECI[M[m][0]] <= 158.0}}
for cut in (150, 155, 156, 157, 158, 159, 160):
    T.setdefault("cutoff_sweep", {})[cut] = list(counts(y, eci) if cut == 158 else (int((eci > cut).sum()), int((y[eci > cut] < 50).sum())))
res["T3"] = T

# Binomial below-chance per model on 52 (pair-level, critic's style) for the strong models
res["sig_below_pair_binomial"] = {m: round(float(stats.binomtest(int(round(ties[m] * 52 / 100)), 52, 0.5, "less").pvalue), 4)
                                  for m in names if ECI[M[m][0]] > 158}

# --- magnet-free placebo (T1) ------------------------------------------------------------
P = [m for m in names if paper[names.index(m)]]
e19 = np.array([ECI[M[m][0]] for m in P]); t19 = np.array([ties[m] for m in P]); mf19 = np.array([MF[m] for m in P])
T1 = {"ties19": pr(e19, t19), "mf19": pr(e19, mf19), "r_ties_mf": round(float(np.corrcoef(t19, mf19)[0, 1]), 3),
      "below50_ties19": int((t19 < 50).sum()), "below50_mf19": int((mf19 < 50).sum()),
      "mean_ties19": round(float(t19.mean()), 2), "mean_mf19": round(float(mf19.mean()), 2)}
# Is the difference between the two correlations larger than chance? model bootstrap of r_t - r_mf
db = []
for _ in range(5000):
    i = rng.integers(0, 19, 19)
    if np.std(t19[i]) > 0 and np.std(mf19[i]) > 0:
        db.append(np.corrcoef(e19[i], t19[i])[0, 1] - np.corrcoef(e19[i], mf19[i])[0, 1])
T1["diff_r_model_bootstrap_ci"] = [round(float(np.percentile(db, 2.5)), 3), round(float(np.percentile(db, 97.5)), 3)]
# Condition mismatch: approximate question-shown magnet-free accuracy as MF - c * (qh - qs)/2,
# i.e. assume the magnet-free subset has c times the whole-benchmark shown/hidden gap.
gap = np.array([qh[m] - qs[m] for m in P])
T1["r_eci_whole_qshown"] = pr(e19, np.array([qs[m] for m in P]))["r"]
T1["r_eci_whole_qhidden"] = pr(e19, np.array([qh[m] for m in P]))["r"]
T1["r_eci_whole_avg_table3"] = pr(e19, np.array([T3[m] for m in P]))["r"]
T1["r_eci_shown_hidden_gap"] = pr(e19, gap)
T1["mf_qshown_approx"] = {str(c): pr(e19, mf19 - c * gap / 2)["r"] for c in (0, 1, 2, 3, 4)}
# Overlap probe: implied accuracy on the 40 magnet pairs (avg condition) vs critic's 40 decided (shown)
mag40 = np.array([(92 * T3[m] - 52 * MF[m]) / 40 for m in P])
d40 = np.array([dec[m]["snap"] if m in dec else np.nan for m in P])
ok = ~np.isnan(d40)
T1["implied_magnet40_mean"] = round(float(mag40.mean()), 2)
T1["r_magnet40_vs_decided40"] = round(float(np.corrcoef(mag40[ok], d40[ok])[0, 1]), 3)
T1["r_qshown_vs_t3"] = round(float(np.corrcoef([qs[m] for m in P], [T3[m] for m in P])[0, 1]), 3)
res["T1"] = T1

# --- T2 within-prompt worst case --------------------------------------------------------
T2 = {}
w = np.array([T5[m][2] for m in P])
for k in (0, 6, 12, 18):
    adj = (52 * t19 - k * w) / (52 - k)
    strong = e19 > 158
    T2[k] = {"r": pr(e19, adj)["r"], "ci": pr(e19, adj)["ci"], "strong_below50": int((adj[strong] < 50).sum()),
             "n_strong": int(strong.sum()), "per_strong": {P[i]: round(float(adj[i]), 1) for i in np.where(strong)[0]}}
T2["r_eci_within_qshown"] = pr(e19, w)
T2["r_eci_within_qhidden"] = pr(e19, np.array([T5[m][3] for m in P]))["r"]
T2["r_eci_distinct_qshown"] = pr(e19, np.array([T5[m][0] for m in P]))["r"]
T2["r_eci_distinct_qhidden"] = pr(e19, np.array([T5[m][1] for m in P]))["r"]
# Table 5 rounding (+-0.5 on each cell) propagated into the k = 18 bound
rb = []
for _ in range(2000):
    ww = w + rng.uniform(-0.5, 0.5, 19)
    adj = (52 * t19 - 18 * ww) / 34
    rb.append(np.corrcoef(e19, adj)[0, 1])
T2["k18_r_rounding_range"] = [round(float(min(rb)), 3), round(float(max(rb)), 3)]
res["T2"] = T2

# --- T7 human number --------------------------------------------------------------------
res["T7"] = {"half_credit_7": round((0.774 * 85 + 3.5) / 92 * 100, 2), "zero_credit_7": round(0.774 * 85 / 92 * 100, 2)}

res["ties_used"] = ties
res["decided_used"] = {m: v["snap"] for m, v in dec.items()}
(HERE / "validation/validation_desk.json").write_text(json.dumps(res, indent=1))
print(json.dumps({k: v for k, v in res.items() if k not in ("ties_used", "decided_used")}, indent=1))

# --- Random-split placebo of the critic's sizes (52/40), models INDEPENDENT -------------------
# Each model's 92 per-pair outcomes are unknown; its count of correct verdicts on the 92 pairs is
# known from the chart (40*dec + 52*tie, in half-credit units). A random 52-pair subset then has a
# hypergeometric count. Models are drawn independently, which ignores that models err on the same
# pairs: this null is too narrow if errors are shared, so it is a lower bound on placebo spread.
units = {m: int(round((40 * res["decided_used"][m] + 52 * ties[m]) / 100 * 2)) for m in names if m in res["decided_used"]}
if "Opus 5.5" not in units:  # decided marker hidden under GPT-6.1 Sol (51.25): use 51.25 +- 2
    units["Opus 5.5"] = int(round((40 * 51.25 + 52 * ties["Opus 5.5"]) / 100 * 2))
K = np.array([units[m] for m in names]); placebo = []
for _ in range(10000):
    t = rng.hypergeometric(K, 184 - K, 104) / 104 * 100
    placebo.append((np.corrcoef(eci, t)[0, 1], np.all(t[eci > 158] < 50)))
placebo = np.array(placebo)
res["random_split_placebo_independent"] = {
    "r_2.5_50_97.5": [round(float(q), 3) for q in np.percentile(placebo[:, 0], [2.5, 50, 97.5])],
    "P_r_le_obs": round(float(np.mean(placebo[:, 0] <= T["all28"]["r"])), 4),
    "P_all_strong_below50": round(float(placebo[:, 1].mean()), 4),
    "r_eci_overall_qshown_28": round(float(np.corrcoef(eci, K)[0, 1]), 3)}
(HERE / "validation/validation_desk.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res["random_split_placebo_independent"]))

# Below-50 count for the 19 paper models on random 52-pair splits (same independence caveat)
K19 = np.array([units[m] for m in P])
cnt = np.array([(rng.hypergeometric(K19, 184 - K19, 104) / 104 * 100 < 50).sum() for _ in range(10000)])
res["random_split_placebo_independent"]["paper19_below50_count_2.5_50_97.5"] = [int(q) for q in np.percentile(cnt, [2.5, 50, 97.5])]
res["random_split_placebo_independent"]["paper19_P_count_ge_13"] = round(float(np.mean(cnt >= 13)), 4)
res["random_split_placebo_independent"]["paper19_overall_qshown_below50"] = int((K19 < 92).sum())
(HERE / "validation/validation_desk.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res["random_split_placebo_independent"]))

# Non-OpenAI trend (critic: r = -0.57, p = .011): leave-one-model-out within the 19 non-OpenAI models
no = np.where(fam != "O")[0]
lo = {names[i]: stats.pearsonr(np.delete(eci[no], k), np.delete(y[no], k)) for k, i in enumerate(no)}
res["non_openai_loo"] = {"r_range": [round(float(min(v[0] for v in lo.values())), 3), round(float(max(v[0] for v in lo.values())), 3)],
                         "n_p_lt_05": int(sum(v[1] < 0.05 for v in lo.values())), "n": len(lo),
                         "fails": {m: [round(float(v[0]), 3), round(float(v[1]), 3)] for m, v in lo.items() if v[1] >= 0.05}}
(HERE / "validation/validation_desk.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res["non_openai_loo"]))
