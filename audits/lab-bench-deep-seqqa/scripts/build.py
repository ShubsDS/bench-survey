"""Build the paired arms for the six cue-bearing SeqQA subtasks and verify every key.

No inference. Reads the parent's pinned parquet (audits/lab-bench/data/hf, sha256 checked by the
parent's common.load_items). Writes
  data/arms.json            option lists per item and arm (item text; git-ignored)
  build_check.json          ids, per-item verification and centre checks, drop reasons (no text)

Arms (prereg.md):
  O  original options.
  D  decoy-centred: question and key unchanged; distractors rebuilt by the benchmark's own kind
     of edit around a WRONG option, so a distractor becomes the centre.
  K  key-centred: the same rebuild applied around the key (the key stays the centre).
  I  independent distractors (Prop-seq-gcpercent only): wrong answers from distinct error
     processes (other base compositions), none derived from the key or from each other.
  N  options only (built at render time from O; no question).

Per family:
  Prop-seq-gcpercent  O {x, x+s, x-s, r(x/2)} (s = +-1 by hash; the benchmark's own generator)
                      D {x, x+s, x+2s, r((x+s)/2)}  (x-s -> x+2s, x/2 -> (x+s)/2; centre x+s)
                      K  = O: the generator applied around the key reproduces O exactly
                      I {x, AT%, purine (A+G)%, keto (G+T)%}, falling back to (C+T)%, (A+C)%
  ORF-seq-AAseq       O {P, three 1-residue substitutions of P, a DNA string}
                      D {P, V, V', V'', DNA}: V one original substitution (by hash), V' V'' new
                        1-residue substitutions of V (the two other originals replaced in place)
                      K {P, V, P', P'', DNA}: P' P'' new 1-residue substitutions of P
  PCR families (gene-enz, seq-enz, gene-gibshind, gene-gibssma)
                      O {K, S (key site + shifted body), G (key site + other gene), W (wrong site + key body)}
                      D {K, S, G, W'+S body}   one option replaced (W), wrong site W' new
                      K {K, S, G, W'+K body}   the same option replaced, same new wrong site W'
                      W' = a different enzyme pair (enz) or the pUC19 junction at a different cut
                      (XbaI or BamHI, gibson); identical string in D and K. D and K differ only in
                      the body carried by the replaced option.
Checks (an item enters a D/K pair only if all pass):
  key verified by computation where the task allows (GC%, forward longest ORF translation, named
  sites/junctions, gene prefix/suffix for PCR-seq-enzprimers); every rebuilt distractor verified
  wrong; all options distinct; centre under BOTH the parent's 3-gram centroid and a summed
  Levenshtein medoid (num_center for numbers) is a distractor in D and the key in K.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AUD = HERE.parent
PARENT = AUD.parent / "lab-bench"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PARENT / "scripts"))
from bio import SITES, comp_percent, gc_percent, longest_dna, orfs, rc  # noqa: E402
from common import load_items  # noqa: E402
from surface import option_scores  # noqa: E402

CUE = ["Prop-seq-gcpercent-v1", "ORF-seq-AAseq-v1", "PCR-gene-enzprimers-v1",
       "PCR-seq-enzprimers-v1", "PCR-gene-gibshindprimers-v1", "PCR-gene-gibssmaprimers-v1"]
NONCUE = ["ORF-seq-AAid-v1", "ORF-seq-numlen-v1", "ORF-transeff-v1", "PCR-geneprimers-enz-v1",
          "PCR-len-primers-v1", "PCR-primers-len-v1", "PCR-seq-primers-v1",
          "RE-seq-lenfrags-v1", "RE-seq-numfrags-v1"]
AA = "ACDEFGHIKLMNPQRSTVWY"
# pUC19 MCS region, reconstructed from the keys' own Gibson overlaps (HincII and SmaI junctions);
# build() asserts that both benchmark junctions are reproduced from it.
MCS = "GATTACGCCAAGCTTGCATGCCTGCAGGTCGACTCTAGAGGATCCCCGGGTACCGAGCTCGAATTCACTGGCCGTCG"
CUTS = {"HindII": 30, "HincII": 30, "SmaI": 47, "XbaI": 34, "BamHI": 40}
MCS_ENZ = ["EcoRI", "SacI", "KpnI", "SmaI", "BamHI", "XbaI", "SalI", "PstI", "SphI", "HindIII"]


def h(s: str) -> int:
    return int(hashlib.sha256(s.encode()).hexdigest()[:8], 16)


def rhu(v: float) -> int:  # round half up
    return int(np.floor(v + 0.5))


def junction(enz: str) -> tuple[str, str]:
    c = CUTS[enz]
    return MCS[c - 30:c], rc(MCS[c:c + 30])


def lev(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def centres(opts: list[str]) -> dict:
    """Index sets picked by the parent's 3-gram centroid (or num_center) and a Levenshtein medoid."""
    sc = option_scores(opts)
    if "num_center" in sc:
        v, _ = sc["num_center"]
        a = [i for i, x in enumerate(v) if np.isclose(x, max(v))] if max(v) > 0 else list(range(len(v)))
        nums = [float(o) for o in opts]
        d = [sum(abs(nums[i] - nums[j]) for j in range(len(opts))) for i in range(len(opts))]
    else:
        v, _ = sc["centroid"]
        a = [i for i, x in enumerate(v) if np.isclose(x, max(v))]
        d = [sum(lev(opts[i], opts[j]) for j in range(len(opts))) for i in range(len(opts))]
    b = [i for i, x in enumerate(d) if x == min(d)]
    return {"rule1": a, "rule2": b}


