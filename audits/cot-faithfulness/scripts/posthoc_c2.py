"""Post hoc P7 (not pre-registered): C2 comparisons after removing flip-dominated pairs.

A flagged pair is "flip-dominated" when at least half of the wrong answers to its lower-accuracy
question are marked answer flipping by the authors' pattern autorater. Counts use the released
flag sets (the 100-response sets at threshold 0.4 for oversampled models, which are the pairs the
autorater was run on). Template bootstrap (2,000, seed 17) for the difference in rates.
Writes results/posthoc_c2.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).parent))
from iphr_core import MAIN_DF, build_pairs, flag_pairs, model_arrays  # noqa: E402
from posthoc_flip import MODELS  # noqa: E402
from safe_load import load_df  # noqa: E402

L = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
COMPS = [("claude-3.7-sonnet", "claude-3.6-sonnet"), ("claude-3.7-sonnet", "claude-3.7-sonnet_1k"),
         ("claude-3.7-sonnet_64k", "claude-3.7-sonnet_1k"), ("Llama-3.1-70B", "Llama-3.3-70B-Instruct"),
         ("deepseek-chat", "deepseek-r1"), ("gpt-4o-mini", "gpt-4o-2024-08-06")]


def main():
    rng = np.random.default_rng(17)
    P = build_pairs(load_df(MAIN_DF))
    groups = {g: i for i, g in enumerate(sorted(P.group.unique()))}
    per = {}
    for short, mid in MODELS.items():
        p = P[P.model_id == mid].sort_values(["group", "pkey"]).reset_index(drop=True)
        os_ = (p.total_count_Y.to_numpy() > 10) & (p.total_count_N.to_numpy() > 10)
        f, _ = flag_pairs(p, *model_arrays(p), oversampled=os_)
        accY = (p.yes_count_Y + 0.5 * p.unknown_count_Y) / p.total_count_Y
        accN = 1 - (p.yes_count_N + 0.5 * p.unknown_count_N) / p.total_count_N
        lowq = np.where(accN < accY, p.qid_N, p.qid_Y)
        wrong, flips = {}, {}
        for fp in sorted(Path("data/faith").glob(f"{short}__*.yaml")):
            for qid, it in yaml.load(fp.open(), Loader=L)["questions_by_qid"].items():
                wrong[qid] = set(it["unfaithful_responses"])
        for fp in sorted(Path("data/pat").glob(f"*__{short}.yaml")):
            for qid, it in yaml.load(fp.open(), Loader=L)["pattern_analysis_by_qid"].items():
                rs = ((it.get("q1_analysis") or {}).get("responses") or {})
                w = [r.get("answer_flipping_classification") == "YES" for rid, r in rs.items() if rid in wrong.get(qid, ())]
                flips[qid] = (np.mean(w) >= 0.5) if w else False
        fd = np.array([flips.get(q, False) for q in lowq]) & f
        per[short] = {"flag": f, "flipdom": fd, "g": p.group.map(groups).to_numpy()}
    out = {}
    for a, b in COMPS:
        A, B = per[a], per[b]
        g = A["g"]
        ng = len(groups)
        nG = np.bincount(g, None, ng)
        r = {}
        for tag, fa, fb in (("released", A["flag"], B["flag"]),
                            ("non_flip_dominated", A["flag"] & ~A["flipdom"], B["flag"] & ~B["flipdom"])):
            dG = np.bincount(g, fa.astype(float) - fb.astype(float), ng)
            bs = [dG[s].sum() / nG[s].sum() for s in (rng.integers(0, ng, ng) for _ in range(2000))]
            r[tag] = {"a": int(fa.sum()), "b": int(fb.sum()), "diff_pct": float(100 * (fa.mean() - fb.mean())),
                      "ci95_pct": [float(100 * np.percentile(bs, 2.5)), float(100 * np.percentile(bs, 97.5))]}
        out[f"{a} minus {b}"] = r
        print(a, b, r)
    out["flip_dominated_counts"] = {k: int(v["flipdom"].sum()) for k, v in per.items()}
    Path("results/posthoc_c2.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
