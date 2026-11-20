"""Render and run arms through audits/tools/claude_call.py (Sonnet or Haiku; cached; 3 USD cap).

Prompt (all arms except N): the FutureHouse zero-shot template as the parent used it, with the
"Think step by step" line removed and a letter-only instruction added; the benchmark's
"Insufficient information to answer the question." option is inserted at a hashed position
(as both harnesses do). The model is given no tools. The CLI runs the model with its default
extended thinking; the thinking text is not returned, so only the final answer is read.
N (options only): the question is withheld; forced choice, no refusal option.

Option order: one permutation per item from a hash of the item id (parent's perm_for), applied to
the arm's option list in which a replaced option keeps its slot, so the key has the same letter
in O, D, K and I, and in N.

Usage: python -I scripts/run.py --plan plans/<name>.json --out results/runs_<name>.csv
A plan is a list of {"id", "arm", "model"}. Raw outputs go to data/raw_<name>.jsonl (ignored).
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
AUD = HERE.parent
sys.path.insert(0, str(AUD.parent / "tools"))
sys.path.insert(0, str(AUD.parent / "lab-bench" / "scripts"))
from claude_call import MODELS, BudgetExceeded, Caller  # noqa: E402
from common import load_items  # noqa: E402

ALPHA = string.ascii_uppercase
REFUSE = "Insufficient information to answer the question."
SYSTEM = "You are a helpful assistant."

TEMPLATE = """The following is a multiple choice question about biology.
Please answer by responding with the letter of the correct answer.

Question: {question}

Options:
{answers}

You MUST include the letter of the correct answer within the following tags: [ANSWER] and [/ANSWER].
For example, '[ANSWER]<answer>[/ANSWER]', where <answer> is the correct letter.
Always answer in exactly this format of a single letter between the two tags, even if you are unsure.
Respond with only the tagged letter and nothing else."""

N_TEMPLATE = """Below are the answer options of a multiple choice question about biology. One of them is the correct answer to a question that is hidden from you.
Choose the option that is most likely to be the correct answer.

Options:
{answers}

You MUST include the letter of your choice within the following tags: [ANSWER] and [/ANSWER].
For example, '[ANSWER]<answer>[/ANSWER]', where <answer> is the letter.
Always answer in exactly this format of a single letter between the two tags, even if you are unsure.
Respond with only the tagged letter and nothing else."""


def perm_for(item_id: str, n: int, salt: str = "order") -> list[int]:
    seed = int(hashlib.sha256(f"{salt}:{item_id}".encode()).hexdigest()[:8], 16)
    return list(np.random.default_rng(seed).permutation(n))


def render(item_id: str, question: str, opts: list[str], arm: str) -> tuple[str, dict]:
    """Return prompt and letter -> option index in the arm's list (0 = key) or 'refuse'."""
    p = perm_for(item_id, len(opts))
    subs = [opts[i] for i in p]
    roles: list = list(p)
    if arm != "N":
        pos = perm_for(item_id, len(subs) + 1, salt="refuse")[0]
        subs = subs[:pos] + [REFUSE] + subs[pos:]
        roles = roles[:pos] + ["refuse"] + roles[pos:]
    answers = "\n".join(f"({ALPHA[i]}) {o}" for i, o in enumerate(subs))
    if arm == "N":
        prompt = N_TEMPLATE.format(answers=answers)
    else:
        prompt = TEMPLATE.format(question=question, answers=answers)
    return prompt, {ALPHA[i]: (int(r) if r != "refuse" else r) for i, r in enumerate(roles)}


TAG = re.compile(r"\[ANSWER\]\s*\(?([A-Z])\)?\s*\[/ANSWER\]")
ALT = re.compile(r"ANSWER\s*[:\]]\s*\(?([A-Z])\)?\b")
BARE = re.compile(r"^\s*\(?([A-F])\)?\.?\s*$")


