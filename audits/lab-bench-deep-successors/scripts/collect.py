"""Collect every reported number into results.json (from results/*.json and the parent's published.json)."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
R = HERE / "results"
ver = json.loads((R / "versions.json").read_text())
lb2 = json.loads((R / "lb2.json").read_text())
exp = json.loads((R / "exposure.json").read_text())
per = json.loads((R / "peritem.json").read_text())
pub = json.loads((HERE.parent / "lab-bench" / "results" / "published.json").read_text())["tables"]

out = {
    "q1_versions": {k: {f: v[f] for f in ("date", "n_items", "S_carrying_cue", "F_carrying_cue", "flaw_present",
                                          "r1_S_mean", "r1_S_ci_subtasks", "r2_S_mean", "r2_S_ci_subtasks",
                                          "r1_all_mean", "r1_all_ci_subtasks", "r2_all_mean", "r2_all_ci_subtasks",
                                          "placebo_all_mean", "placebo_all_ci_subtasks", "r1_F_mean", "r2_F_mean",
                                          "dbqa_variant_multi_sequence")}
                    | {"vs_parent_pin": v.get("vs_parent_pin"),
                       "per_subtask": {s: {x: e[x] for x in ("n", "chance", "r1", "r1_p", "r1_halves", "r2", "r2_p", "r2_halves", "placebo", "placebo_p", "carries_cue")}
                                       for s, e in v["subtasks"].items()}}
                    for k, v in ver["sources"].items()},
    "q1_hfbio_curated": ver["hfbio_curated"].get("subtasks"),
    "q1_labbench2": {"report_files": lb2["n_report_files"], "cases": lb2["format_totals"]["cases"],
                     "cases_with_lettered_list_regex_hits": lb2["format_totals"]["lettered"],
                     "lettered_hits_by_task": lb2["lettered_hits_by_task"], "unique_task_ids": lb2["unique_ids_total"],
                     "grading_dispatch": lb2["grading_dispatch"]},
    "lead_labbench2_seqqa2": {"constant_answer_ceiling_by_type": lb2["seqqa2_constant"],
                              "mutation_restriction": lb2["mutation_restriction"],
                              "inject_refusals": lb2["seqqa2_inject_refusals"],
                              "inject_means": lb2["seqqa2_inject_means"],
                              "label": "post hoc; 'answered_none_rate' uses truncated answers in the reports and is a lower bound"},
    "lead_numfrags_2024": {"paper_full_set": {m: pub[m]["SeqQA_RE-seq-numfrags"] for m in ("accuracy", "precision", "coverage")},
                           "rule_on_2024_public_release": ver["sources"]["hf@7268767a"]["subtasks"]["RE-seq-numfrags"],
                           "label": "post hoc; the paper's tables cover public+private items"},
    "q2_q3_exposure": exp,
    "q4_peritem": per,
    "inference": {"calls": 0, "usd": 0.0},
}
(HERE / "results.json").write_text(json.dumps(out, indent=1))
print("wrote results.json", len(json.dumps(out)))
