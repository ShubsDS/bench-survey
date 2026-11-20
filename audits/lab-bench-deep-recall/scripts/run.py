"""Run one arm on one subset with one model through audits/tools/claude_call.py.

  python -I scripts/run.py --arm qo --model sonnet --subset ProtocolQA [--ids a,b] [--limit N] [--out name]

Writes results/runs/<out>.csv: id, cluster (hashed), arm, model, letter, bucket, picked_role,
refusal flag, output length. No item text. For `qgen` the free-text reply is graded later by
grade_qgen.py from the cache; here only its length is recorded.
At most 4 concurrent calls.
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_r import (AUDIT, DATA, REFUSAL_RE, RESULTS, SYSTEM, bucket, key_hash, load, parse,
                      render)
from claude_call import BudgetExceeded, Caller


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--model", required=True, choices=["haiku", "sonnet"])
    ap.add_argument("--subset", required=True, choices=["ProtocolQA", "CloningScenarios"])
    ap.add_argument("--ids", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--style", default="cot", choices=["cot", "direct"])
    ap.add_argument("--quiet", action="store_true", help="do not print outcome counts (pilot)")
    a = ap.parse_args()
    assert a.threads <= 4
    items = load()
    items = items[items.subset == a.subset]
    if a.ids:
        items = items.loc[[i for i in a.ids.split(",")]]
    if a.limit:
        items = items.head(a.limit)
    para = {}
    if a.arm.endswith("_pa"):
        para = json.loads((DATA / "paraphrases.json").read_text())
        items = items[items.id.isin(para)]
    llm = Caller(str(AUDIT))
    before = llm.spent()

    def one(r):
        prompt, roles = render(r, a.arm, para.get(r.id), style=a.style)
        rec = {"id": r.id, "cluster": key_hash(r.cluster), "arm": a.arm, "model": a.model, "style": a.style,
               "n_sub": len(roles)}
        try:
            out = llm.ask(prompt, system=SYSTEM, model=a.model)
        except BudgetExceeded as e:
            return {**rec, "bucket": "budget", "err": str(e)}
        except Exception as e:  # noqa: BLE001
            return {**rec, "bucket": "error", "err": repr(e)[:200]}
        rec["out_len"] = len(out)
        rec["refusal_text"] = bool(REFUSAL_RE.search(out))
        if a.arm == "qgen":
            rec["bucket"] = "free"
            return rec
        letter = parse(out)
        rec.update({"letter": letter, "bucket": bucket(letter, roles),
                    "picked_role": roles.get(letter) if letter else None, "roles": json.dumps(roles)})
        return rec

    with ThreadPoolExecutor(a.threads) as ex:
        rows = list(ex.map(one, [r for _, r in items.iterrows()]))
    df = pd.DataFrame(rows)
    out = RESULTS / "runs" / f"{a.out or (a.arm + '_' + a.model + '_' + a.subset)}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    after = llm.spent()
    print(f"{len(df)} rows -> {out.name}; spent {after - before:.4f} USD this run, total {after:.4f}")
    if not a.quiet:
        print(df.bucket.value_counts().to_dict())


if __name__ == "__main__":
    main()
