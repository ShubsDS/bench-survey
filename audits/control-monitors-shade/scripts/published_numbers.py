"""Extract the AUROC / TPR@1%FPR tables that the MRT authors' own notebooks printed (stored outputs),
from scaleapi/mrt@3535620 notebooks/final/*_comparison_table.ipynb. These are the numbers behind the
paper's Figure 4 (Claude 3.6 Sonnet monitor). Reads JSON only; runs nothing.
Usage: python -I scripts/published_numbers.py data/mrt-code > published_numbers.json"""
import json, re, sys
from pathlib import Path
root = Path(sys.argv[1]) / "notebooks/final"
out = {"source": "scaleapi/mrt@3535620b2bdf0dc1e6140f6fbe198399aac2c74f notebooks/final (stored cell outputs)"}
row = re.compile(r"^\s*(\d+)\s+(\S+)\s+([UA]) - (\w+) \(([UAO])\)\s+([\d.]+)")
for nb in ["unaware_aware_comparison_table", "agentcompany_unaware_aware_comparison_table"]:
    d = json.load(open(root / f"{nb}.ipynb"))
    rows = {}
    for c in d["cells"]:
        if c["cell_type"] != "code" or "auc_results.append" not in "".join(c["source"]):
            continue
        for o in c.get("outputs", []):
            txt = "".join(o.get("data", {}).get("text/plain", []))
            for line in txt.splitlines():
                m = row.match(line)
                if m:
                    _, agent, att, scaf, mon, auc = m.groups()
                    rows.setdefault(f"{agent}|{att}-{scaf}({mon})", float(auc))
        break
    out[nb] = rows
print(json.dumps(out, indent=1))
