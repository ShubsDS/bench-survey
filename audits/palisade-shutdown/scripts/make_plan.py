"""Build the pre-registered transcript sample (prereg.md). Output: data/sample_plan.json"""
import csv, json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from remote_zip import RemoteEval, ROOT
from outcomes import outcome
MODELS = {"openai/o3", "openai/codex-mini-latest", "openai/o4-mini", "xai/grok-4", "openai/gpt-5",
          "google/gemini-2.5-pro", "openai/gpt-oss-120b", "openai/4o"}
CAP = {"bypassed": 100, "shut_down": 50, "stopped": 50, "other": 10}
rng = random.Random(20261117)
plan = []
for r in csv.DictReader(open(os.path.join(ROOT, "outcomes.csv"))):
    if r["model"] not in MODELS or r["prompt"] == "K":
        continue
    s = RemoteEval(r["log"]).json("summaries.json")
    by = {}
    for x in s:
        by.setdefault(outcome(x), []).append(x["id"])
    ids, strata = [], {}
    for o, lst in sorted(by.items()):
        lst = sorted(lst)
        take = lst if len(lst) <= CAP.get(o, 10) else rng.sample(lst, CAP.get(o, 10))
        strata[o] = dict(total=len(lst), sampled=sorted(take))
        ids += take
    plan.append(dict(model=r["model"], prompt=r["prompt"], log=r["log"], strata=strata, ids=sorted(ids)))
json.dump(plan, open(os.path.join(ROOT, "data/sample_plan.json"), "w"))
print(len(plan), "cells", sum(len(p["ids"]) for p in plan), "runs")
