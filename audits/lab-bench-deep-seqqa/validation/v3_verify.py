"""Validator: independent verification of keys and of the K/D rebuilds.

Written from the pinned parquet and data/arms.json only (the auditor's build.py was not used).
Checks, per cue subtask:

GC-percent      key == round(GC%); every other option in O/D/K/I != that value; the paper's
                distractor pattern {x-1, x+1, x/2}.
ORF-seq-AAseq   key == translation of the longest forward-strand ORF (own translator); the
                longest reverse-strand ORF is computed too (claim 6b); every non-key option in
                K and D is not a correct translation under either strand.
PCR (4)         every option is parsed as "F, R"; the enzyme sites / Gibson overlaps the option
                carries are identified from a hardcoded site table; an option is "site-correct"
                only if F starts with the named site (or forward overlap) and R starts with the
                named site (or reverse overlap). For PCR-seq-enzprimers the gene sequence is in
                the question, so the body is checked against the gene's 5' prefix and the 3'
                suffix in sense orientation and against its reverse complement (claim 6a).
                Then: is the key the only site-correct and body-correct option in K and D?

Also compares K and D arms on everything except centrality: option lengths, duplicate bodies,
obviously broken options, which option is the parquet key.

Run: ../lab-bench/data/.venv/bin/python -I validation/v3_verify.py
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

AUD = Path(__file__).resolve().parent.parent
PQ = AUD.parent / "lab-bench" / "data" / "hf" / "SeqQA" / "train-00000-of-00001.parquet"
SHA = "5864776d3d85774f91d82432e30ac31e9222f1670621e8ea141414173c5e9b46"

SITES = {  # the paper's eligible enzyme list (App. C.7.1) plus the aliases used in the items
    "BfuAI": "ACCTGC", "SalI": "GTCGAC", "XbaI": "TCTAGA", "EcoRI": "GAATTC", "SphI": "GCATGC",
    "BamHI": "GGATCC", "Acc65I": "GGTACC", "TspMI": "CCCGGG", "SbfI": "CCTGCAGG", "SmaI": "CCCGGG",
    "KpnI": "GGTACC", "HindIII": "AAGCTT", "BspMI": "ACCTGC", "Eco53kI": "GAGCTC",
    "SacI": "GAGCTC", "PstI": "CTGCAG", "XmaI": "CCCGGG", "SstI": "GAGCTC", "HincII": "GTYRAC",
}
# pUC19 Gibson overlaps as the paper states them (App. C.7.4 / C.7.5)
GIBSON = {
    "hind": ("GATTACGCCAAGCTTGCATGCCTGCAGGTC", "GAGCTCGGTACCCGGGGATCCTCTAGAGTC"),
    "sma": ("ATGCCTGCAGGTCGACTCTAGAGGATCCCC", "CGACGGCCAGTGAATTCGAGCTCGGTACCC"),
}
CODON = {}
_B = "TCAG"
_AA = "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG"
for i, b1 in enumerate(_B):
    for j, b2 in enumerate(_B):
        for k, b3 in enumerate(_B):
            CODON[b1 + b2 + b3] = _AA[i * 16 + j * 4 + k]


def rc(s: str) -> str:
    return s.translate(str.maketrans("ACGT", "TGCA"))[::-1]


def translate(dna: str) -> str:
    return "".join(CODON.get(dna[i:i + 3], "X") for i in range(0, len(dna) - len(dna) % 3, 3))


def orfs(seq: str):
    """All ATG..stop ORFs (stop included) on the given strand, as translated strings."""
    out = []
    for f in range(3):
        i = f
        while i + 3 <= len(seq):
            if seq[i:i + 3] == "ATG":
                j = i
                while j + 3 <= len(seq):
                    c = seq[j:j + 3]
                    if c in ("TAA", "TAG", "TGA"):
                        out.append(translate(seq[i:j + 3]))
                        break
                    j += 3
            i += 3
    return out


def longest(seq: str):
    o = orfs(seq)
    if not o:
        return None, 0, False
    m = max(len(x) for x in o)
    top = [x for x in o if len(x) == m]
    return top[0], m, len(set(top)) > 1


def main():
    assert hashlib.sha256(PQ.read_bytes()).hexdigest() == SHA
    items = {r["id"]: r for r in pq.read_table(PQ).to_pylist()}
    for r in items.values():
        r["subtask"] = r["subtask"].replace("-public", "")
    arms = json.loads((AUD / "data" / "arms.json").read_text())
    rep = defaultdict(lambda: Counter())
    notes = []

    # ---------------- GC
    for iid, a in arms.items():
        if a["family"] != "Prop-seq-gcpercent-v1":
            continue
        it = items[iid]
        seq = re.search(r"sequence ([ACGT]+)\?", it["question"]).group(1)
        gc = round(100 * sum(c in "GC" for c in seq) / len(seq))
        r = rep["GC"]
        r["n"] += 1
        r["key_is_round_gc"] += int(str(gc) == it["ideal"])
        x = int(it["ideal"])
        r["paper_pattern"] += int(sorted(int(d) for d in it["distractors"]) == sorted([x - 1, x + 1, round(x / 2)]))
        for arm in ("O", "D", "K", "I"):
            if arm not in a:
                continue
            vals = [int(v) for v in a[arm]]
            r[f"{arm}_key_unique_correct"] += int(sum(v == gc for v in vals) == 1 and vals[0] == gc)
            r[f"{arm}_dup_options"] += int(len(set(vals)) != len(vals))

    # ---------------- AAseq
    for iid, a in arms.items():
        if a["family"] != "ORF-seq-AAseq-v1":
            continue
        it = items[iid]
        seq = re.search(r"sequence '([ACGT]+)", it["question"]).group(1)
        f_top, f_len, f_tie = longest(seq)
        r_top, r_len, _ = longest(rc(seq))
        r = rep["AAseq"]
        r["n"] += 1
        r["key_eq_longest_fwd"] += int(f_top == it["ideal"])
        r["fwd_tie"] += int(f_tie)
        r["rev_strictly_longer"] += int(r_len > f_len)
        r["key_eq_longest_either"] += int(it["ideal"] in (f_top, r_top))
        allowed = {f_top, r_top}
        r["has_pair"] += int("D" in a and "K" in a)
        for arm in ("D", "K"):
            if arm not in a:
                continue
            opts = a[arm]
            r[f"{arm}_key_first"] += int(opts[0] == it["ideal"])
            r[f"{arm}_other_option_also_valid"] += int(any(o in allowed for o in opts[1:]))

    # ---------------- PCR
    def sites_named(q: str, fam: str):
        if "enzprimers" in fam:
            m = re.search(r"enzymes (\w+) and (\w+)", q)
            return SITES[m.group(1)], SITES[m.group(2)]
        key = "hind" if "gibshind" in fam else "sma"
        return GIBSON[key]

    for iid, a in arms.items():
        fam = a["family"]
        if fam not in ("PCR-gene-enzprimers-v1", "PCR-seq-enzprimers-v1",
                       "PCR-gene-gibshindprimers-v1", "PCR-gene-gibssmaprimers-v1"):
            continue
        it = items[iid]
        s1, s2 = sites_named(it["question"], fam)
        gene = None
        if fam == "PCR-seq-enzprimers-v1":
            gene = re.search(r"sequence ([ACGT]+) into", it["question"]).group(1)
        r = rep[fam]
        r["n"] += 1
        key_f, key_r = [x.strip() for x in it["ideal"].split(",")]
        r["key_F_has_site"] += int(key_f.startswith(s1))
        r["key_R_has_site"] += int(key_r.startswith(s2))
        if gene:
            body_f, body_r = key_f[len(s1):], key_r[len(s2):]
            r["key_F_body_is_gene_prefix"] += int(gene.startswith(body_f))
            r["key_R_body_is_gene_suffix_sense"] += int(gene.endswith(body_r))
            r["key_R_body_is_rc_of_gene_end"] += int(rc(gene).startswith(body_r))
            r["key_R_body_ends_in_sense_stop"] += int(body_r[-3:] in ("TAA", "TAG", "TGA"))
        else:
            kr = key_r[len(s2):] if key_r.startswith(s2) else key_r
            r["key_R_body_ends_in_sense_stop"] += int(kr[-3:] in ("TAA", "TAG", "TGA"))
            r["key_R_body_starts_with_rc_stop"] += int(kr[:3] in ("TTA", "CTA", "TCA"))
        r["has_pair"] += int("D" in a and "K" in a)
        for arm in ("O", "D", "K"):
            if arm not in a:
                continue
            opts = a[arm]
            n_site_ok = 0
            for o in opts:
                parts = [x.strip() for x in o.split(",")]
                ok = len(parts) == 2 and parts[0].startswith(s1) and parts[1].startswith(s2)
                n_site_ok += int(ok)
            r[f"{arm}_n_site_correct"] += n_site_ok
            r[f"{arm}_key_only_site_correct"] += int(n_site_ok == 1 and
                                                     opts[0].split(",")[0].strip().startswith(s1))
            r[f"{arm}_key_is_parquet_ideal"] += int(opts[0] == it["ideal"])
            r[f"{arm}_dup_options"] += int(len(set(opts)) != len(opts))
        if "D" not in a or "K" not in a:
            continue
        # K vs D structural comparison: only one option differs?
        dk = [i for i in range(len(a["K"])) if a["K"][i] != a["D"][i]]
        r["n_options_differing_K_vs_D"] += len(dk)
        if len(dk) == 1:
            i = dk[0]
            r["replaced_len_K"] += len(a["K"][i])
            r["replaced_len_D"] += len(a["D"][i])
            # does the replaced option's body duplicate another option's body?
            def body(o):
                p = [x.strip() for x in o.split(",")]
                return (p[0][6:], p[1][6:]) if len(p) == 2 else (o, "")
            bK, bD = body(a["K"][i]), body(a["D"][i])
            others = [body(o) for j, o in enumerate(a["K"]) if j != i]
            r["K_replaced_body_matches_another_option"] += int(bK in others)
            othersD = [body(o) for j, o in enumerate(a["D"]) if j != i]
            r["D_replaced_body_matches_another_option"] += int(bD in othersD)
        opt_lens = {arm: [len(o) for o in a[arm]] for arm in ("K", "D")}
        r["K_total_len"] += sum(opt_lens["K"])
        r["D_total_len"] += sum(opt_lens["D"])
        r["key_is_longest_K"] += int(max(opt_lens["K"]) == opt_lens["K"][0] and
                                     opt_lens["K"].count(max(opt_lens["K"])) == 1)
        r["key_is_longest_D"] += int(max(opt_lens["D"]) == opt_lens["D"][0] and
                                     opt_lens["D"].count(max(opt_lens["D"])) == 1)

    out = {k: dict(v) for k, v in rep.items()}
    print(json.dumps(out, indent=1))
    (AUD / "validation" / "v3_verify.json").write_text(json.dumps(out, indent=1) + "\n")
    for n in notes:
        print(n)


if __name__ == "__main__":
    main()
