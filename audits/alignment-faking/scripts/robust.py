"""Robustness checks and the post-hoc analyses (labelled as such in README.md).

    data/.venv/bin/python -I scripts/robust.py

Needs results/analysis_seed0.json, analysis_seed1.json and analysis_seed0_thr-0.5.json (from
analyze.py). Writes results/robust.json.

Post hoc, after seeing the pre-registered results:
  P1  A5: each "no gap" cell's observed gap interval against the gap Opus's marginal odds ratio
      would produce at that cell's paid rate (the pre-registered conditional-OR rule turned out
      to be driven by the few discordant pairs).
  P2  Claude 3 Opus vs Claude 3.5 Sonnet on the risk and odds scales, on their shared queries.
  P3  Bootstrap intervals for AUROCs on the 106 human labels (rule K vs original classifier).
  P4  A3 on the odds scale: conditional OR for C_both.
  P5  A3 pooled ratio, dropping each variant.
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze as A  # noqa: E402  (our own module)

RES = os.path.join(HERE, "..", "results")


def load_json(n):
    with open(os.path.join(RES, n)) as fh:
        return json.load(fh)


def main():
    rng = np.random.default_rng(0)
    r0, r1, r5 = (load_json(f) for f in ("analysis_seed0.json", "analysis_seed1.json", "analysis_seed0_thr-0.5.json"))
    out = {}

    # ---- seed and threshold stability of the headline quantities
    def keyq(r):
        return {
            "A1_gap_ci": r["A1"]["gap_ci_query_boot"],
            "A1_cond_or": r["A1"]["cond_or"],
            "A2_dropk10_default_share_removed": r["A2"]["dropk"]["k"]["10"]["default_share_removed"],
            "A2_dropk10_halfB_share_removed": r["A2"]["dropk"]["k"]["10"]["halfB_share_removed"],
            "A2_top10pct_share": r["A2"]["top10pct_share_of_gap"],
            "A2_top10pct_null_p95": r["A2"]["top10pct_share_null_p50_p95"][1],
            "A2_overdispersion_p": r["A2"]["overdispersion_p"],
            "A2_spearman_gap": r["A2"]["cross_model"]["spearman_gap"],
            "A3_default_ratio": r["A3"]["default"]["gaps"]["C_both_over_C_pm"],
            "A3_default_ratio_ci": r["A3"]["default"]["gaps"]["C_both_over_C_pm_ci"],
            "A3_pooled_ratio": r["A3"]["opus_pooled"]["gaps"]["C_both_over_C_pm"],
            "A3_pooled_ratio_ci": r["A3"]["opus_pooled"]["gaps"]["C_both_over_C_pm_ci"],
            "A4_residual": r["A4"]["opus_pooled"]["residual"],
            "A4_residual_ci": r["A4"]["opus_pooled"]["residual_ci"],
            "A6_auroc_K": r["A6"]["auroc_K_heldout"],
            "A6_auroc_K_human": r["A6"]["human"]["auroc_K_vs_human"],
            "A5_cells_ci_includes_opus_or": sorted(k for k, c in r["A5"]["cells"].items()
                                                   if c["no_gap_per_paper"] and c["ci_includes_opus_or"]),
        }
    out["seed0"], out["seed1"], out["thr_minus05"] = keyq(r0), keyq(r1), keyq(r5)

    d = A.load()
    opus = A.opus_variants(d)

    # ---- P1: observed gap interval vs gap under Opus's marginal OR
    p1 = {}
    for k, c in r0["A5"]["cells"].items():
        if not c["no_gap_per_paper"]:
            continue
        p1[k] = {"n": c["n_pairs"], "paid": c["paid"], "gap": c["gap"], "gap_ci": c["gap_ci"],
                 "gap_if_opus_or": c["gap_if_opus_or"], "mde80": c["mde80"],
                 "ci_excludes_opus_like_gap": c["gap_ci"][1] < c["gap_if_opus_or"]}
    out["P1_no_gap_cells_vs_opus_like"] = p1

    # ---- P2: Opus vs Sonnet 3.5 (default prompt), shared queries
    o = A.paired(d, "atn_honly").set_index("qkey")
    s = A.paired(d, "atn_honly_sonnet_3_5").set_index("qkey")
    j = o.join(s, lsuffix="_o", rsuffix="_s", how="inner")
    fo, po = j.C_pm_f_o.values.astype(float), j.C_pm_p_o.values.astype(float)
    fs, ps = j.C_pm_f_s.values.astype(float), j.C_pm_p_s.values.astype(float)

    def lor(f, p):
        f, p = f.mean(), p.mean()
        f = min(max(f, 0.5 / len(fo)), 1 - 0.5 / len(fo))
        p = min(max(p, 0.5 / len(fo)), 1 - 0.5 / len(fo))
        return np.log(f / (1 - f)) - np.log(p / (1 - p))

    n = len(j)
    bs_rd, bs_lor = [], []
    for _ in range(2000):
        i = rng.integers(0, n, n)
        bs_rd.append((fs[i].mean() - ps[i].mean()) - (fo[i].mean() - po[i].mean()))
        bs_lor.append(lor(fs[i], ps[i]) - lor(fo[i], po[i]))
    out["P2_opus_vs_sonnet35_default"] = {
        "n_shared_queries": n,
        "opus": {"free": fo.mean(), "paid": po.mean(), "gap": fo.mean() - po.mean(), "log_or": lor(fo, po)},
        "sonnet35": {"free": fs.mean(), "paid": ps.mean(), "gap": fs.mean() - ps.mean(), "log_or": lor(fs, ps)},
        "gap_diff_sonnet_minus_opus": float((fs.mean() - ps.mean()) - (fo.mean() - po.mean())),
        "gap_diff_ci": [float(np.percentile(bs_rd, 2.5)), float(np.percentile(bs_rd, 97.5))],
        "log_or_diff_sonnet_minus_opus": float(lor(fs, ps) - lor(fo, po)),
        "log_or_diff_ci": [float(np.percentile(bs_lor, 2.5)), float(np.percentile(bs_lor, 97.5))],
        "af_rate": {"opus": float(j.AF_f_o.mean()), "sonnet35": float(j.AF_f_s.mean())},
    }

    # ---- P3: AUROC intervals on the 106 human labels
    vs = [v for v in opus if not v.startswith("atn_basic")] + [v for v in d.variant.unique() if "sonnet_3_5" in v and "no_cot" not in v]
    X = d[(d.variant.isin(vs)) & (d.tier == "train") & (~d.AF_fail)].copy()
    X["log_len"] = np.log1p(X.len_scratch)
    feats = list(A.KW.keys()) + ["log_len"]
    # same split as analyze.py seed 0: reproduce by re-drawing with the same generator state is
    # impractical, so refit on all Greenblatt rows (the rule never sees the human labels either way)
    sc = StandardScaler().fit(X[feats])
    lr = LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(X[feats]), X.AF.values.astype(int))
    H = pd.read_csv(A.HUMAN_CSV).merge(pd.read_parquet(A.HUMAN_HF)[["scratchpad_reasoning", "alignment_faking_human_label"]],
                                       on="scratchpad_reasoning", how="inner")
    y = H.alignment_faking_human_label.values.astype(int)
    kh = lr.predict_proba(sc.transform(A.kw_feats(H.scratchpad_reasoning.tolist())[feats]))[:, 1]
    scores = {"rule_K_fit_on_all_greenblatt": kh,
              "original_hard": H["original-sonnet-new-hard"].values,
              "original_easy": H["original-sonnet-new-easy"].values,
              "new_gpt4o_v5_n20": H["4o-CoT-v5 n=20 t=1.0"].values,
              "length": H.scratchpad_reasoning.fillna("").str.len().values}
    pt = {k: float(roc_auc_score(y, v)) for k, v in scores.items()}
    bs = {k: [] for k in scores}
    bsd = {"K_minus_original_hard": [], "K_minus_original_easy": [], "new_minus_K": []}
    for _ in range(2000):
        i = rng.integers(0, len(y), len(y))
        if y[i].min() == y[i].max():
            continue
        a = {k: roc_auc_score(y[i], v[i]) for k, v in scores.items()}
        for k in scores:
            bs[k].append(a[k])
        bsd["K_minus_original_hard"].append(a["rule_K_fit_on_all_greenblatt"] - a["original_hard"])
        bsd["K_minus_original_easy"].append(a["rule_K_fit_on_all_greenblatt"] - a["original_easy"])
        bsd["new_minus_K"].append(a["new_gpt4o_v5_n20"] - a["rule_K_fit_on_all_greenblatt"])
    out["P3_human_label_aurocs"] = {
        "n": int(len(y)), "n_pos": int(y.sum()),
        "auroc": pt,
        "ci": {k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for k, v in bs.items()},
        "diff_ci": {k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for k, v in bsd.items()},
        "note": "column-to-classifier mapping inferred from names in human_labelled_data2.csv",
    }

    # ---- P4: odds scale for C_both in the default cell
    m = A.paired(d, "atn_honly")
    for c in ("C_pm", "C_both"):
        f, p = m[c + "_f"].values, m[c + "_p"].values
        b, cc = int((f & ~p).sum()), int((~f & p).sum())
        out.setdefault("P4_default_odds_scale", {})[c] = {"b": b, "c": cc, "cond_or": A.cond_or(b, cc),
                                                          "free": float(f.mean()), "paid": float(p.mean())}

    # ---- P5: A3 pooled ratio dropping each variant
    vs3 = [v for v in opus if not v.startswith("atn_basic")]
    ms = {v: A.paired(d, v) for v in vs3}
    ratios = []
    for v in vs3:
        mm = pd.concat([ms[u] for u in vs3 if u != v])
        gp = mm.C_pm_f.mean() - mm.C_pm_p.mean()
        gb = mm.C_both_f.mean() - mm.C_both_p.mean()
        ratios.append(gb / gp)
    out["P5_A3_pooled_ratio_drop_each_variant_min_max"] = [float(min(ratios)), float(max(ratios))]

    # ---- Bonferroni: 5 main tests + one per A5 cell
    ncells = len(r0["A5"]["cells"])
    k = 5 + ncells
    alpha = 0.05 / k
    m = A.paired(d, "atn_honly")
    f, p = m.C_pm_f.values.astype(float), m.C_pm_p.values.astype(float)
    bs = [f[i].mean() - p[i].mean() for i in rng.integers(0, len(f), (4000, len(f)))]
    out["bonferroni"] = {"n_tests": k, "alpha": alpha,
                         "A1_gap_ci_bonf": [float(np.percentile(bs, 100 * alpha / 2)), float(np.percentile(bs, 100 * (1 - alpha / 2)))],
                         "A1_mcnemar_p": r0["A1"]["cond_or"]["p_mcnemar"]}
    # A3 difference at the Bonferroni level (default cell)
    qs = m.qkey.values
    fb, pb = m.C_both_f.values.astype(float), m.C_both_p.values.astype(float)
    dd = []
    for _ in range(4000):
        i = rng.integers(0, len(f), len(f))
        dd.append((f[i].mean() - p[i].mean()) - (fb[i].mean() - pb[i].mean()))
    out["bonferroni"]["A3_default_diff_ci_bonf"] = [float(np.percentile(dd, 100 * alpha / 2)), float(np.percentile(dd, 100 * (1 - alpha / 2)))]

    with open(os.path.join(RES, "robust.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print(json.dumps(out, indent=1, default=float)[:6000])


if __name__ == "__main__":
    main()
