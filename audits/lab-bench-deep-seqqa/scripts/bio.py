"""Sequence helpers for verifying SeqQA keys by computation (no third-party code).

Standard genetic code (NCBI table 1). ORFs are ATG..stop on both strands, all six frames,
as in the benchmark's construction notes (App. C.7).
"""
from __future__ import annotations

import re

COMP = str.maketrans("ACGTUacgtu", "TGCAAtgcaa")
BASES = "TCAG"
AAS = "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG"
CODON = {a + b + c: AAS[16 * i + 4 * j + k]
         for i, a in enumerate(BASES) for j, b in enumerate(BASES) for k, c in enumerate(BASES)}
STOPS = {"TAA", "TAG", "TGA"}

# Recognition sites of the enzymes named in the SeqQA PCR templates (pUC19 MCS enzymes)
SITES = {"EcoRI": "GAATTC", "SacI": "GAGCTC", "SstI": "GAGCTC", "KpnI": "GGTACC",
         "SmaI": "CCCGGG", "XmaI": "CCCGGG", "BamHI": "GGATCC", "XbaI": "TCTAGA",
         "SalI": "GTCGAC", "PstI": "CTGCAG", "SphI": "GCATGC", "HindIII": "AAGCTT"}


def rc(s: str) -> str:
    return s.translate(COMP)[::-1]


def translate(nt: str, to_stop: bool = False) -> str:
    out = []
    for i in range(0, len(nt) - 2, 3):
        aa = CODON.get(nt[i:i + 3], "X")
        out.append(aa)
        if to_stop and aa == "*":
            break
    return "".join(out)


def orfs(seq: str, min_aa: int = 0) -> list[dict]:
    """All ATG-initiated ORFs ending in a stop codon, both strands, nested starts included."""
    seq = seq.upper().replace("U", "T")
    res = []
    for strand, s in (("+", seq), ("-", rc(seq))):
        for f in range(3):
            for i in range(f, len(s) - 2, 3):
                if s[i:i + 3] != "ATG":
                    continue
                for j in range(i, len(s) - 2, 3):
                    if s[j:j + 3] in STOPS:
                        prot = translate(s[i:j + 3])
                        if len(prot) - 1 >= min_aa:
                            res.append({"strand": strand, "start": i, "end": j + 3, "prot": prot})
                        break
    return res


def longest_orf(seq: str) -> tuple[str | None, int]:
    """Protein (with trailing *) of the longest ORF, and the number of distinct proteins of that length."""
    o = orfs(seq)
    if not o:
        return None, 0
    m = max(len(x["prot"]) for x in o)
    best = sorted({x["prot"] for x in o if len(x["prot"]) == m})
    return best[0], len(best)


def gc_percent(seq: str) -> float:
    s = seq.upper()
    return 100.0 * (s.count("G") + s.count("C")) / len(s)


def comp_percent(seq: str, letters: str) -> float:
    s = seq.upper()
    return 100.0 * sum(s.count(b) for b in letters) / len(s)


DNA_RE = re.compile(r"[ACGTU]{30,}")


def longest_dna(text: str) -> str:
    m = DNA_RE.findall(text)
    return max(m, key=len) if m else ""
