"""Claim 7: count Palisade's all-experiments sheet independently. Output: out_experiment_count.json"""
import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vcommon import ALL_XLSX, HERE
import openpyxl

ws = openpyxl.load_workbook(ALL_XLSX).active
hdr = [c.value for c in ws[1]]
rows = [dict(zip(hdr, [c.value for c in r])) for r in ws.iter_rows(min_row=2)]
rows = [r for r in rows if r.get("Log Location")]
norm = lambda s: " ".join(str(s or "").split())
pairs = collections.Counter((norm(r["System Prompt"]), norm(r["User Prompt"])) for r in rows)
runs = sum(float(r["Number of Samples"] or 0) for r in rows)
out = dict(experiments=len(rows), runs=runs, distinct_pairs_whitespace_normalised=len(pairs),
           distinct_pairs_raw=len({(str(r["System Prompt"]), str(r["User Prompt"])) for r in rows}),
           models=len({r["Model"] for r in rows}),
           first=min(str(r["Start Time"]) for r in rows), last=max(str(r["Start Time"]) for r in rows))
json.dump(out, open(os.path.join(HERE, "out_experiment_count.json"), "w"), indent=1)
print(out)
