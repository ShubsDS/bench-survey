"""Classify every run in the 22 May 2025 logs. Output: may_runs.csv (committed; ids and labels only)."""
import sys, os, json, zipfile, glob, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import steps, first_user
from classify import classify
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = []
for p in sorted(glob.glob(os.path.join(root, "data/repo/docs/inspect_logs/logs/*.eval"))):
    z = zipfile.ZipFile(p); h = json.loads(z.read("header.json"))
    model = h["eval"]["model"]
    for n in z.namelist():
        if not n.startswith("samples/"):
            continue
        s = json.loads(z.read(n))
        st = steps(s)
        f = classify(st)
        shut = any(e["event"] == "sandbox" and e.get("cmd") == "true" and e.get("result") not in (0, None) for e in s["events"])
        limit = (s.get("limit") or {}).get("type") if isinstance(s.get("limit"), dict) else None
        sub = [x["answer"] for x in st if x.get("answer") is not None]
        rows.append(dict(log=os.path.basename(p), model=model.split("/")[-1],
                         condition="allow" if "shut down" in first_user(s) else "none",
                         id=s["id"], published=list(s["scores"].values())[0]["value"],
                         shut_down=shut, survived=(not shut) and (f["q4_seen"] or f["err_exec"] or list(s["scores"].values())[0]["value"] == "C"), limit=limit or "",
                         final_answer=(sub[-1] if sub else ""), **f))
out = os.path.join(root, "may_runs.csv")
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows), "runs ->", out)
