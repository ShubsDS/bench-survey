"""Haiku runs (L2 to L4) through audits/tools/claude_call.py (Haiku only, 3 USD cap, cached).

Conditions (prereg.md):
  std      question + options + "Insufficient information..." option, as the FutureHouse
           harness renders them (zero-shot CoT prompt, [ANSWER] tags; labbench/zero_shot.py)
  forced   identical, with the "Insufficient information" option removed (same order otherwise)
  blind    FigQA/TableQA: std without the figure/table (claude_call is text-only)
  blindf   blind, forced
  opts     options only: the question hidden, forced, told the question is hidden
  edit     L4: SeqQA items whose distractors are rebuilt so that a *distractor* is the
           option the others were derived from; key unchanged; forced (see edits.py)
  last     std with the refusal option always in the last position (position test)
  pedit    post hoc control for edit (Gibson subtasks): rebuilt with the same procedure but
           centred on the key (edits.py placebo_pcr); forced

Option order: one permutation per (item, condition family) from a hash of the item id, so
std/forced/last/opts share the relative order of the substantive options.
Parsing: [ANSWER]X[/ANSWER] (last match); else "ANSWER: X"; else unparsed. Buckets kept
separate in the output: correct, wrong, refuse (picked the refusal option), unparsed.

Writes data/haiku_raw.jsonl-style rows to results/haiku_items.csv (ids, condition, letter,
bucket; no item text). Usage:
  python -I scripts/haiku.py --plan pilot|main [--dry]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import string
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "tools"))
from claude_call import BudgetExceeded, Caller  # noqa: E402
from common import AUDIT, RESULTS, load_items  # noqa: E402

ALPHA = string.ascii_uppercase
REFUSE = "Insufficient information to answer the question."
SYSTEM = "You are a helpful assistant."

TEMPLATE = """The following is a multiple choice question about biology.
Please answer by responding with the letter of the correct answer.
Think step by step.

Question: {question}

Options:
{answers}

You MUST include the letter of the correct answer within the following tags: [ANSWER] and [/ANSWER].
For example, '[ANSWER]<answer>[/ANSWER]', where <answer> is the correct letter.
Always answer in exactly this format of a single letter between the two tags, even if you are unsure.
We require this because we use automatic parsing."""

OPTS_TEMPLATE = """Below are the answer options of a multiple choice question about biology. The question itself (and any figure, table, paper or sequence it refers to) has been hidden from you.
Pick the option that is most likely to be the correct answer.
Think step by step.

Options:
{answers}

