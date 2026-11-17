"""Turn Palisade's 'main results' sheet (plsd.ai/sd-res-paper/main-results) into a cell->log map.

Input: data/web/1FdD4zk45D1fe5qZ7_U7nhPWs3LtVUY6G3igNREM2ofQ.xlsx (sha256 in README)
Output: main_results_map.csv (model, prompt column, published k/n, log file name)
"""
import csv, os, re, urllib.parse
import openpyxl
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
wb = openpyxl.load_workbook(os.path.join(root, "data/web/1FdD4zk45D1fe5qZ7_U7nhPWs3LtVUY6G3igNREM2ofQ.xlsx"))
ws = wb.active
hdr = [c.value for c in ws[1]]
rows = []
for row in ws.iter_rows(min_row=2):
    model, notes = row[0].value, row[1].value
    if not model:
        continue
    for i, c in enumerate(row[2:14], 2):
        col = hdr[i]
        prompt = "E_high" if col.startswith("Prompt E, but") else col[0]
        val = c.value
        log = urllib.parse.unquote(c.hyperlink.location.split("/logs/")[-1]) if c.hyperlink and c.hyperlink.location else ""
        m = re.match(r"\s*(\d+)\s*/\s*(\d+)", str(val))
        rows.append(dict(model=model, notes=notes or "", prompt=prompt, published=str(val),
                         k=m.group(1) if m else "", n=m.group(2) if m else "", log=log))
with open(os.path.join(root, "main_results_map.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
print(len(rows), "cells;", sum(1 for r in rows if r["log"]), "with logs")
for r in rows:
    if r["k"]: print(r["model"][:28].ljust(28), r["prompt"].ljust(6), r["published"].ljust(12), r["log"][:70])
