"""Validator: the 15-subtask SeqQA score arithmetic, re-derived from validation/v1_rows.csv,
and the comparison with the human line.

Human reference numbers come from the parent audit's validation (validation/v5_human.json in
audits/lab-bench): SeqQA, mean over the 15 subtasks, a = 0.789 (unsure scored wrong, the paper's
rule), and the forced-choice values 0.808 (unsure guesses at chance), 0.854 (at the humans' own
precision) and 0.866 (all unsure guesses right).

Run: ../lab-bench/data/.venv/bin/python -I validation/v7_score.py
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

AUD = Path(__file__).resolve().parent.parent
CUE = ["Prop-seq-gcpercent-v1", "ORF-seq-AAseq-v1", "PCR-gene-enzprimers-v1",
       "PCR-seq-enzprimers-v1", "PCR-gene-gibshindprimers-v1", "PCR-gene-gibssmaprimers-v1"]
HUMAN = {"paper_unsure_wrong": 0.789, "forced_q_chance": 0.808, "forced_q_precision": 0.854,
         "forced_q_one": 0.866}


def main():
    rows = list(csv.DictReader(open(AUD / "validation" / "v1_rows.csv")))
    acc = defaultdict(lambda: defaultdict(list))
    for r in rows:
        arm = "K" if r["arm"] == "O/K" else r["arm"]
        acc[(r["model"], arm)][r["subtask"]].append(int(r["bucket"] == "correct"))
    out = {"human": HUMAN, "models": {}}
    for model in ("sonnet", "haiku"):
        noncue = {s: v for s, v in acc[(model, "O")].items() if s not in CUE}
        res = {"noncue_subtasks": len(noncue),
               "noncue_items": sum(len(v) for v in noncue.values()),
               "noncue_mean": round(float(np.mean([np.mean(v) for v in noncue.values()])), 4)}
        for name, arm in (("cue_for_K", "K"), ("cue_against_D", "D")):
            cue = {s: acc[(model, arm)][s] for s in CUE if acc[(model, arm)][s]}
            vals = {**noncue, **cue}
            if len(vals) != 15:
                res[name] = {"missing": sorted(set(CUE) - set(cue))}
                continue
            point = float(np.mean([np.mean(v) for v in vals.values()]))
            rng = np.random.default_rng(0)
            arrs = [np.array(v, float) for v in vals.values()]
            bs = [np.mean([a[rng.integers(0, len(a), len(a))].mean() for a in arrs])
                  for _ in range(2000)]
            res[name] = {"score": round(point, 4),
                         "ci_items_within_subtask": [round(float(np.percentile(bs, 2.5)), 4),
                                                     round(float(np.percentile(bs, 97.5)), 4)],
                         "above_paper_human_0.789": round(point - HUMAN["paper_unsure_wrong"], 4),
                         "inside_forced_range_0.808_0.866":
                             HUMAN["forced_q_chance"] <= point <= HUMAN["forced_q_one"]}
        res["ci_overlaps_whole_forced_range"] = (
            res.get("cue_against_D", {}).get("ci_items_within_subtask", [1, 0])[0] <= HUMAN["forced_q_chance"]
            and res["cue_against_D"]["ci_items_within_subtask"][1] >= HUMAN["forced_q_precision"])
        out["models"][model] = res
    print(json.dumps(out, indent=1))
    (AUD / "validation" / "v7_score.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
