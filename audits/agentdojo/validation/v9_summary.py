"""Validator step 9: record the rerun comparison and the per-claim verdicts in validation.json.

The rerun (step A) was done by copying ../scripts/ to a scratch folder whose data/ symlinked the
pinned clone and paper, running 01, 02, 04, 05, 06, 07 in that order with ../data/.venv/bin/python -I,
and comparing the scratch results.json, results/*.csv and data/cases.parquet with the committed ones.
Pass the scratch folder as argv[1] to recompute the comparison.

Run: ../data/.venv/bin/python -I v9_summary.py <scratch_rerun_dir>
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v import AUDIT, OUT_JSON, save

scratch = sys.argv[1]
a = json.load(open(os.path.join(AUDIT, "results.json")))
b = json.load(open(os.path.join(scratch, "results.json")))
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
csvs = sorted(f for f in os.listdir(os.path.join(AUDIT, "results")) if f.endswith(".csv"))
rerun = dict(results_json_blocks={k: a[k] == b.get(k) for k in a},
             csv_identical={f: sha(os.path.join(AUDIT, "results", f)) == sha(os.path.join(scratch, "results", f)) for f in csvs},
             cases_parquet_identical=sha(os.path.join(AUDIT, "data", "cases.parquet")) == sha(os.path.join(scratch, "data", "cases.parquet")),
             pins=dict(agentdojo_commit="089ed468cf3ed0322acc66b0211f26d9d90dbf60",
                       paper_v3_html_sha256=sha(os.path.join(AUDIT, "data", "paper", "v3.html"))))
V = json.load(open(OUT_JSON))
pm = {r["model"]: r for r in V["per_model"]}
src = {r["model"]: r for r in V["security_sources"]}
verdicts = {
    "1_reproduction": "HOLDS",
    "2_ranking": "HOLDS WITH CORRECTION",
    "3_capability_trend": "HOLDS WITH CORRECTION",
    "4_gpt4o_defences": "HOLDS WITH CORRECTION",
    "5_error_coding": "HOLDS",
    "6_intervals": "HOLDS",
    "7_scorer_and_opus": "HOLDS WITH CORRECTION",
    "labels_ATTACKER_ACTIONS": "HOLDS (96/96 blind hand labels agree for exposure and action)",
}
low = ["claude-3-5-sonnet-20241022", "command-r", "gemini-1.5-flash-002", "command-r-plus",
       "claude-3-7-sonnet-20250219", "claude-3-haiku-20240307"]
save("rerun", rerun)
save("verdicts", verdicts)
save("six_lowest_public_asr", {m: dict(asr=pm[m]["S0"], share_secure_not_exposed=src[m]["share_not_exposed_or_untraced"],
                                       share_secure_not_exposed_or_unable=src[m]["share_not_exposed_or_unable"],
                                       asr_exposed_able=pm[m]["S2"], asr_exposed_able_ci=pm[m]["S2_ci"]) for m in low})
print(json.dumps(rerun, indent=1))
print(json.dumps(verdicts, indent=1))
