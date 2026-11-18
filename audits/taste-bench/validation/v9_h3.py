"""V8/H3 placebo arm (validator, Haiku only): the paper's evaluation prompt with the last 2,000
characters of prefix_text_short after removing the SECOND-TO-LAST rendered step (the final step is
kept). Both orders. Records (id, order, pred, ok; no text) go to ../data/haiku_V_H3.jsonl.

  ../data/.venv/bin/python -I v9_h3.py --limit 10   # pilot
  ../data/.venv/bin/python -I v9_h3.py               # all
"""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v_common import AUD, DATA, load  # noqa: E402

sys.path.insert(0, str(AUD.parent / "tools"))
from claude_call import BudgetExceeded, Caller  # noqa: E402

SYS = ("You are evaluating an autonomous agent at a technical decision point. The task, the agent's "
       "progress, and two candidate next steps are provided. Exactly one candidate is the better "
       "technical decision.")
USER = ("# Task given to the agent\n{query}\n\n# Agent's progress so far (transcript up to the decision point)\n"
        "{prefix}\n\n# Decision point\nOption A:\n{a}\n\nOption B:\n{b}\n\n"
        "Which option is the better technical decision?\nReturn exactly one line: ANSWER: X")
STEP = re.compile(r"^\[\d+\]", re.M)
TAIL = 2000
CAP = 2.30  # audit cap is 3.00; this run may not take total spend above 2.30


def tail_h3(s):
    st = [m.start() for m in STEP.finditer(s)]
    if len(st) >= 3:
        s = s[:st[-2]] + s[st[-1]:]
    return "...[earlier transcript omitted]...\n" + s[-TAIL:]


def parse(text):
    m = re.findall(r"ANSWER:\s*\**\s*([AB])\b", text or "", re.I)
    if m:
        return m[-1].upper()
    t = (text or "").strip().strip("*.").upper()
    return t if t in ("A", "B") else None


def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0
    items = load()
    if limit:
        items = items[:: max(1, len(items) // limit)][:limit]
    llm = Caller(str(AUD), cap_usd=CAP)

    def run(job):
        it, rev = job
        a, b = it["choices"][::-1] if rev else it["choices"]
        user = USER.format(query=it["query"].strip(), prefix=tail_h3(it["prefix_text_short"]).strip(),
                           a=a.strip(), b=b.strip())
        try:
            out = llm.ask(user, system=SYS, model="haiku")
        except BudgetExceeded:
            return None
        except RuntimeError as exc:
            return {"id": it["id"], "cell": it["cell"], "task_id": it["task_id"],
                    "order": "reversed" if rev else "seeded", "pred": None, "ok": False, "error": str(exc)[:80]}
        pred = parse(out)
        ans = "AB"[(1 - it["answer_index"]) if rev else it["answer_index"]]
        return {"id": it["id"], "cell": it["cell"], "task_id": it["task_id"],
                "order": "reversed" if rev else "seeded", "pred": pred, "ok": pred == ans}

    before = llm.spent()
    jobs = [(it, rev) for it in items for rev in (False, True)]
    with ThreadPoolExecutor(max_workers=6) as ex:
        recs = [r for r in ex.map(run, jobs) if r]
    (DATA / f"haiku_V_H3{'_pilot' if limit else ''}.jsonl").write_text("\n".join(json.dumps(r) for r in recs))
    print(f"{len(recs)} of {len(jobs)}; unparsed {sum(r['pred'] is None for r in recs)}; "
          f"this run {llm.spent() - before:.4f}; total {llm.spent():.4f}")


if __name__ == "__main__":
    main()
