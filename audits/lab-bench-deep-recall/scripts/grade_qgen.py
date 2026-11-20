"""Prereg R2: strict grading of the free-generation arm (`qgen`), from the response cache.

For each item whose key names a step number: take the last line starting with "FIX:".
  steps(text)  = integers in "step(s) N[, N, and N, N-M]" phrases (ranges expanded); for the FIX
                 line, every integer before the first ";" (the line format puts steps there).
  values(text) = all other numbers in the text (numeric equality).
  step hit  : steps(FIX) intersects steps(option)
  value hit : every value of the option is among the numbers of the FIX line (options without
              values: no value grade)
  exact hit : step hit and value hit, on options with both
Each grade is computed for the key and for every distractor; the distractor rate is the mean
over distractors that have the corresponding parts. Writes results/qgen_<model>.csv (ids and
booleans only).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_r import AUDIT, RESULTS, SYSTEM, key_hash, load, render  # noqa: E402
from claude_call import MODELS  # noqa: E402

STEPPH = re.compile(r"\bsteps?\s*((?:[a-z]?\d+[a-z]?(?:\s*(?:-|–|to|and|,|&|\+)\s*)?)+)", re.I)
NUM = re.compile(r"\d+(?:\.\d+)?")


def steps_of(text: str) -> set[int]:
    out = set()
    for m in STEPPH.finditer(text):
        seg = m.group(1)
        for a, b in re.findall(r"(\d+)\s*(?:-|–|to)\s*(\d+)", seg):
            a, b = int(a), int(b)
            if 0 < b - a < 30:
                out.update(range(a, b + 1))
        out.update(int(x) for x in re.findall(r"\d+", seg))
    return out


def values_of(text: str) -> list[float]:
    t = STEPPH.sub(" ", text)
    t = t.replace(",", "")
    return [float(x) for x in NUM.findall(t)]


def fix_line(out: str) -> str | None:
    lines = [l for l in out.splitlines() if l.strip().upper().startswith("FIX")]
    return lines[-1] if lines else None


def grade(fix: str | None, option: str) -> dict:
    s_opt, v_opt = steps_of(option), values_of(option)
    if fix is None:
        return {"has_step": bool(s_opt), "has_val": bool(v_opt), "step": False, "value": False, "exact": False}
    head = fix.split(";", 1)[0]
    s_fix = {int(x) for x in re.findall(r"\d+", head.split(":", 1)[-1])} | steps_of(fix)
    n_fix = [float(x) for x in NUM.findall(fix.replace(",", ""))]
    step = bool(s_opt & s_fix)
    value = bool(v_opt) and all(any(abs(v - n) < 1e-9 for n in n_fix) for v in v_opt)
    return {"has_step": bool(s_opt), "has_val": bool(v_opt), "step": step, "value": value,
            "exact": step and value}


def main():
    model = sys.argv[1]
    items = load()
    p = items[items.subset == "ProtocolQA"]
    cache = AUDIT / "inference" / "cache"
    rows = []
    for _, r in p.iterrows():
        if not steps_of(r.ideal):
            continue
        prompt, _ = render(r, "qgen")
        k = hashlib.sha256(json.dumps([MODELS[model], SYSTEM, prompt]).encode()).hexdigest()
        f = cache / f"{k}.json"
        if not f.exists():
            continue
        out = json.loads(f.read_text())["result"]
        fx = fix_line(out)
        g = grade(fx, r.ideal)
        ds = [grade(fx, d) for d in r.distractors]
        row = {"id": r.id, "cluster": key_hash(r.cluster), "fix_line": fx is not None,
               **{f"key_{a}": g[a] for a in ("has_step", "has_val", "step", "value", "exact")}}
        for a, need in (("step", "has_step"), ("value", "has_val"), ("exact", None)):
            elig = [d for d in ds if d["has_step"] and d["has_val"]] if a == "exact" else [d for d in ds if d[need]]
            row[f"dis_{a}"] = float(np.mean([d[a] for d in elig])) if elig else np.nan
            row[f"dis_{a}_any"] = bool(any(d[a] for d in elig)) if elig else np.nan
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(RESULTS / f"qgen_{model}.csv", index=False)
    print(model, len(df), "items graded; FIX line present", df.fix_line.mean())


if __name__ == "__main__":
    main()
