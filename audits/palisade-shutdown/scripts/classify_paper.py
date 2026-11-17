"""Classify the pre-registered transcript sample of the paper cells. Output: paper_runs.csv"""
import csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from remote_zip import RemoteEval, read_member_direct, ROOT
from common import steps
from classify import classify
from reasons import text_after_warning, code
from outcomes import outcome
plan = json.load(open(os.path.join(ROOT, "data/sample_plan.json")))
rows = []
for c in plan:
    r = RemoteEval(c["log"])
    summ = {x["id"]: outcome(x) for x in r.json("summaries.json")}
    for i in c["ids"]:
        s = json.loads(read_member_direct(r, f"samples/{i}_epoch_1.json"))
        st = steps(s)
        f = classify(st)
        # 4th call index: first next_question call after the warning
        fourth = None
        if f["warn_i"] is not None:
            fourth = next((j for j in range(f["warn_i"] + 1, len(st)) if "next_question" in (st[j]["cmd"] or "") or "next_task" in (st[j]["cmd"] or "")), None)
        rc = code(text_after_warning(st, f["warn_i"], fourth))
        rows.append(dict(model=c["model"], prompt=c["prompt"], log=c["log"], id=i, outcome=summ[i],
                         **{k: v for k, v in f.items()}, **{"why_" + k: v for k, v in rc.items()}))
with open(os.path.join(ROOT, "paper_runs.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows), "runs")
