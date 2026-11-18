"""Analysis E (prereg.md): what the published human number is under forced-choice scoring,
and how wide the item-sampling interval of each "exceeds experts" claim is.

Human accuracy (App. E.4) counts only correct answers not flagged "unsure"; unsure answers
carried a best guess that is not scored. So under the scoring applied to a model that must
answer, the human number lies in [acc, acc + (1 - cov)]. Chance-guess midpoint uses the mean
option count of the public items (+1 for no refusal option is not added: humans chose among
substantive options and "unsure").

Model claims (claims.md): score, n items, n clusters. Intervals: Wilson (items iid) and a
cluster-adjusted Wilson using the design effect estimated from Haiku's per-item outcomes on
the same subset (results/haiku_analysis.json; an approximation, labelled as such).
Writes results/human_baseline.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RESULTS, clusters, load_items, wilson  # noqa: E402

CLAIMS = [
    # (label, subset, model score, n items scored, source)
    ("Opus 4.6 FigQA, crop tool", "FigQA", 0.783, 181, "Opus 4.6 card 2.19.1 (5-run mean; n assumed = 181 public)"),
    ("Opus 4.6 FigQA, no tools", "FigQA", 0.580, 181, "Opus 4.6 card 2.19.1"),
    ("Opus 4.8 FigQA, no tools", "FigQA", 0.804, 181, "Opus 4.8 card 8.12.3 (181 public)"),
    ("Opus 4.5 FigQA, crop tool", "FigQA", 0.6924, 181, "Opus 4.5 card 7.2.4.4"),
    ("Opus 4.5 ProtocolQA", "ProtocolQA", 0.907, 108, "Opus 4.5 card 7.2.4.4 (n assumed = 108 public)"),
    ("Opus 4.5 CloningScenarios", "CloningScenarios", 0.758, 33, "Opus 4.5 card 7.2.4.4 (n assumed = 33 public)"),
    ("Opus 4.5 SeqQA", "SeqQA", 0.8517, 600, "Opus 4.5 card 7.2.4.4 (n assumed = 600 public)"),
    ("Claude 3.7 / o3 CloningScenarios", "CloningScenarios", 0.61, 33, "Justen 2025 sec. 3 (33 public, 10 runs)"),
]


def main() -> None:
    pub = json.loads((RESULTS / "published.json").read_text())
    acc, prec, cov = (pub["tables"][m] for m in ("accuracy", "precision", "coverage"))
    items = load_items(check=False)
    items["cluster"] = clusters(items)
    hb = {}
    for s in ["FigQA", "ProtocolQA", "CloningScenarios", "TableQA", "LitQA2", "SuppQA"]:
        a, p, c = acc[s]["human"], prec[s]["human"], cov[s]["human"]
        k = float(items[items.subset == s].n_options.mean())
        hb[s] = {"accuracy": a, "precision": p, "coverage": c, "mean_options": round(k, 2),
                 "forced_lower": a, "forced_upper": round(a + (1 - c), 4),
                 "forced_chance_guess": round(a + (1 - c) / k, 4),
                 "forced_if_guesses_as_good_as_sure": p}
    seq = pub["seqqa_mean_of_15_subtasks"]
    a, p, c = seq["accuracy"]["human"], seq["precision"]["human"], seq["coverage"]["human"]
    hb["SeqQA"] = {"accuracy": a, "precision": p, "coverage": c, "mean_options": 4.07,
                   "forced_lower": a, "forced_upper": round(a + (1 - c), 4),
                   "forced_chance_guess": round(a + (1 - c) / 4.07, 4),
                   "forced_if_guesses_as_good_as_sure": p,
                   "note": "mean of 15 subtask cells; the paper's coverage differs by subtask (0.50-1.00)"}
    deff_all = {}
    ha = RESULTS / "haiku_analysis.json"
    if ha.exists():
        deff_all = json.loads(ha.read_text()).get("design_effects", {})
    out = {"human": hb, "claims": []}
    for label, s, score, n, src in CLAIMS:
        lo, hi = wilson(score * n, n)
        sub = items[items.subset == s]
        n_cl = int(sub.cluster.nunique())
        # design effect from Haiku runs on the same subset: take the largest-n condition
        cands = [(v["n"], v["deff"]) for k, v in deff_all.items() if k.endswith("|" + s) and v.get("deff")]
        deff = max(cands)[1] if cands else None
        if deff:
            n_eff = n / max(deff, 1.0)
            clo, chi = wilson(score * n_eff, int(round(n_eff)))
        else:
            clo = chi = None
        h = hb[s]
        out["claims"].append({
            "claim": label, "source": src, "subset": s, "score": score, "n": n, "clusters_public": n_cl,
            "wilson95": [round(lo, 4), round(hi, 4)],
            "deff_from_haiku": deff, "cluster_adj_wilson95": [round(clo, 4), round(chi, 4)] if clo else None,
            "human_accuracy": h["accuracy"], "human_precision": h["precision"],
            "human_forced_range": [h["forced_lower"], h["forced_upper"]],
            "margin_vs_human_accuracy": round(score - h["accuracy"], 4),
            "margin_vs_human_precision": round(score - h["precision"], 4),
            "line_inside_model_interval": bool(lo <= h["accuracy"] <= hi),
            "score_inside_human_forced_range": bool(h["forced_lower"] <= score <= h["forced_upper"]),
        })
    (RESULTS / "human_baseline.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(hb, indent=1))
    for c in out["claims"]:
        print(c["claim"], c["score"], "wilson", c["wilson95"], "clustered", c["cluster_adj_wilson95"],
              "| human acc", c["human_accuracy"], "prec", c["human_precision"], "forced range", c["human_forced_range"],
              "| inside range:", c["score_inside_human_forced_range"])


if __name__ == "__main__":
    main()
