"""Desk tests T0-T3 and T7 (prereg.md) from published and digitised numbers.

Run: data/.venv/bin/python -I scripts/desk.py
Inputs: data/eci/eci_scores.csv (Epoch, fetched 2026-11-17), results/critic_fig2_digitised.json.
Output: results/desk.json. Seed 20261117.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "scripts"))
import published as P  # noqa: E402

RNG = np.random.default_rng(20261117)


def load_eci():
    eci = {}
    with open(HERE / "data/eci/eci_scores.csv", newline="") as f:
        for row in csv.DictReader(f):
            eci[row["Display name"]] = float(row["eci"])
    return {m: eci[n] for m, n in P.ECI_NAME.items()}


def match_markers(eci, panel_markers):
    """Assign digitised markers to models by colour and nearest ECI (greedy, max distance 0.8)."""
    cls = {"anthropic": "anthropic_blue", "openai": "openai_orange", "other": "other_green"}
    cands = []
    for m, x in eci.items():
        target = x - (0.4 if m in P.CRESCENT else 0.0)
        for j, mk in enumerate(panel_markers):
            if mk["class"] == cls[P.family(m)]:
                cands.append((abs(mk["eci"] - target), m, j))
    cands.sort()
    used_m, used_j, out = set(), set(), {}
    for d, m, j in cands:
        if d > 0.8 or m in used_m or j in used_j:
            continue
        out[m] = {"acc": panel_markers[j]["acc"], "marker_eci": panel_markers[j]["eci"], "dist": round(d, 2)}
        used_m.add(m); used_j.add(j)
    return out


def pearson(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    r = float(np.corrcoef(x, y)[0, 1])
    n = len(x)
    if n > 3:
        z, se = np.arctanh(r), 1 / np.sqrt(n - 3)
        lo, hi = float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se))
    else:
        lo = hi = float("nan")
    perm = np.array([np.corrcoef(x, RNG.permutation(y))[0, 1] for _ in range(10000)])
    p = float((np.abs(perm) >= abs(r) - 1e-12).mean())
    return {"r": round(r, 3), "ci95": [round(lo, 3), round(hi, 3)], "p_perm": round(p, 4), "n": n}


def fe_slope(x, y, groups, nperm=10000):
    """Slope of y on x with group fixed effects; p from permuting y within groups."""
    x, y, g = np.asarray(x, float), np.asarray(y, float), np.asarray(groups)
    def slope(yv):
        xd, yd = x.copy(), yv.copy()
        for k in np.unique(g):
            s = g == k
            xd[s] -= x[s].mean(); yd[s] -= yv[s].mean()
        return float((xd * yd).sum() / (xd * xd).sum())
    b = slope(y)
    null = []
    for _ in range(nperm):
        yp = y.copy()
        for k in np.unique(g):
            s = np.where(g == k)[0]
            yp[s] = y[RNG.permutation(s)]
        null.append(slope(yp))
    null = np.array(null)
    return {"slope_pts_per_eci": round(b, 3), "p_perm_within_family": round(float((np.abs(null) >= abs(b)).mean()), 4)}


def main():
    eci = load_eci()
    dig = json.loads((HERE / "results/critic_fig2_digitised.json").read_text())
    dec = match_markers(eci, dig["rubric_40_decided"]["markers"])
    tie = match_markers(eci, dig["rubric_52_ties"]["markers"])
    pdec = match_markers(eci, dig["past_40_decided"]["markers"])
    ptie = match_markers(eci, dig["past_52_ties"]["markers"])
    out = {"eci": eci, "digitised": {"decided": dec, "ties": tie, "past_decided": pdec, "past_ties": ptie},
           "missing": {"decided": sorted(set(eci) - set(dec)), "ties": sorted(set(eci) - set(tie))}}
    paper = list(P.TABLE5)

    # ---------- T0 reproduction ----------
    t0 = {}
    for m in paper:
        _, ds, dh, ws, wh = P.TABLE5[m]
        qshown = (74 * ds + 18 * ws) / 92
        qhidden = (74 * dh + 18 * wh) / 92
        crit = (40 * dec[m]["acc"] + 52 * tie[m]["acc"]) / 92 if (m in dec and m in tie) else None
        t0[m] = {"qshown_table5": round(qshown, 1), "qhidden_table5": round(qhidden, 1),
                 "qshown_from_critic_fig": None if crit is None else round(crit, 1),
                 "diff": None if crit is None else round(crit - qshown, 1)}
    diffs = [abs(v["diff"]) for v in t0.values() if v["diff"] is not None]
    models_tie = sorted(tie)
    r_all = pearson([eci[m] for m in models_tie], [tie[m]["acc"] for m in models_tie])
    out["T0"] = {"per_model": t0, "median_abs_diff": round(float(np.median(diffs)), 2),
                 "max_abs_diff": round(float(np.max(diffs)), 2), "n_compared": len(diffs),
                 "r_ties_eci_digitised": r_all,
                 "n_above158": sum(eci[m] > 158 for m in models_tie),
                 "n_above158_below50": sum(eci[m] > 158 and tie[m]["acc"] < 50 for m in models_tie),
                 "openai_mean_ties": round(float(np.mean([tie[m]["acc"] for m in models_tie if P.family(m) == "openai"])), 1),
                 "fable5_qshown_table5": t0["Fable 5"]["qshown_table5"], "haiku_qshown_table5": t0["Haiku 4.5"]["qshown_table5"]}
    # Gemini 3.1 Pro is occluded in the ties panel: derive it from Table 5 and the decided panel.
    derived_tie = {}
    for m in paper:
        if m in dec:
            derived_tie[m] = round((92 * t0[m]["qshown_table5"] - 40 * dec[m]["acc"]) / 52, 1)
    out["T0"]["ties_derived_from_table5_and_decided"] = derived_tie

    # Full 28-model ties vector: digitised, with occluded models filled from the derivation.
    ties28 = {m: tie[m]["acc"] for m in tie}
    for m in eci:
        if m not in ties28 and m in derived_tie:
            ties28[m] = derived_tie[m]
    out["ties28"] = ties28
    r28 = pearson([eci[m] for m in ties28], [ties28[m] for m in ties28])
    out["T0"]["r_ties_eci_28_filled"] = r28

    # ---------- T1 label-blind placebo: magnet-free ----------
    mf = P.FIG19_MAGNET_FREE_SITUATIONAL
    t1 = {
        "magnet_free_below50": sum(v < 50 for v in mf.values()),
        "magnet_free_mean": round(float(np.mean(list(mf.values()))), 1),
        "magnet_free_r_eci": pearson([eci[m] for m in paper], [mf[m] for m in paper]),
        "critic_ties_below50_paper19": sum(ties28[m] < 50 for m in paper),
        "critic_ties_mean_paper19": round(float(np.mean([ties28[m] for m in paper])), 1),
        "critic_ties_r_eci_paper19": pearson([eci[m] for m in paper], [ties28[m] for m in paper]),
        "magnet_free_above158": {m: mf[m] for m in paper if eci[m] > 158},
        "critic_ties_above158_paper": {m: ties28[m] for m in paper if eci[m] > 158},
        "r_magnetfree_vs_critic_ties": pearson([mf[m] for m in paper], [ties28[m] for m in paper]),
        # accuracy on the 40 magnet pairs implied by Table 3 and Fig. 19 (averaged condition)
        "implied_magnet_pairs_acc": {m: round((92 * P.TABLE3[m] - 52 * mf[m]) / 40, 1) for m in paper},
    }
    t1["implied_magnet_mean"] = round(float(np.mean(list(t1["implied_magnet_pairs_acc"].values()))), 1)
    # Same-size binomial: how many below 50 at p<.05 (one-sided exact) on 52 pairs
    t1["magnet_free_sig_below"] = sum(stats.binomtest(round(v * 52 / 100), 52, 0.5, alternative="less").pvalue < 0.05 for v in mf.values())
    t1["critic_ties_sig_below_paper19"] = sum(stats.binomtest(round(ties28[m] * 52 / 100), 52, 0.5, alternative="less").pvalue < 0.05 for m in paper)
    out["T1"] = t1

    # ---------- T2 within-prompt pairs inside the ties ----------
    t2 = {}
    for m in paper:
        _, ds, dh, ws, wh = P.TABLE5[m]
        t = ties28[m]
        worst = (52 * t / 100 - 18 * ws / 100) / 34 * 100
        t2[m] = {"eci": eci[m], "ties": t, "within_qshown": ws, "distinct_qshown": ds,
                 "distinct_ties_if_all18_within_inside": round(worst, 1)}
    above = [m for m in paper if eci[m] > 158]
    gpt = [m for m in paper if m.startswith("GPT-5.6")]
    out["T2"] = {
        "per_model": t2,
        "above158_models": above,
        "above158_still_below50_worstcase": sum(t2[m]["distinct_ties_if_all18_within_inside"] < 50 for m in above),
        "gpt56_still_below50_worstcase": sum(t2[m]["distinct_ties_if_all18_within_inside"] < 50 for m in gpt),
        "r_eci_within_qshown": pearson([eci[m] for m in paper], [P.TABLE5[m][3] for m in paper]),
        "r_eci_within_qhidden": pearson([eci[m] for m in paper], [P.TABLE5[m][4] for m in paper]),
        "r_eci_distinct_qshown": pearson([eci[m] for m in paper], [P.TABLE5[m][1] for m in paper]),
        "r_eci_distinct_qhidden": pearson([eci[m] for m in paper], [P.TABLE5[m][2] for m in paper]),
        "r_eci_qshown_overall": pearson([eci[m] for m in paper], [t0[m]["qshown_table5"] for m in paper]),
        "r_eci_qhidden_overall": pearson([eci[m] for m in paper], [t0[m]["qhidden_table5"] for m in paper]),
        "r_eci_table3": pearson([eci[m] for m in paper], [P.TABLE3[m] for m in paper]),
        "mean_within_qshown_above158": round(float(np.mean([P.TABLE5[m][3] for m in above])), 1),
    }
    # Exploratory sweep (labelled as such in the README): k of the 18 within-prompt pairs in the
    # ties, each scored at the model's Table 5 within-prompt question-shown rate.
    sweep = {}
    for k in (0, 6, 12, 18):
        vals = {m: (52 * ties28[m] / 100 - k * P.TABLE5[m][3] / 100) / (52 - k) * 100 for m in paper}
        sweep[k] = {"r_eci_19": pearson([eci[m] for m in paper], [vals[m] for m in paper]),
                    "above158_below50": sum(vals[m] < 50 for m in above),
                    "values_above158": {m: round(vals[m], 1) for m in above}}
    out["T2"]["sweep_k_within_in_ties"] = sweep

    # ---------- T3 leverage and families ----------
    ms = sorted(ties28)
    x = np.array([eci[m] for m in ms]); y = np.array([ties28[m] for m in ms]); g = [P.family(m) for m in ms]
    t3 = {"all": pearson(x, y)}
    keep = [i for i, m in enumerate(ms) if m != "Haiku 4.5"]
    t3["without_haiku45"] = pearson(x[keep], y[keep])
    for fam in ("anthropic", "openai", "other"):
        s = [i for i, gg in enumerate(g) if gg == fam]
        t3[f"within_{fam}"] = pearson(x[s], y[s])
        s2 = [i for i, gg in enumerate(g) if gg != fam]
        t3[f"drop_{fam}"] = pearson(x[s2], y[s2])
    s = [i for i, (m, gg) in enumerate(zip(ms, g)) if gg == "anthropic" and m != "Haiku 4.5"]
    t3["within_anthropic_without_haiku45"] = pearson(x[s], y[s])
    t3["family_fixed_effects"] = fe_slope(x, y, g)
    t3["family_fixed_effects_without_haiku45"] = fe_slope(x[keep], y[keep], [g[i] for i in keep])
    # leave-one-model-out range of r
    loo = []
    for i in range(len(ms)):
        k = [j for j in range(len(ms)) if j != i]
        loo.append((float(np.corrcoef(x[k], y[k])[0, 1]), ms[i]))
    t3["loo_r_min_max"] = [round(min(loo)[0], 3), min(loo)[1], round(max(loo)[0], 3), max(loo)[1]]
    # whole-benchmark trend vs split-specific trend (models with both panels)
    both = [m for m in ms if m in dec]
    ov = {m: (40 * dec[m]["acc"] + 52 * ties28[m]) / 92 for m in both}
    t3["r_eci_qshown_overall_27"] = pearson([eci[m] for m in both], [ov[m] for m in both])
    t3["r_eci_ties_minus_overall_27"] = pearson([eci[m] for m in both], [ties28[m] - ov[m] for m in both])
    t3["r_eci_decided_27"] = pearson([eci[m] for m in both], [dec[m]["acc"] for m in both])
    t3["overall_qshown_mean_above158"] = round(float(np.mean([ov[m] for m in both if eci[m] > 158])), 1)
    t3["overall_qshown_below50_above158"] = sum(ov[m] < 50 for m in both if eci[m] > 158)
    t3["n_above158_with_both"] = sum(eci[m] > 158 for m in both)
    out["T3"] = t3

    # ---------- T7 the human number ----------
    fc = (P.HUMAN_AGREE * P.HUMAN_N_COMMITTED + 0.5 * (92 - P.HUMAN_N_COMMITTED)) / 92
    out["T7"] = {
        "forced_choice_equiv_pair_level": round(fc * 100, 1),
        "human_binomial_ci95": [round(100 * v, 1) for v in stats.binomtest(round(P.HUMAN_AGREE * 85), 85).proportion_ci()],
        "fable5_binomial_ci95": [round(100 * v, 1) for v in stats.binomtest(55, 92).proportion_ci()],
        "cap_range": P.HUMAN_CAP_RANGE,
        "magnet_free_gap_fable5": P.FIG19_HUMAN_MAGNET_FREE - P.FIG19_MAGNET_FREE_SITUATIONAL["Fable 5"],
        "full_gap_fable5": 77 - 60,
        "anchor_share_top2": round((38 + 27) / 92, 3),
    }
    (HERE / "results/desk.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    for k in ("T0", "T1", "T2", "T3", "T7"):
        print("=====", k)
        v = out[k]
        print(json.dumps({kk: vv for kk, vv in v.items() if kk not in ("per_model",)}, default=lambda o: o.item())[:6000])
    print("missing", out["missing"])
    print("T2 per model", json.dumps(out["T2"]["per_model"]))
    print("T0 per model", json.dumps(out["T0"]["per_model"]))


if __name__ == "__main__":
    main()
