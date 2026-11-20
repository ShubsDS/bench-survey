"""Validator, claim 2: does any LABBench2 report case show a multiple-choice format?

Own scan, written without reading scripts/lb2.py. Reads every JSON under
data/labbench2_gh/assets/reports_paper/ (GitHub EdisonScientific/labbench2 @ 5eafca56) and applies
several independent patterns to each case's question text. Writes counts only (no item text).
Run: ../lab-bench/data/.venv/bin/python -I validation/v3_lb2_format.py
"""
import collections
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent / "data" / "labbench2_gh" / "assets" / "reports_paper"
PATS = {
    "letter_list_3plus": re.compile(r"(?m)^\s*\(?[A-H][\).:]\s+\S.*\n\s*\(?[B-H][\).:]\s+\S.*\n\s*\(?[C-H][\).:]\s+\S"),
    "inline_letters": re.compile(r"\(A\).{1,300}\(B\).{1,300}\(C\)", re.S),
    "options_word": re.compile(r"(?i)\b(answer choices|options:|choices:|select one of|which of the following)\b"),
    "insufficient_info": re.compile(r"(?i)insufficient information"),
}


def text_of(case):
    for k in ("inputs", "input", "question"):
        v = case.get(k)
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            for kk in ("question", "prompt", "input"):
                if isinstance(v.get(kk), str):
                    return v[kk]
            return json.dumps(v)
    return json.dumps(case)[:20000]


def main():
    files = sorted(ROOT.rglob("*.json"))
    n_cases = 0
    hits = {k: collections.Counter() for k in PATS}
    uniq = set()
    tags = collections.Counter()
    for f in files:
        d = json.loads(f.read_text())
        tag = f.relative_to(ROOT).parts[0]
        for c in d.get("cases", []):
            n_cases += 1
            tags[tag] += 1
            t = text_of(c)
            uniq.add((tag, hash(t)))
            for k, p in PATS.items():
                if p.search(t):
                    hits[k][tag] += 1
    out = {"files": len(files), "cases": n_cases, "unique_question_texts": len(uniq),
           "cases_by_tag": dict(tags), "hits_by_pattern_and_tag": {k: dict(v) for k, v in hits.items()}}
    print(json.dumps(out, indent=1))
    (HERE / "v3_lb2_format.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