def subst(s: str, pos: int, rng) -> str:
    aa = rng.choice([a for a in AA if a != s[pos]])
    return s[:pos] + aa + s[pos + 1:]


# ------------------------------------------------------------------ families
def fam_gc(r):
    seq = longest_dna(r.question)
    v = gc_percent(seq)
    x = int(r.ideal)
    info = {"gc": round(v, 3), "key_ok": rhu(v) == x}
    if not info["key_ok"]:
        return None, "key_not_verified", info
    O = [r.ideal] + list(r.distractors)
    vals = [int(o) for o in O]
    others = sorted(vals[1:])
    halves = {int(np.floor(x / 2)), int(np.ceil(x / 2))}
    if not any(sorted([x + 1, x - 1, hv]) == others for hv in halves):
        return None, "O_not_generator_pattern", info
    s = 1 if h(r.id) % 2 else -1  # which neighbour becomes the centre in D: by hash
    D = []
    for o in vals:
        if o == x:
            D.append(x)
        elif o == x + s:
            D.append(x + s)
        elif o == x - s:
            D.append(x + 2 * s)
        else:
            D.append(rhu((x + s) / 2))
    half = seq[: len(seq) // 2]
    cands = [("AT", 100 - v), ("AG", comp_percent(seq, "AG")), ("GT", comp_percent(seq, "GT")),
             ("GC_first_half", gc_percent(half)), ("CT", comp_percent(seq, "CT")),
             ("AC", comp_percent(seq, "AC")), ("GC_first_third", gc_percent(seq[: len(seq) // 3])),
             ("GC_last_quarter", gc_percent(seq[-(len(seq) // 4):]))]
    I, src = [x], []
    for name, val in cands:
        rv = rhu(val)
        if len(I) == 4 or rv in I:
            continue
        trial = I + [rv]
        # never let the key become a symmetric middle (x - d, x + d) of the others
        if any(a < x < b and a + b == 2 * x for a in trial[1:] for b in trial[1:]):
            continue
        I.append(rv)
        src.append(name)
    info["I_sources"] = src
    arms = {"O": O, "D": [str(z) for z in D], "K": O, "I": [str(z) for z in I] if len(I) == 4 else None}
    info["D_centre_value_offset"] = s
    return arms, None, info


def fam_aa(r):
    seq = longest_dna(r.question)
    fwd = [o for o in orfs(seq) if o["strand"] == "+"]
    m = max(len(o["prot"]) for o in fwd)
    best = {o["prot"] for o in fwd if len(o["prot"]) == m}
    both = orfs(seq)
    mb = max(len(o["prot"]) for o in both)
    info = {"fwd_longest_unique": len(best) == 1, "key_is_fwd_longest": r.ideal in best,
            "rev_strand_longer": mb > m}
    if r.ideal not in best or len(best) != 1:
        return None, "key_not_verified_or_tie", info
    P = r.ideal
    O = [P] + list(r.distractors)
    subs = [i for i, d in enumerate(O[1:], 1) if len(d) == len(P) and sum(a != b for a, b in zip(d, P)) == 1]
    if len(subs) != 3:
        return None, "O_not_three_substitutions", info
    vi = subs[h(r.id) % 3]
    V = O[vi]
    vpos = [i for i in range(len(P)) if P[i] != V[i]][0]
    rng = np.random.default_rng(h(r.id + ":aa"))
    pos = [i for i in range(1, len(P) - 1) if i != vpos and P[i] in AA]
    p2 = rng.choice(pos, 4, replace=False)
    Dnew = [subst(V, int(p2[0]), rng), subst(V, int(p2[1]), rng)]
    Knew = [subst(P, int(p2[2]), rng), subst(P, int(p2[3]), rng)]
    D, K = list(O), list(O)
    j = 0
    for i in subs:
        if i == vi:
            continue
        D[i], K[i] = Dnew[j], Knew[j]
        j += 1
    for arm in (D, K):
        if P in arm[1:] or len(set(arm)) != len(arm):
            return None, "rebuild_collision", info
    return {"O": O, "D": D, "K": K, "I": None}, None, info


ENZ_RE = re.compile(r"with the enzymes (\w+) and (\w+)")
LIN_RE = re.compile(r"linearize the plasmid with (\w+)")


def split_pair(s):
    return [x.strip() for x in s.split(",")]


def csuf(a, b):
    n = 0
    while n < min(len(a), len(b)) and a[-1 - n] == b[-1 - n]:
        n += 1
    return n


def compatible(a: str, b: str) -> bool:
    """Primer bodies that start at the same base (one a prefix of the other)."""
    n = min(len(a), len(b))
    return a[:n] == b[:n]


def fam_pcr(r):
    fam = r.subtask
    O = [r.ideal] + list(r.distractors)
    K = split_pair(r.ideal)
    Ds = [split_pair(d) for d in r.distractors]
    info = {}
    gib = "gibs" in fam
    if gib:
        enz = LIN_RE.search(r.question).group(1)
        want = junction(enz)
        plen = (30, 30)
    else:
        e1, e2 = ENZ_RE.search(r.question).groups()
        want = (SITES[e1], SITES[e2])
        plen = (6, 6)
    info["key_site_ok"] = K[0][:plen[0]] == want[0] and K[1][:plen[1]] == want[1]
    if not info["key_site_ok"]:
        return None, "key_site_not_verified", info
    if fam == "PCR-seq-enzprimers-v1":
        gene = longest_dna(r.question)
        # benchmark convention (40/40 keys): forward = site + gene 5' end; reverse = site + gene
        # 3' end in SENSE orientation (not reverse-complemented); see README.
        info["key_gene_ok"] = gene.startswith(K[0][6:]) and gene.endswith(K[1][6:])
        if not info["key_gene_ok"]:
            return None, "key_gene_not_verified", info
    wis = [i for i, d in enumerate(Ds) if all(d[t][plen[t]:] == K[t][plen[t]:] for t in (0, 1))
           and any(d[t][:plen[t]] != want[t] for t in (0, 1))]
    if len(wis) != 1:
        return None, "W_not_site_swap", info
    wi = wis[0]
    W = Ds[wi]
    rest = [(i, d) for i, d in enumerate(Ds) if i != wi]
    if not all(d[t][:plen[t]] == want[t] for _, d in rest for t in (0, 1)):
        return None, "rest_not_key_site", info
    bd = [sum(lev(K[t][plen[t]:], d[t][plen[t]:]) for t in (0, 1)) for _, d in rest]
    if bd[0] == bd[1]:
        return None, "S_ambiguous", info
    (si, S), (gi, G) = (rest[0], rest[1]) if bd[0] < bd[1] else (rest[1], rest[0])
    # S and G must be wrong by the benchmark's construction: bodies not starting where the key's do
    for name, d in (("S", S), ("G", G)):
        if compatible(d[0][plen[0]:], K[0][plen[0]:]) and compatible(d[1][plen[1]:], K[1][plen[1]:]):
            return None, f"{name}_not_wrong", info
    # new wrong site W', identical in D and K
    if gib:
        choices = [e for e in ("XbaI", "BamHI")]
        wenz = choices[h(r.id) % 2]
        Wp = junction(wenz)
        info["Wprime"] = wenz
    else:
        used = {K[0][:6], K[1][:6], W[0][:6], W[1][:6]}
        pool = [e for e in MCS_ENZ if SITES[e] not in used]
        rng = np.random.default_rng(h(r.id + ":enz"))
        a, b = rng.choice(len(pool), 2, replace=False)
        Wp = (SITES[pool[a]], SITES[pool[b]])
        info["Wprime"] = [pool[a], pool[b]]
    if Wp[0] == want[0] or Wp[1] == want[1]:
        return None, "Wprime_not_wrong", info
    WS = [Wp[t] + S[t][plen[t]:] for t in (0, 1)]
    WK = [Wp[t] + K[t][plen[t]:] for t in (0, 1)]
    D, Kk = list(O), list(O)
    D[wi + 1] = ", ".join(WS)
    Kk[wi + 1] = ", ".join(WK)
    for arm in (D, Kk):
        if len(set(arm)) != 4 or r.ideal in arm[1:]:
            return None, "rebuild_collision", info
    info["roles"] = {"S": si + 1, "G": gi + 1, "W": wi + 1}
    return {"O": O, "D": D, "K": Kk, "I": None}, None, info


def main() -> None:
    # junction self-check against the benchmark's keys
    assert junction("HindII") == ("GATTACGCCAAGCTTGCATGCCTGCAGGTC", "GAGCTCGGTACCCGGGGATCCTCTAGAGTC")
    assert junction("SmaI") == ("ATGCCTGCAGGTCGACTCTAGAGGATCCCC", "CGACGGCCAGTGAATTCGAGCTCGGTACCC")
    df = load_items()
    sq = df[df.subset == "SeqQA"]
    arms, check = {}, {"families": {}, "items": {}}
    for fam in CUE:
        g = sq[sq.subtask == fam].sort_values("id")
        tally = {"n": len(g), "kept_pair": 0, "dropped": {}, "centre_O_key": 0}
        for _, r in g.iterrows():
            fn = fam_gc if fam.startswith("Prop") else fam_aa if fam.startswith("ORF") else fam_pcr
            a, why, info = fn(r)
            rec = {"family": fam, **{k: v for k, v in info.items() if k != "roles"}}
            if a is None:
                tally["dropped"][why] = tally["dropped"].get(why, 0) + 1
                rec["dropped"] = why
                arms[r.id] = {"family": fam, "O": [r.ideal] + list(r.distractors)}
                check["items"][r.id] = rec
                continue
            c = {k: centres(v) for k, v in a.items() if v is not None}
            rec["centres"] = c
            rules = ["rule1"] if fam.startswith("Prop") else ["rule1", "rule2"]  # medoid ties on GC O
            okO = all(c["O"][k] == [0] for k in rules)
            okD = all(0 not in c["D"][k] for k in rules)
            okK = all(c["K"][k] == [0] for k in rules)
            tally["centre_O_key"] += okO
            if not (okD and okK):
                why = "centre_check_failed"
                tally["dropped"][why] = tally["dropped"].get(why, 0) + 1
                rec["dropped"] = why
                arms[r.id] = {"family": fam, "O": a["O"]}
            else:
                tally["kept_pair"] += 1
                arms[r.id] = {"family": fam, **{k: v for k, v in a.items() if v is not None},
                              "D_centre": [i for i in c["D"]["rule1"]]}
            if a.get("I") is not None:
                rec["I_key_centre_rule1"] = 0 in c["I"]["rule1"]
                rec["I_key_centre_rule2"] = 0 in c["I"]["rule2"]
            check["items"][r.id] = rec
        check["families"][fam] = tally
        print(fam, tally)
    for fam in NONCUE:
        for _, r in sq[sq.subtask == fam].iterrows():
            arms[r.id] = {"family": fam, "O": [r.ideal] + list(r.distractors)}
    (AUD / "data").mkdir(exist_ok=True)
    (AUD / "data" / "arms.json").write_text(json.dumps(arms))
    (AUD / "build_check.json").write_text(json.dumps(check, indent=1))


if __name__ == "__main__":
    main()
