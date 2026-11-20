"""Validator run (prereg: validation/v6_prereg_prompt.md): the parent's prompt on this folder's
K and D Gibson pairs.

Arms Kp / Dp: same option lists and the same hashed option order as the auditor's K and D, but the
parent audit's rendering (audits/lab-bench/scripts/haiku.py TEMPLATE: "Think step by step.", no
letter-only line) and forced choice (no refusal option). Haiku only, 60 calls.

Writes validation/v6_prompt_runs.csv and validation/v6_prompt.json.
Run: ../lab-bench/data/.venv/bin/python -I validation/v6_prompt.py
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

AUD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AUD.parent / "tools"))
from claude_call import BudgetExceeded, Caller  # noqa: E402

PQ = AUD.parent / "lab-bench" / "data" / "hf" / "SeqQA" / "train-00000-of-00001.parquet"
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
GIBSON = ("PCR-gene-gibshindprimers-v1", "PCR-gene-gibssmaprimers-v1")


def perm(item_id: str, n: int, salt: str = "order"):
    seed = int(hashlib.sha256(f"{salt}:{item_id}".encode()).hexdigest()[:8], 16)
    return list(np.random.default_rng(seed).permutation(n))


def main():
    items = {r["id"]: r for r in pq.read_table(PQ).to_pylist()}
    arms = json.loads((AUD / "data" / "arms.json").read_text())
    rows = list(csv.DictReader(open(AUD / "validation" / "v1_rows.csv")))
    have = {}
    for r in rows:
        if r["model"] == "haiku" and r["subtask"] in GIBSON and r["arm"] in ("K", "D"):
            have.setdefault(r["id"], {})[r["arm"]] = r["bucket"]
    ids = sorted(i for i, v in have.items() if len(v) == 2)
    assert len(ids) == 30, len(ids)
    jobs = []
    for iid in ids:
        for arm in ("K", "D"):
            opts = arms[iid][arm]
            p = perm(iid, len(opts))
            shown = [opts[j] for j in p]
            answers = "\n".join(f"({ALPHA[k]}) {o}" for k, o in enumerate(shown))
            prompt = TEMPLATE.format(question=items[iid]["question"], answers=answers)
            jobs.append({"id": iid, "arm": arm + "p", "key_letter": ALPHA[shown.index(opts[0])],
                         "subtask": items[iid]["subtask"].replace("-public", ""), "prompt": prompt})
    llm = Caller(str(AUD))
    before = llm.spent()
    print(f"{len(jobs)} calls; spent so far {before:.4f}")

    def one(j):
        try:
            return {**j, "out": llm.ask(j["prompt"], system=SYSTEM, model="haiku"), "err": ""}
        except BudgetExceeded as e:
            return {**j, "out": None, "err": f"budget: {e}"}
        except Exception as e:  # noqa: BLE001
            return {**j, "out": None, "err": repr(e)[:150]}

    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(one, jobs))
    out_rows = []
    for j in res:
        m = re.findall(r"\[ANSWER\]\s*\(?([A-Z])\)?\s*\[/ANSWER\]", j["out"] or "")
        letter = m[-1] if m else None
        bucket = ("error" if j["out"] is None else
                  "unparsed" if letter is None else
                  "correct" if letter == j["key_letter"] else "wrong")
        out_rows.append({"id": j["id"], "subtask": j["subtask"], "arm": j["arm"],
                         "letter": letter, "bucket": bucket, "out_len": len(j["out"] or ""),
                         "err": j["err"]})
    with open(AUD / "validation" / "v6_prompt_runs.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0]))
        w.writeheader()
        w.writerows(out_rows)
    spent = llm.spent() - before
    by = {}
    for r in out_rows:
        by.setdefault(r["id"], {})[r["arm"]] = r["bucket"] == "correct"
    pairs = [(v["Kp"], v["Dp"]) for v in by.values() if len(v) == 2]
    d = np.array([a - b for a, b in pairs], float)
    rng = np.random.default_rng(0)
    s = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)]
    from math import comb
    b = sum(1 for a, c in pairs if a and not c)
    c = sum(1 for a, cc in pairs if cc and not a)
    n = b + c
    p = min(1.0, 2 * sum(comb(n, i) for i in range(0, min(b, c) + 1)) / 2 ** n) if n else 1.0
    res_j = {"n_pairs": len(pairs), "Kp": round(float(np.mean([x[0] for x in pairs])), 4),
             "Dp": round(float(np.mean([x[1] for x in pairs])), 4), "diff": round(float(d.mean()), 4),
             "ci_items": [round(float(np.percentile(s, 2.5)), 4), round(float(np.percentile(s, 97.5)), 4)],
             "Kp_only": b, "Dp_only": c, "mcnemar_exact_p": round(p, 5),
             "unparsed": sum(r["bucket"] == "unparsed" for r in out_rows),
             "errors": sum(r["bucket"] == "error" for r in out_rows),
             "mean_out_len": round(float(np.mean([r["out_len"] for r in out_rows])), 1),
             "spend_usd": round(spent, 4), "total_spend_usd": round(llm.spent(), 4),
             "prior_same_items": {"K": 0.7667, "D": 0.7, "diff": 0.0667}}
    per = {}
    for st in GIBSON:
        sub = [(by[i]["Kp"], by[i]["Dp"]) for i in by if items[i]["subtask"].startswith(st[:-3])]
        if sub:
            per[st] = {"n": len(sub), "Kp": round(float(np.mean([x[0] for x in sub])), 4),
                       "Dp": round(float(np.mean([x[1] for x in sub])), 4)}
    res_j["per_subtask"] = per
    print(json.dumps(res_j, indent=1))
    (AUD / "validation" / "v6_prompt.json").write_text(json.dumps(res_j, indent=1) + "\n")


if __name__ == "__main__":
    main()
