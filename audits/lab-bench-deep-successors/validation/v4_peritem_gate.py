"""Validator, claim 5: re-count DeepSeek-R1 chains whose chosen option is recoverable.

Own implementation of the pre-registered rule (prereg Analysis 5), written without reading
scripts/peritem.py. doc_id -> row of the HF release; tried on every release. The chain text is the
user message embedded in `data`. Recovered: the last 'ANSWER: X' letter is bound to exactly one
option by `X)`, `(X)`, `X.`, `X:` or `Option X` followed within 8 characters by the first 25
characters of that option. Counts only. Run with ../lab-bench/data/.venv/bin/python -I.
"""
import collections
import json
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
S6 = {"ORF-seq-AAseq", "PCR-gene-enzprimers", "PCR-seq-enzprimers", "PCR-gene-gibshindprimers",
      "PCR-gene-gibssmaprimers", "Prop-seq-gcpercent"}
REVS = {"7268767a": DATA / "hfrev_7268767a", "4709d14f": DATA / "hfrev_4709d14f",
        "5c77cec6": HERE.parent.parent / "lab-bench" / "data" / "hf"}


def main():
    ch = pd.read_parquet(DATA / "hf_lihaoxin_dsr1" / "SeqQA" / "train-00000-of-00001.parquet")
    out = {}
    for rev, p in REVS.items():
        items = pd.read_parquet(p / "SeqQA" / "train-00000-of-00001.parquet").reset_index(drop=True)
        rec = collections.Counter()
        content_hit = 0
        rec_correct = collections.Counter()
        for r in ch.itertuples():
            it = items.iloc[int(r.doc_id)]
            text = str(r.data)
            opts = [str(it.ideal)] + [str(x) for x in it.distractors]
            if any(len(o) >= 14 and o[:14] in text for o in opts) or it.question[-60:-46] in text:
                content_hit += 1
            m = re.findall(r"ANSWER:\s*\(?([A-H])\b", text)
            if not m:
                continue
            L = m[-1]
            bound = []
            for i, o in enumerate(opts):
                pre = re.escape(o[:25])
                pat = rf"(?:\({L}\)|\b{L}\)|\b{L}\.|\b{L}:|Option {L})[\s\S]{{0,8}}?{pre}"
                if re.search(pat, text):
                    bound.append(i)
            if len(bound) == 1:
                st = it.subtask.replace("-v1-public", "")
                grp = "S" if st in S6 else "F"
                rec[(grp, st)] += 1
                rec_correct[grp] += int(bound[0] == 0)
        S = {k[1]: v for k, v in rec.items() if k[0] == "S"}
        F = {k[1]: v for k, v in rec.items() if k[0] == "F"}
        out[rev] = {"content_match_share": round(content_hit / len(ch), 4),
                    "recovered_S": sum(S.values()), "recovered_S_subtasks": S,
                    "recovered_F": sum(F.values()), "n_F_subtasks": len(F),
                    "gate_met": sum(S.values()) >= 20 and len(S) >= 3 and sum(F.values()) >= 20 and len(F) >= 3}
        print(rev, out[rev])
    (HERE / "v4_peritem_gate.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
