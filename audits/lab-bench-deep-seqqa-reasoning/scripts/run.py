"""Sonnet K/D pairs under a step-by-step reasoning prompt (prereg.md).

Items and arms come from ../lab-bench-deep-seqqa by path: data/arms.json (K and D option lists,
key at index 0, D_centre) and plans/b1_sonnet_pilot.json + plans/b2_sonnet_main.json (the 48
Sonnet pairs). The prompt is the parent audit's rendering (audits/lab-bench/scripts/haiku.py
TEMPLATE: "Think step by step.", no letter-only line), forced choice (no refusal option), with the
same hashed option order as every earlier arm, so the key has the same letter in K and D. This is
exactly the rendering of ../lab-bench-deep-seqqa/validation/v6_prompt.py.

Usage:
  python -I scripts/run.py pilot      # 4 calls on 2 Gibson pairs that are NOT in the sample
  python -I scripts/run.py main       # the sample, in the pre-registered order, until N_TARGET
  python -I scripts/run.py score      # no calls: re-score everything from the cache
Outputs: results/runs_<mode>.csv; raw text stays in inference/cache (git-ignored).
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
AUD = HERE.parent
SRC = AUD.parent / "lab-bench-deep-seqqa"
REPO = AUD.parent.parent
sys.path.insert(0, str(AUD.parent / "tools"))
from claude_call import BudgetExceeded, Caller  # noqa: E402

PQ = AUD.parent / "lab-bench" / "data" / "hf" / "SeqQA" / "train-00000-of-00001.parquet"
PQ_SHA = "5864776d3d85774f91d82432e30ac31e9222f1670621e8ea141414173c5e9b46"
ALPHA = "ABCDEFGH"
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
GIBSON = ["PCR-gene-gibshindprimers-v1", "PCR-gene-gibssmaprimers-v1"]
OTHER = ["Prop-seq-gcpercent-v1", "ORF-seq-AAseq-v1", "PCR-seq-enzprimers-v1", "PCR-gene-enzprimers-v1"]
N_TARGET = int((AUD / "N_TARGET").read_text().strip()) if (AUD / "N_TARGET").exists() else 0


def perm(item_id: str, n: int, salt: str = "order"):
    seed = int(hashlib.sha256(f"{salt}:{item_id}".encode()).hexdigest()[:8], 16)
    return list(np.random.default_rng(seed).permutation(n))


def load():
    assert hashlib.sha256(PQ.read_bytes()).hexdigest() == PQ_SHA
    items = {r["id"]: r for r in pq.read_table(PQ).to_pylist()}
    arms = json.loads((SRC / "data" / "arms.json").read_text())
    return items, arms


def sample_order(arms):
    """The pre-registered order: Gibson pairs first (in the earlier plan's order), then the other
    four subtasks round-robin in the earlier plan's order within each subtask."""
    plan = (json.loads((SRC / "plans" / "b1_sonnet_pilot.json").read_text())
            + json.loads((SRC / "plans" / "b2_sonnet_main.json").read_text()))
    orders = json.loads((SRC / "plans" / "orders.json").read_text())
    ids = {j["id"] for j in plan if j["arm"] == "K"}
    by = {f: [i for i in orders[f] if i in ids] for f in GIBSON + OTHER}
    out = []
    for k in range(max(len(by[f]) for f in GIBSON)):
        for f in GIBSON:
            if k < len(by[f]):
                out.append(by[f][k])
    for k in range(max(len(by[f]) for f in OTHER)):
        for f in OTHER:
            if k < len(by[f]):
                out.append(by[f][k])
    assert len(out) == 48 and len(set(out)) == 48
    return out


def pilot_ids(arms):
    """Two Gibson pairs outside the Sonnet sample (positions 10 of each subtask's order)."""
    orders = json.loads((SRC / "plans" / "orders.json").read_text())
    return [orders[f][10] for f in GIBSON]


def render(item, opts, iid):
    p = perm(iid, len(opts))
    shown = [opts[j] for j in p]
    answers = "\n".join(f"({ALPHA[k]}) {o}" for k, o in enumerate(shown))
    return TEMPLATE.format(question=item["question"], answers=answers), p


def parse(out: str):
    m = re.findall(r"\[ANSWER\]\s*\(?([A-Z])\)?\s*\[/ANSWER\]", out or "")
    return m[-1] if m else None


def jobs_for(ids, items, arms):
    jobs = []
    for iid in ids:
        for arm in ("K", "D"):
            opts = arms[iid][arm]
            prompt, p = render(items[iid], opts, iid)
            jobs.append({"id": iid, "arm": arm, "subtask": arms[iid]["family"], "prompt": prompt,
                         "role_of_letter": {ALPHA[k]: int(j) for k, j in enumerate(p)},
                         "centre": arms[iid].get("D_centre") if arm == "D" else None})
    return jobs


def run(jobs, llm, call: bool):
    def one(j):
        if not call:
            key = hashlib.sha256(json.dumps(["claude-sonnet-5-5", SYSTEM, j["prompt"]]).encode()).hexdigest()
            f = llm.cache / f"{key}.json"
            return {**j, "out": json.loads(f.read_text())["result"] if f.exists() else None,
                    "err": "" if f.exists() else "not run"}
        try:
            return {**j, "out": llm.ask(j["prompt"], system=SYSTEM, model="sonnet", timeout=400), "err": ""}
        except BudgetExceeded as e:
            return {**j, "out": None, "err": f"budget: {e}"}
        except Exception as e:  # noqa: BLE001
            return {**j, "out": None, "err": repr(e)[:150]}

    with ThreadPoolExecutor(3) as ex:
        res = list(ex.map(one, jobs))
    rows = []
    for j in res:
        letter = parse(j["out"]) if j["out"] is not None else None
        role = j["role_of_letter"].get(letter) if letter else None
        bucket = ("error" if j["out"] is None else "unparsed" if role is None else
                  "correct" if role == 0 else "wrong")
        rows.append({"id": j["id"], "subtask": j["subtask"], "arm": j["arm"], "letter": letter,
                     "role": "" if role is None else role, "bucket": bucket,
                     "centre": json.dumps(j["centre"]) if j["centre"] is not None else "",
                     "key_letter": [L for L, r in j["role_of_letter"].items() if r == 0][0],
                     "out_len": len(j["out"] or ""), "err": j["err"]})
    return rows


def write(rows, name):
    out = AUD / "results" / f"runs_{name}.csv"
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return out


def main():
    mode = sys.argv[1]
    items, arms = load()
    llm = Caller(str(AUD), cap_usd=2.50, neutral_cwd=True)
    before = llm.spent()
    if mode == "pilot":
        rows = run(jobs_for(pilot_ids(arms), items, arms), llm, call=True)
        write(rows, "pilot")
    elif mode in ("main", "score"):
        ids = sample_order(arms)[:N_TARGET]
        rows = run(jobs_for(ids, items, arms), llm, call=(mode == "main"))
        write(rows, "main")
    else:
        raise SystemExit("mode: pilot | main | score")
    print(f"spent this run {llm.spent() - before:.4f}; total {llm.spent():.4f} USD")
    from collections import Counter
    print(Counter((r["arm"], r["bucket"]) for r in rows))


if __name__ == "__main__":
    main()
