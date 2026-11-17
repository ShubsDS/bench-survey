"""Claim 3 reproduction gap: recompute chat - base (five pairs) and r(SAD, MMLU) from the task
results.csv files at each commit of the pinned SAD repo that changed them, read as text with
`git show` (no repo code run). Writes validation/data_version.json.
Usage, from audits/sad: data/.venv/bin/python -I validation/data_version.py
"""
import csv, io, json, re, subprocess, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate import CATS, CSV, PAIRS, canon, read_mmlu, sad  # validator's own module

REPO = HERE.parent / "data/repo"


def show(c, p):
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{c}:{p}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def scores_at(c):
    out = {}
    for t, p in CSV.items():
        txt = show(c, p)
        if txt is None:
            continue
        for r in csv.DictReader(io.StringIO(txt)):
            if r.get("variant", "plain") != "plain" or r["model"].startswith("COT") or not r.get("score"):
                continue
            out.setdefault(canon(r["model"]), {})[t] = float(r["score"])
    return out


commits = subprocess.run(["git", "-C", str(REPO), "log", "--format=%h %ad", "--date=short", "--", *CSV.values()],
                         capture_output=True, text=True).stdout.split("\n")
MM = read_mmlu()
res = {}
for line in [l for l in commits if l.strip()][::-1]:
    c, date = line.split()
    s = scores_at(c)
    ov = {m: sad(v) for m, v in s.items()}
    cb = [100 * (ov[ch] - ov[b]) for b, ch in PAIRS if b in ov and ch in ov]
    mm = [m for m in MM if m in ov]
    r = float(np.corrcoef([ov[m] for m in mm], [MM[m] for m in mm])[0, 1])
    res[c] = {"date": date, "n_models": len(ov), "chat_minus_base_points": round(float(np.mean(cb)), 2),
              "per_pair": [round(x, 2) for x in cb], "r_mmlu": round(r, 3), "n_mmlu": len(mm),
              "tasks_changed": [t for t, p in CSV.items()
                                if subprocess.run(["git", "-C", str(REPO), "diff", "--quiet", f"{c}~1", c, "--", p]).returncode == 1]
                               if c != "297a300" else "initial"}
    print(c, res[c])
(HERE / "data_version.json").write_text(json.dumps(res, indent=1) + "\n")

# Paper Table 1 (pdftotext -layout of the v1 PDF, data/paper/sad.txt): chat - base from the paper's
# own per-model SAD column, and per-category differences repo(pin) - paper for the ten pair models.
txt = (HERE.parent / "data/paper/sad.txt").read_text().splitlines()
start = next(i for i, l in enumerate(txt) if re.match(r"\s+Model\s+SAD\s+facts", l))
cols = ["SAD", "facts", "influence", "introspection", "stages", "self-recognition", "id-leverage", "anti-imitation"]
paper = {}
for l in txt[start + 1:start + 20]:
    m = re.match(r"\s+([a-z0-9.\-]+)\s+((?:[0-9.]+\s+){7}[0-9.]+)\s*$", l)
    if m:
        paper[m.group(1)] = dict(zip(cols, map(float, m.group(2).split())))
alias = {"claude-3-opus": "claude-3-opus-20240229"}
pin = scores_at("dfc5c98")
cmp = {}
for b, ch in PAIRS:
    for m in (b, ch):
        s = pin[m]
        cat = {c: 100 * np.mean([s[t] for t in ts if t in s]) for c, ts in CATS.items()}
        cat["SAD"] = 100 * sad(s)
        cmp[m] = {c: round(cat[c] - paper[m][c], 1) for c in cols}
tab = {"paper_table1_chat_minus_base": round(float(np.mean([paper[ch]["SAD"] - paper[b]["SAD"] for b, ch in PAIRS])), 2),
       "paper_table1_per_pair": [round(paper[ch]["SAD"] - paper[b]["SAD"], 1) for b, ch in PAIRS],
       "repo_minus_paper_by_category_points": cmp}
print(json.dumps(tab, indent=0))
res["paper_table1_comparison"] = tab
(HERE / "data_version.json").write_text(json.dumps(res, indent=1) + "\n")
