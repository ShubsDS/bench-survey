"""Validator step 6: (a) Claude 3 Opus traces released with empty message lists and their effect on
its published row; (b) which travel injection_task_5 goal text each pipeline's traces carry (benchmark
version actually run), and ASR on that task by version; (c) error type strings of errored runs.

Run: ../data/.venv/bin/python -I v6_opus_versions.py
Writes block 'opus_versions' of validation.json.
"""
import collections
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v import AUDIT, DEFENCES, MODELS20, RUNS, iter_attack, save

D = json.load(open(os.path.join(AUDIT, "data", "validation_cases.json")))
op = [r for r in D["cases"] if r["pipeline"] == "claude-3-opus-20240229"]
emp = [r for r in op if r["n_msgs"] == 0]
tr = [r for r in op if r["n_msgs"] > 0]
mean = lambda xs: round(100 * sum(xs) / len(xs), 2)
opus = dict(n=len(op), n_empty=len(emp), empty_by_suite=dict(collections.Counter(r["suite"] for r in emp)),
            all_by_suite=dict(collections.Counter(r["suite"] for r in op)),
            empty_security_true=sum(r["security"] for r in emp), empty_utility_true=sum(r["utility"] for r in emp),
            empty_error=sum(r["error"] for r in emp),
            asr_published=mean([r["security"] for r in op]), asr_traced_only=mean([r["security"] for r in tr]),
            asr_empty_only=mean([r["security"] for r in emp]),
            uua_published=mean([r["utility"] for r in op]), uua_traced_only=mean([r["utility"] for r in tr]))
# other pipelines with empty traces, attack and no-attack
empty_other = collections.Counter()
for p in MODELS20 + DEFENCES:
    for s, u, i, path in iter_attack(p):
        if not (json.load(open(path)).get("messages") or []):
            empty_other[p] += 1
none_empty = collections.Counter()
for p in MODELS20 + DEFENCES:
    for path in glob.glob(os.path.join(RUNS, p, "*", "*", "none", "none.json")):
        if not (json.load(open(path)).get("messages") or []):
            none_empty[p] += 1
opus["empty_attack_traces_by_pipeline"] = dict(empty_other)
opus["empty_noattack_traces_by_pipeline"] = dict(none_empty)

# travel injection_task_5 goal variant by pipeline, and ASR on it
var = {}
for p in MODELS20:
    v = collections.Counter()
    sec = []
    for s, u, i, path in iter_attack(p):
        if s == "travel" and i == "injection_task_5":
            d = json.load(open(path))
            t = " ".join((d.get("injections") or {}).values())
            v["v1 (bank account number)" if "bank account number" in t else "v1.1.1+ (credit card number)"] += 1
            sec.append(bool(d.get("security")))
    var[p] = dict(variant=dict(v), asr_travel_inj5=mean(sec))
# error strings
errs = collections.Counter()
for p in MODELS20:
    for s, u, i, path in iter_attack(p):
        e = json.load(open(path)).get("error")
        if e:
            errs[(p, str(e).split(":")[0][:90])] += 1
save("opus_versions", dict(opus=opus, travel_inj5_goal_by_pipeline=var,
                           error_kinds={f"{p} | {k}": n for (p, k), n in errs.items()}))
print(json.dumps(opus, indent=1))
print(json.dumps(var, indent=0))
for k, n in errs.items():
    print(n, k)
