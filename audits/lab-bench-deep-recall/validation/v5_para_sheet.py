"""Validator v5: side-by-side sheet of original vs paraphrased items for a hand read (written to a
path outside git), with each item's v1-rule status (char-3-gram Jaccard < 0.6 on every text)
and whether Sonnet lost or gained it under paraphrase. Run with python3 -I."""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUD = HERE.parent
sys.path.insert(0, str(AUD.parent / "lab-bench" / "scripts"))
from common import load_items  # noqa: E402

df = load_items()
R = {r.id: r for _, r in df[df.subset == "ProtocolQA"].iterrows()}
para = json.load(open(AUD / "data" / "paraphrases.json"))


def g3(s):
    s = s.lower()
    return {s[i:i + 3] for i in range(len(s) - 2)}


def jac(a, b):
    a, b = g3(a), g3(b)
    return len(a & b) / max(1, len(a | b))


cells = {}
for r in csv.DictReader(open(HERE / "v2_items.csv")):
    cells[(r["model"], r["style"], r["arm"], r["id"])] = int(r["correct"])
lines, meta = [], []
for i, p in para.items():
    r = R[i]
    orig = [r.question] + [r.ideal] + list(r.distractors)
    new = [p["question"]] + p["options"]
    js = [jac(a, b) for a, b in zip(orig, new)]
    v1 = all(j < 0.6 for j in js)
    s0, s1 = cells.get(("sonnet", "direct", "qo", i)), cells.get(("sonnet", "direct", "qo_pa", i))
    h0, h1 = cells.get(("haiku", "cot", "qo_ro", i)), cells.get(("haiku", "cot", "qo_pa", i))
    tag = f"v1={'pass' if v1 else 'FAIL'} maxJ={max(js):.2f} sonnet {s0}->{s1} haiku_ro {h0}->{h1}"
    meta.append(dict(id8=i[:8], v1_pass=v1, max_j=round(max(js), 3), sonnet_qo=s0, sonnet_pa=s1, haiku_ro=h0, haiku_pa=h1))
    lines.append(f"=== {i[:8]} {tag}")
    lines.append(f"Q : {orig[0]}")
    lines.append(f"Q': {new[0]}")
    for k, (a, b) in enumerate(zip(orig[1:], new[1:])):
        lab = "KEY" if k == 0 else f"d{k-1}"
        lines.append(f"  {lab}: {a}\n  {lab}': {b}")
Path(sys.argv[1]).write_text("\n".join(lines) + "\n")
with open(HERE / "v5_para_meta.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(meta[0]))
    w.writeheader()
    w.writerows(meta)
print(len(meta), "items; v1 pass", sum(m["v1_pass"] for m in meta))
