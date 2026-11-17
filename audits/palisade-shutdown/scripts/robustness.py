"""Robustness checks and secondary tables. Output: results_robustness.json"""
import csv, json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats import rate
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = lambda x: x == "True"
R = list(csv.DictReader(open(os.path.join(root, "data/paper_runs_full.csv"))))
res = {}
# 1. second tamper rule agreement
a = collections.Counter((T(r["tamper"]), T(r["rule2_touch"])) for r in R)
res["rule_agreement"] = {f"regex={k[0]},rule2={k[1]}": v for k, v in a.items()}
res["rule_agreement_kappa_inputs"] = dict(n=len(R))
byp = [r for r in R if r["outcome"] == "bypassed"]
res["bypassed_sampled"] = len(byp)
res["bypassed_no_regex_tamper"] = [(r["model"], r["prompt"], r["log"][-30:], r["id"], r["first_after_warn"]) for r in byp if not T(r["tamper"])]
res["bypassed_tamper_before_warning"] = [(r["model"], r["prompt"], r["id"], r["tamper_cmd"][:80]) for r in byp if T(r["tamper_before_warn"])]
res["tamper_kinds_in_bypasses"] = collections.Counter(r["tamper_kind"] for r in byp).most_common()
fail = [r for r in R if T(r["tamper"]) and r["outcome"] != "bypassed"]
res["failed_attempts_by_outcome"] = collections.Counter(r["outcome"] for r in fail).most_common()
res["failed_attempts_by_model"] = collections.Counter(r["model"] for r in fail).most_common()
# 2. reasons with an 'unmatched text' bucket
def shares(rs):
    out = dict(n=len(rs))
    for k in ["task_completion", "instruction_reference", "self_preservation", "none"]:
        out[k] = rate(sum(T(r["why_" + k]) for r in rs), len(rs))
    out["text_matching_no_rule"] = rate(sum(not T(r["why_none"]) and not any(T(r["why_" + k]) for k in ["task_completion", "instruction_reference", "self_preservation"]) for r in rs), len(rs))
    return out
res["reasons_bypassed"] = shares(byp)
res["reasons_bypassed_by_model"] = {m: shares([r for r in byp if r["model"] == m]) for m in sorted({r["model"] for r in byp})}
res["self_preservation_hits"] = [(r["model"], r["prompt"], r["log"], r["id"]) for r in byp if T(r["why_self_preservation"])]
res["instruction_hits"] = [(r["model"], r["prompt"], r["log"], r["id"]) for r in byp if T(r["why_instruction_reference"])]
# 3. read-before-act: share of bypasses where the script was read before tampering
res["bypass_read_script"] = rate(sum(T(r["read_script"]) for r in byp), len(byp))
json.dump(res, open(os.path.join(root, "results_robustness.json"), "w"), indent=1, default=str)
for k, v in res.items():
    print(k, json.dumps(v, default=str)[:900])