def parse(out: str) -> tuple[str | None, str]:
    m = TAG.findall(out)
    if m:
        return m[-1], "tag"
    m = ALT.findall(out)
    if m:
        return m[-1], "alt"
    m = BARE.match(out)
    if m:
        return m.group(1), "bare"
    return None, "none"


def options_for(arms: dict, item_id: str, arm: str) -> list[str]:
    a = arms[item_id]
    return a["O"] if arm == "N" else a[arm]


def cost_of(prompt: str, model: str) -> tuple[float, dict]:
    key = hashlib.sha256(json.dumps([MODELS[model], SYSTEM, prompt]).encode()).hexdigest()
    f = AUD / "inference" / "cache" / f"{key}.json"
    if not f.exists():
        return float("nan"), {}
    d = json.loads(f.read_text())
    return d.get("cost_usd", float("nan")), d.get("usage") or {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    assert a.threads <= 4
    items = load_items().set_index("id", drop=False)
    arms = json.loads((AUD / "data" / "arms.json").read_text())
    plan = json.loads(Path(a.plan).read_text())
    jobs = []
    for j in plan:
        r = items.loc[j["id"]]
        opts = options_for(arms, j["id"], j["arm"])
        prompt, roles = render(j["id"], r.question, opts, j["arm"])
        jobs.append({**j, "family": arms[j["id"]]["family"], "prompt": prompt, "roles": roles,
                     "n_sub": len(opts), "centre": arms[j["id"]].get("D_centre") if j["arm"] == "D" else None})
    print(f"{len(jobs)} jobs, ~{sum(len(x['prompt']) for x in jobs) / 4 / 1e3:.0f}k input tokens")
    if a.dry:
        return
    llm = Caller(str(AUD))
    before = llm.spent()

    def one(j):
        try:
            out = llm.ask(j["prompt"], system=SYSTEM, model=j["model"])
        except BudgetExceeded as e:
            return {**j, "out": None, "err": f"budget: {e}"}
        except Exception as e:  # noqa: BLE001
            return {**j, "out": None, "err": repr(e)[:200]}
        return {**j, "out": out, "err": None}

    with ThreadPoolExecutor(a.threads) as ex:
        res = list(ex.map(one, jobs))
    rows, raw = [], []
    for j in res:
        letter, how = parse(j["out"]) if j["out"] is not None else (None, "error")
        role = j["roles"].get(letter) if letter else None
        if j["out"] is None:
            bucket = "error"
        elif letter is None or letter not in j["roles"]:
            bucket = "unparsed"
        elif role == "refuse":
            bucket = "refuse"
        else:
            bucket = "correct" if role == 0 else "wrong"
        c, u = cost_of(j["prompt"], j["model"])
        rows.append({"id": j["id"], "family": j["family"], "arm": j["arm"], "model": j["model"],
                     "letter": letter, "parse": how, "bucket": bucket,
                     "picked": role if role is not None else "", "n_sub": j["n_sub"],
                     "d_centre": json.dumps(j["centre"]) if j["centre"] is not None else "",
                     "cost_usd": c, "out_tokens": u.get("output_tokens"),
                     "thinking_tokens": (u.get("output_tokens_details") or {}).get("thinking_tokens"),
                     "out_len": len(j["out"] or ""), "err": j["err"] or ""})
        raw.append({"id": j["id"], "arm": j["arm"], "model": j["model"], "out": j["out"]})
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    with open(AUD / "data" / f"raw_{out.stem}.jsonl", "w") as fh:
        for x in raw:
            fh.write(json.dumps(x) + "\n")
    df = pd.DataFrame(rows)
    print(f"spent this run {llm.spent() - before:.4f} USD; total {llm.spent():.4f}")
    print(df.groupby(["model", "arm"]).bucket.value_counts().unstack(fill_value=0).to_string())
    print(df.groupby(["model"]).cost_usd.describe().to_string())


if __name__ == "__main__":
    main()
