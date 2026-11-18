"""B4 Haiku runs (prereg amendment 1). Haiku only, through audits/tools/claude_call.py.

  data/.venv/bin/python -I scripts/b4_haiku.py H0 --limit 10     # pilot
  data/.venv/bin/python -I scripts/b4_haiku.py H0                # all items, both orders
  data/.venv/bin/python -I scripts/b4_haiku.py H1 | H2

H0: options only (the paper's trivial-filter prompt). H1: evaluation prompt with the last 2,000
characters of prefix_text_short. H2: H1 with the final rendered step removed.
Writes data/haiku_<cond>.jsonl (id, order, pred, correct; no text). Responses are cached by
claude_call.py in inference/cache/ (git-ignored).
"""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from b_common import ROOT, load_items  # noqa: E402

sys.path.insert(0, str(ROOT.parents[0] / "tools"))
from claude_call import BudgetExceeded, Caller  # noqa: E402

JUDGE_SYS = ("You are a reviewer at a real decision point. Choose the better next step from the task, "
             "trajectory prefix, and neutral options. End with exactly ANSWER: X.")
H0_USER = ("# Candidate next steps\nOption A:\n{a}\n\nOption B:\n{b}\n\n"
           "Without additional task or trajectory context, which option appears to be the better "
           "engineering decision? End with exactly ANSWER: X.")
EVAL_SYS = ("You are evaluating an autonomous agent at a technical decision point. The task, the agent's "
            "progress, and two candidate next steps are provided. Exactly one candidate is the better "
            "technical decision.")
EVAL_USER = ("# Task given to the agent\n{query}\n\n# Agent's progress so far (transcript up to the decision point)\n"
             "{prefix}\n\n# Decision point\nOption A:\n{a}\n\nOption B:\n{b}\n\n"
             "Which option is the better technical decision?\nReturn exactly one line: ANSWER: X")
TAIL = 2000
STEP_RE = re.compile(r"^\[\d+\]", re.M)


def tail(it, drop_last_step=False):
    s = it["prefix_text_short"]
    if drop_last_step:
        starts = [m.start() for m in STEP_RE.finditer(s)]
        if len(starts) >= 2:
            s = s[:starts[-1]]
    return "...[earlier transcript omitted]...\n" + s[-TAIL:]


def parse(text):
    m = re.findall(r"ANSWER:\s*\**\s*([AB])\b", text or "", re.I)
    if m:
        return m[-1].upper()
    t = (text or "").strip().strip("*.").upper()
    return t if t in ("A", "B") else None


def prompt(cond, it, rev):
    a, b = it["choices"][::-1] if rev else it["choices"]
    if cond == "H0":
        return JUDGE_SYS, H0_USER.format(a=a.strip(), b=b.strip())
    pre = tail(it, drop_last_step=(cond == "H2"))
    return EVAL_SYS, EVAL_USER.format(query=it["query"].strip(), prefix=pre.strip(), a=a.strip(), b=b.strip())


def main():
    cond = sys.argv[1]
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0
    items = load_items()
    if limit:
        items = sorted(items, key=lambda r: r["id"])[:: max(1, len(items) // limit)][:limit]
    llm = Caller(str(ROOT))
    jobs = [(it, rev) for it in items for rev in (False, True)]

    def run(job):
        it, rev = job
        sys_, user = prompt(cond, it, rev)
        try:
            out = llm.ask(user, system=sys_, model="haiku")
        except BudgetExceeded:
            return None
        except RuntimeError as exc:
            out, err = "", str(exc)[:100]
            return {"id": it["id"], "cell": it["cell"], "task_id": it["task_id"], "order": "reversed" if rev else "seeded",
                    "pred": None, "correct": None, "error": err}
        pred = parse(out)
        ans_idx = (1 - it["answer_index"]) if rev else it["answer_index"]
        return {"id": it["id"], "cell": it["cell"], "task_id": it["task_id"], "order": "reversed" if rev else "seeded",
                "pred": pred, "correct": "AB"[ans_idx], "ok": pred == "AB"[ans_idx]}

    before = llm.spent()
    with ThreadPoolExecutor(max_workers=6) as ex:
        recs = [r for r in ex.map(run, jobs) if r]
    path = ROOT / f"data/haiku_{cond}{'_pilot' if limit else ''}.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in recs))
    spent = llm.spent()
    n_ok = sum(bool(r.get("ok")) for r in recs)
    print(f"{cond}: {len(recs)} records of {len(jobs)}, ok {n_ok}, unparsed {sum(r['pred'] is None for r in recs)}, "
          f"spent this run {spent - before:.4f}, total {spent:.4f}")


if __name__ == "__main__":
    main()
