"""Analysis 5 (prereg.md): per-item outputs of DeepSeek-R1 ("deepseek-reasoner") on LAB-Bench SeqQA,
HF lihaoxin2020/deepseek-reasoner-full-lab_bench-r1 @ 43fa27ef. Each row holds a knowledge-extraction
prompt that embeds the model's reasoning chain ending in "ANSWER: X"; the option order shown to the
model is not stored.

Steps (all fixed in prereg.md):
1. Item mapping: doc_id -> row of a HF revision of futurehouse/lab-bench SeqQA. For each revision, the
   share of rows whose chain contains a >= 14-character substring of that item's options or question.
2. Recovery: the final ANSWER letter is explicitly bound in the chain to exactly one option
   ("X)", "(X)", "X.", "X:", "**X**" or "Option X" followed within 8 characters by its first 25 characters).
3. Gate: >= 20 recovered items in S across >= 3 S subtasks and >= 20 in F across >= 3 F subtasks.
Writes counts only (no text).
"""
from __future__ import annotations

import collections
import hashlib
import json
import re
from pathlib import Path

import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent.parent
D = HERE / "data"
OUT = D / "hf_lihaoxin_dsr1" / "SeqQA" / "train-00000-of-00001.parquet"
REVS = {"hf@7268767a": D / "hfrev_7268767a", "hf@8e6bb002": D / "hfrev_8e6bb002", "hf@4709d14f": D / "hfrev_4709d14f",
        "hf@8137378e": D / "hfrev_8137378e", "hf@5c77cec6": HERE.parent / "lab-bench" / "data" / "hf"}
S6 = {"ORF-seq-AAseq", "PCR-gene-enzprimers", "PCR-seq-enzprimers", "PCR-gene-gibshindprimers",
      "PCR-gene-gibssmaprimers", "Prop-seq-gcpercent"}
K = 14


def chain(row):
    c = row["data"][0]["content"]
    i, j = c.find("## Reasoning Chain:"), c.rfind("## Now perform")
    return c[i + 19:j]


def items(path):
    t = pq.read_table(path / "SeqQA" / "train-00000-of-00001.parquet").to_pandas()
    t["subtask"] = t["subtask"].str.replace("-public", "").str.replace("-v1", "")
    return t


def contains_piece(text, strings):
    for s in strings:
        s = s.strip()
        for p in range(0, max(1, len(s) - K + 1), 7):
            if s[p:p + K] in text and len(s[p:p + K]) == K:
                return True
    return False


def main():
    out = pq.read_table(OUT).to_pandas()
    res = {"source": "lihaoxin2020/deepseek-reasoner-full-lab_bench-r1@43fa27efe117cff2f6f47dd30e647ecac3d75c2d",
           "parquet_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(), "n_rows": len(out),
           "doc_id_range": [int(out.doc_id.min()), int(out.doc_id.max())], "mapping": {}}
    chains = {int(r.doc_id): chain(r) for _, r in out.iterrows()}
    best, best_share = None, -1
    for lab, p in REVS.items():
        it = items(p)
        hit = collections.Counter()
        tot = collections.Counter()
        for d, ch in chains.items():
            r = it.iloc[d]
            tot[r.subtask] += 1
            hit[r.subtask] += contains_piece(ch, [r.ideal, *r.distractors, r.question])
        share = sum(hit.values()) / len(chains)
        res["mapping"][lab] = {"share_with_substring": round(share, 4),
                               "by_subtask": {s: f"{hit[s]}/{tot[s]}" for s in sorted(tot)}}
        if share > best_share:
            best, best_share = lab, share
    res["revision_used"] = best
    it = items(REVS[best])
    letters = collections.Counter()
    rec = collections.defaultdict(collections.Counter)
    for d, ch in chains.items():
        r = it.iloc[d]
        m = re.findall(r"ANSWER:\s*\**\(?([A-J])\)?", ch)
        if not m:
            rec[r.subtask]["no_letter"] += 1
            continue
        L = m[-1]
        letters[L] += 1
        opts = [o.strip() for o in [r.ideal, *r.distractors]]
        bound = set()
        for k, o in enumerate(opts):
            pre = re.escape(o[:25])
            if re.search(r"(?:\(|\b|\*\*)" + L + r"(?:\)|\.|:|\*\*)[\s\*:`\-]{0,8}" + pre, ch) or \
               re.search(r"[Oo]ption\s*\(?" + L + r"\)?[\s\*:`\-]{0,8}" + pre, ch):
                bound.add(k)
        rec[r.subtask]["recovered" if len(bound) == 1 else ("ambiguous" if bound else "not_bound")] += 1
    res["final_letter_counts"] = dict(sorted(letters.items()))
    res["recovery_by_subtask"] = {s: dict(c) for s, c in sorted(rec.items())}
    nS = sum(c["recovered"] for s, c in rec.items() if s in S6)
    nF = sum(c["recovered"] for s, c in rec.items() if s not in S6)
    kS = sum(1 for s, c in rec.items() if s in S6 and c["recovered"])
    kF = sum(1 for s, c in rec.items() if s not in S6 and c["recovered"])
    res["recovered_S"], res["recovered_F"], res["S_subtasks_with_recovery"], res["F_subtasks_with_recovery"] = nS, nF, kS, kF
    res["gate_met"] = bool(nS >= 20 and kS >= 3 and nF >= 20 and kF >= 3)
    (HERE / "results" / "peritem.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
