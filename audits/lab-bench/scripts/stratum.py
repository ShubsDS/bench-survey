"""Analysis A (prereg.md): published SeqQA model-minus-human gaps on shortcut (S) versus
shortcut-free (F) subtasks, with two placebos over subtask splits. Uses the paper's
per-subtask Tables 2-3 (results/published.json) and the rule results (results/surface.json).
Writes results/stratum.json.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RESULTS  # noqa: E402

S = ["ORF-seq-AAseq", "PCR-gene-enzprimers", "PCR-seq-enzprimers", "PCR-gene-gibshindprimers",
     "PCR-gene-gibssmaprimers", "Prop-seq-gcpercent"]
PRIMER = ["PCR-gene-enzprimers", "PCR-seq-enzprimers", "PCR-gene-gibshindprimers",
          "PCR-gene-gibssmaprimers", "PCR-len-primers", "PCR-seq-primers"]
MODELS = ["claude-3-5-sonnet", "claude-3-opus", "gemini-1.5-pro", "gpt-4o", "gpt-4-turbo",
          "claude-3-haiku", "llama-3-70b"]


def gaps(tab, subs, split):
    d = {}
    for m in MODELS:
        g = lambda X: np.mean([tab[f"SeqQA_{s}"][m] - tab[f"SeqQA_{s}"]["human"] for s in X])  # noqa: E731
        F = [s for s in subs if s not in split]
        d[m] = {"gap_S": g(split), "gap_F": g(F), "D": g(split) - g(F)}
    return d


def analyse(tab, subs, s_set):
    obs = gaps(tab, subs, s_set)
    obs_mean = float(np.mean([v["D"] for v in obs.values()]))
    k = len(s_set)
    p1 = [float(np.mean([v["D"] for v in gaps(tab, subs, list(c)).values()]))
          for c in itertools.combinations(subs, k)]
    n_primer = sum(s in PRIMER for s in s_set)
    others = [s for s in subs if s not in PRIMER]
    p2 = []
    for a in itertools.combinations(PRIMER, n_primer):
        for b in itertools.combinations(others, k - n_primer):
            p2.append(float(np.mean([v["D"] for v in gaps(tab, subs, list(a) + list(b)).values()])))
    pct = lambda arr: float(np.mean(np.array(arr) < obs_mean))  # noqa: E731
    best = max(MODELS, key=lambda m: np.mean([tab[f"SeqQA_{s}"][m] for s in subs]))
    hum = lambda X: float(np.mean([tab[f"SeqQA_{s}"]["human"] for s in X]))  # noqa: E731
    mod = lambda X, m: float(np.mean([tab[f"SeqQA_{s}"][m] for s in X]))  # noqa: E731
    F = [s for s in subs if s not in s_set]
    return {
        "S": s_set, "per_model": {m: {kk: round(vv, 4) for kk, vv in v.items()} for m, v in obs.items()},
        "mean_D": round(obs_mean, 4),
        "placebo_all_splits": {"n": len(p1), "q025": round(float(np.percentile(p1, 2.5)), 4),
                               "q975": round(float(np.percentile(p1, 97.5)), 4), "percentile_of_obs": round(pct(p1), 4)},
        "placebo_matched_answer_type": {"n": len(p2), "q025": round(float(np.percentile(p2, 2.5)), 4),
                                        "q975": round(float(np.percentile(p2, 97.5)), 4), "percentile_of_obs": round(pct(p2), 4)},
        "best_model_by_seqqa_mean": best,
        "best_model_S": round(mod(s_set, best), 4), "human_S": round(hum(s_set), 4),
        "best_model_F": round(mod(F, best), 4), "human_F": round(hum(F), 4),
        "per_model_S_minus_human": {m: round(mod(s_set, m) - hum(s_set), 4) for m in MODELS},
        "per_model_F_minus_human": {m: round(mod(F, m) - hum(F), 4) for m in MODELS},
    }


def main() -> None:
    pub = json.loads((RESULTS / "published.json").read_text())
    surf = json.loads((RESULTS / "surface.json").read_text())
    subs = sorted(k.replace("SeqQA_", "") for k in pub["tables"]["accuracy"] if k.startswith("SeqQA_"))
    assert len(subs) == 15
    # S must be exactly the rule-solvable families (surface.json, heldout_best == 1.0)
    solved = sorted(f.split(":")[1].replace("-v1", "") for f, v in surf["families"].items()
                    if f.startswith("SeqQA:") and v["heldout_best"] >= 0.999)
    assert solved == sorted(S), solved
    out = {"rule_solved_subtasks": solved,
           "rule_heldout_by_subtask": {f.split(":")[1].replace("-v1", ""): v["heldout_best"]
                                       for f, v in surf["families"].items() if f.startswith("SeqQA:")}}
    for metric in ("accuracy", "precision"):
        tab = pub["tables"][metric]
        out[metric] = analyse(tab, subs, S)
        out[metric + "_numlen_in_S"] = analyse(tab, subs, S + ["ORF-seq-numlen"])
    # exploratory (not pre-registered): if a model scores 1.00 on the 6 S subtasks, what mean
    # accuracy on the 9 F subtasks reaches the human SeqQA mean (equal subtask weights, as in the
    # paper's 50-per-subtask full set and the 40-per-subtask public set)?
    acc = pub["tables"]["accuracy"]
    hum_all = float(np.mean([acc[f"SeqQA_{s}"]["human"] for s in subs]))
    F = [s for s in subs if s not in S]
    hum_F = float(np.mean([acc[f"SeqQA_{s}"]["human"] for s in F]))
    need_F = (hum_all * 15 - 6 * 1.0) / 9
    out["exploratory_threshold_arithmetic"] = {
        "human_seqqa_mean": round(hum_all, 4), "human_F_mean": round(hum_F, 4),
        "F_mean_needed_to_match_human_if_S_is_1": round(need_F, 4),
        "opus45_seqqa_0.8517_implies_F_if_S_is_1": round((0.8517 * 15 - 6) / 9, 4),
        "note": "Anthropic's SeqQA set, weighting and scoring are not published; equal weights assumed"}
    (RESULTS / "stratum.json").write_text(json.dumps(out, indent=1))
    print(out["exploratory_threshold_arithmetic"])
    for k in ("accuracy", "precision", "accuracy_numlen_in_S"):
        a = out[k]
        print(k, "mean D", a["mean_D"], "placebo all", a["placebo_all_splits"], "matched", a["placebo_matched_answer_type"])
        print("   best", a["best_model_by_seqqa_mean"], "S", a["best_model_S"], "vs human", a["human_S"],
              "| F", a["best_model_F"], "vs human", a["human_F"])
        print("   S-human", a["per_model_S_minus_human"])
        print("   F-human", a["per_model_F_minus_human"])


if __name__ == "__main__":
    main()