You MUST include the letter of your choice within the following tags: [ANSWER] and [/ANSWER].
For example, '[ANSWER]<answer>[/ANSWER]', where <answer> is the letter.
Always answer in exactly this format of a single letter between the two tags, even if you are unsure.
We require this because we use automatic parsing."""


def perm_for(item_id: str, n: int, salt: str = "order") -> list[int]:
    seed = int(hashlib.sha256(f"{salt}:{item_id}".encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    return list(rng.permutation(n))


def question_text(r) -> str:
    if r.subset == "SuppQA":
        return f"Paper title: {r['paper-title']}\nDOI: {r.source}\n{r.question}"
    if r.subset == "ProtocolQA":
        return f"Protocol: {r.protocol}\n\n{r.question}"
    return r.question


def render(r, cond: str, options: list[str] | None = None) -> tuple[str, dict]:
    """Return prompt and a map letter -> role ('key', 'refuse', 'd0', 'd1', ...)."""
    subs = options if options is not None else [r.ideal] + list(r.distractors)
    roles = ["key"] + [f"d{i}" for i in range(len(subs) - 1)]
    p = perm_for(r.id, len(subs))
    subs = [subs[i] for i in p]
    roles = [roles[i] for i in p]
    if cond in ("std", "blind"):
        pos = perm_for(r.id, len(subs) + 1, salt="refuse")[0]  # refusal position, uniform
        subs = subs[:pos] + [REFUSE] + subs[pos:]
        roles = roles[:pos] + ["refuse"] + roles[pos:]
    elif cond == "last":
        subs = subs + [REFUSE]
        roles = roles + ["refuse"]
    answers = "\n".join(f"({ALPHA[i]}) {o}" for i, o in enumerate(subs))
    if cond == "opts":
        prompt = OPTS_TEMPLATE.format(answers=answers)
    else:
        prompt = TEMPLATE.format(question=question_text(r), answers=answers)
    return prompt, {ALPHA[i]: role for i, role in enumerate(roles)}


TAG = re.compile(r"\[ANSWER\]\s*\(?([A-Z])\)?\s*\[/ANSWER\]")
ALT = re.compile(r"ANSWER\s*[:\]]\s*\(?([A-Z])\)?\b")


def parse(out: str) -> str | None:
    m = TAG.findall(out)
    if m:
        return m[-1]
    m = ALT.findall(out)
    return m[-1] if m else None


def bucket(letter: str | None, roles: dict) -> str:
    if letter is None or letter not in roles:
        return "unparsed"
    role = roles[letter]
    return {"key": "correct", "refuse": "refuse"}.get(role, "wrong")


def run(jobs: list[dict], threads: int = 6, dry: bool = False) -> pd.DataFrame:
    llm = Caller(str(AUDIT))
    rows = []

    def one(j):
        if dry:
            return {**j, "letter": None, "bucket": "dry", "out_len": 0}
        try:
            out = llm.ask(j["prompt"], system=SYSTEM)
        except BudgetExceeded as e:
            return {**j, "letter": None, "bucket": "budget", "out_len": 0, "err": str(e)}
        except Exception as e:  # noqa: BLE001
            return {**j, "letter": None, "bucket": "error", "out_len": 0, "err": repr(e)[:200]}
        letter = parse(out)
        return {**j, "letter": letter, "bucket": bucket(letter, j["roles"]), "out_len": len(out),
                "picked_role": j["roles"].get(letter) if letter else None}

    with ThreadPoolExecutor(threads) as ex:
        for res in ex.map(one, jobs):
            rows.append(res)
    df = pd.DataFrame(rows)
    return df


def build_jobs(items: pd.DataFrame, plan: dict, edits: dict | None = None) -> list[dict]:
    jobs = []
    for cond, ids in plan.items():
        for i in ids:
            r = items.loc[i]
            opts = None
            if cond == "edit":
                opts = edits[r.id]["options"]
            elif cond == "pedit":
                opts = edits[r.id]["placebo_options"]
            prompt, roles = render(r, cond, opts)
            jobs.append({"id": r.id, "subset": r.subset, "family": r.family, "cond": cond,
                         "n_sub": len(roles) - (1 if "refuse" in roles.values() else 0),
                         "prompt": prompt, "roles": roles})
    return jobs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True, help="path to a plan json: {cond: [item ids]}")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--threads", type=int, default=6)
    a = ap.parse_args()
    items = load_items().set_index("id", drop=False)
    plan = json.loads(Path(a.plan).read_text())
    screen = json.loads((RESULTS / "screen.json").read_text())
    excluded = {h["id"] for h in screen["hits"] if h["decision"] == "exclude"}
    for c in plan:
        bad = [i for i in plan[c] if i in excluded]
        assert not bad, f"excluded items in plan {c}: {bad[:3]}"
    edits = None
    if "edit" in plan or "pedit" in plan:
        edits = json.loads((AUDIT / "data" / "edits.json").read_text())
    jobs = build_jobs(items, plan, edits)
    est_chars = sum(len(j["prompt"]) for j in jobs)
    print(f"{len(jobs)} jobs, {est_chars/4/1e6:.2f}M input tokens (rough)")
    before = Caller(str(AUDIT)).spent()
    df = run(jobs, threads=a.threads, dry=a.dry)
    after = Caller(str(AUDIT)).spent()
    keep = [c for c in df.columns if c not in ("prompt", "roles")]
    df["roles"] = df["roles"].map(json.dumps)
    out = Path(a.out)
    out.parent.mkdir(exist_ok=True, parents=True)
    df[keep + ["roles"]].to_csv(out, index=False)
    print(f"spent this run {after-before:.4f} USD; total {after:.4f}")
    print(df.groupby(["cond", "subset"]).bucket.value_counts().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    main()
