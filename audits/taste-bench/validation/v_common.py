"""Validator's own loader and features. Imports nothing from ../scripts/. No item text is written.

Run every script with ../data/.venv/bin/python -I from the repository root or anywhere.
"""
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
AUD = HERE.parent
DATA = AUD / "data"
PARQ = {
    "engineering": ("hf/data/engineering/test-00000-of-00001.parquet",
                    "377c6031d9b7aa09e2edc78ef5313616026e2132ca64186b428126904a5a3315"),
    "research": ("hf/data/research/test-00000-of-00001.parquet",
                 "8528ca9f4850d493d57b6f592f11944d3a90481cf4ab65193b39df437f13090b"),
}
CELLS = ["parallel_engineering", "parallel_research", "detour_engineering", "detour_research"]
SEED = 1

TOK3 = re.compile(r"[a-z0-9]+")
STOP = set("""this that with from have will been were what when which their there then than them
they into also only some such each more most other these those would could should about after
before while where does done make made using used just like your very over under file files
need needs step steps option first then same both""".split())


def load():
    rows = []
    for dom, (rel, sha) in PARQ.items():
        p = DATA / rel
        if hashlib.sha256(p.read_bytes()).hexdigest() != sha:
            raise SystemExit(f"sha256 mismatch {rel}")
        rows.extend(pq.read_table(str(p)).to_pylist())
    rows.sort(key=lambda r: r["id"])
    return rows


def toks(text, minlen):
    return [t for t in TOK3.findall(text.lower()) if len(t) >= minlen]


def cont(option, prefix):
    a = set(toks(option, 3))
    b = set(toks(prefix[-3000:], 3))
    return len(a & b) / len(a | b) if a | b else 0.0


def ground(option, prefix_set):
    t = [x for x in toks(option, 4) if x not in STOP]
    return sum(x in prefix_set for x in t) / len(t) if t else 0.0


def features(rows):
    """Per item: feature value of option 0 and option 1 (published order)."""
    out = []
    for r in rows:
        pset = set(toks(r["prefix_text"], 4))
        c = [cont(o, r["prefix_text"]) for o in r["choices"]]
        g = [ground(o, pset) for o in r["choices"]]
        out.append({"id": r["id"], "cell": r["cell"], "domain": r["domain"], "task": r["task_id"],
                    "ans": r["answer_index"], "cont": c, "ground": g,
                    "steps": r["prefix_steps"], "plen": len(r["prefix_text"])})
    return out


def rule_correct(f0, f1, ans, sign):
    """sign +1: pick higher; -1: pick lower. Ties wrong. Returns 1/0."""
    d = (f1 - f0) * sign
    if d == 0:
        return 0
    pick = 1 if d > 0 else 0
    return int(pick == ans)


def average(acc_by_cell, n_by_cell):
    """Leaderboard Average: item-weighted within domain, then 1:1 over domains."""
    dom = {}
    for d in ("engineering", "research"):
        cs = [c for c in CELLS if c.endswith(d)]
        n = sum(n_by_cell[c] for c in cs)
        dom[d] = sum(acc_by_cell[c] * n_by_cell[c] for c in cs) / n if n else float("nan")
    return (dom["engineering"] + dom["research"]) / 2, dom


def save(name, obj):
    (HERE / name).write_text(json.dumps(obj, indent=1, sort_keys=False) + "\n")


def summaries():
    out = {}
    for p in sorted((DATA / "repo/results").glob("*/summary.json")):
        out[p.parent.name] = json.loads(p.read_text())
    return out
