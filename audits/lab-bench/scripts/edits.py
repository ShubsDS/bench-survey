"""L4 minimal edits: rebuild distractors so that a *distractor*, not the key, is the option
the others were derived from. The key and the question are unchanged.

Families (the six SeqQA subtasks where a content-blind rule scores 1.00):
  Prop-seq-gcpercent   original {x, x-1, x+1, x/2}: x is the centre.
                       edited   {x, x+d, x+2d, (x+d)/2}, d = +-1 by item hash: x+d is the centre.
  ORF-seq-AAseq        original {P, three 1-substitution variants of P, DNA}: P is the consensus.
                       edited   {P, V, two 1-substitution variants of V, DNA}: V is the consensus.
  PCR-gene-enzprimers, PCR-seq-enzprimers, PCR-gene-gibshindprimers, PCR-gene-gibssmaprimers
                       original {K, S (key site/overlap + shifted body), G (key site + other gene),
                                 W (other site + key body)}: K shares parts with all three.
                       edited   {K, S, W-site + S body, S shifted one more base}: S is central.
                       Error types kept: one wrong-site option, two frame-shifted options.
Each edited item is checked: the centroid rule (scripts/surface.py) must pick a distractor,
and the key must still be the only option that the construction calls correct.
Writes data/edits.json (contains item text; git-ignored) and results/edits_check.json.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import AUDIT, RESULTS, load_items  # noqa: E402
from surface import credit, grams, jacc, option_scores  # noqa: E402

AA = "ACDEFGHIKLMNPQRSTVWY"
FAMS = ["Prop-seq-gcpercent-v1", "ORF-seq-AAseq-v1", "PCR-gene-enzprimers-v1",
        "PCR-seq-enzprimers-v1", "PCR-gene-gibshindprimers-v1", "PCR-gene-gibssmaprimers-v1"]
N_PER = 25


def h(s: str) -> int:
    return int(hashlib.sha256(s.encode()).hexdigest()[:8], 16)


def common_suffix(a: str, b: str) -> int:
    n = 0
    while n < min(len(a), len(b)) and a[-1 - n] == b[-1 - n]:
        n += 1
    return n


def common_prefix(a: str, b: str) -> int:
    n = 0
    while n < min(len(a), len(b)) and a[n] == b[n]:
        n += 1
    return n


def edit_gc(r):
    x = int(r.ideal)
    d = 1 if h(r.id) % 2 else -1
    c = x + d
    half = int(np.floor(c / 2 + 0.5))
    return [str(x), str(c), str(x + 2 * d), str(half)], 1


def edit_aaseq(r):
    P = r.ideal
    vars_ = [d for d in r.distractors if len(d) == len(P) and sum(a != b for a, b in zip(d, P)) == 1]
    other = [d for d in r.distractors if d not in vars_]
    if len(vars_) < 1:
        return None, None
    V = vars_[0]
    diffpos = [i for i in range(len(P)) if P[i] != V[i]][0]
    rng = np.random.default_rng(h(r.id))
    cand = [i for i in range(1, len(V) - 1) if i != diffpos and V[i] in AA]
    if len(cand) < 2:
        return None, None
    new = []
    for pos in rng.choice(cand, 2, replace=False):
        aa = rng.choice([a for a in AA if a != V[pos]])
        new.append(V[:pos] + aa + V[pos + 1:])
    return [P, V] + new + other, 1


def split_pair(s):
    f, r = [x.strip() for x in s.split(",")]
    return f, r


def edit_pcr(r):
    K = split_pair(r.ideal)
    D = [split_pair(d) for d in r.distractors]
    # W: same bodies as K (longest common suffixes on both primers)
    suf = [common_suffix(K[0], d[0]) + common_suffix(K[1], d[1]) for d in D]
    wi = int(np.argmax(suf))
    W = D[wi]
    rest = [d for i, d in enumerate(D) if i != wi]
    pf = [len(K[k]) - common_suffix(K[k], W[k]) for k in (0, 1)]  # key prefix lengths
    pw = [len(W[k]) - common_suffix(K[k], W[k]) for k in (0, 1)]  # W prefix lengths
    if min(pf) < 4 or min(pw) < 4:
        return None, None
    # S: the remaining option whose bodies are closest to K's after the prefix (shifted)
    def body_sim(d):  # 3-gram similarity of the primer bodies to the key's bodies
        return sum(jacc(grams(K[k][pf[k]:]), grams(d[k][pf[k]:])) for k in (0, 1))
    if not all(d[k].startswith(K[k][:pf[k]]) for d in rest for k in (0, 1)):
        return None, None
    S = max(rest, key=body_sim)
    WS = tuple(W[k][:pw[k]] + S[k][pf[k]:] for k in (0, 1))
    S2 = tuple(S[k][:pf[k] + (3 if k == 0 and S[k][pf[k]:pf[k] + 3] == "ATG" else 0)]
               + S[k][pf[k] + (3 if k == 0 and S[k][pf[k]:pf[k] + 3] == "ATG" else 0) + 1:]
               for k in (0, 1))
    opts = [", ".join(K), ", ".join(S), ", ".join(WS), ", ".join(S2)]
    if len(set(opts)) < 4:
        return None, None
    return opts, 1


def placebo_pcr(r):
    """Post hoc control (added after the L4 result): same procedure, but centred on the key:
    {K, S, W, K shifted one base}. The key stays the option the others derive from."""
    K = split_pair(r.ideal)
    D = [split_pair(d) for d in r.distractors]
    suf = [common_suffix(K[0], d[0]) + common_suffix(K[1], d[1]) for d in D]
    wi = int(np.argmax(suf))
    W = D[wi]
    rest = [d for i, d in enumerate(D) if i != wi]
    pf = [len(K[k]) - common_suffix(K[k], W[k]) for k in (0, 1)]
    def body_sim(d):
        return sum(jacc(grams(K[k][pf[k]:]), grams(d[k][pf[k]:])) for k in (0, 1))
    S = max(rest, key=body_sim)
    skip = [3 if k == 0 and K[k][pf[k]:pf[k] + 3] == "ATG" else 0 for k in (0, 1)]
    K2 = tuple(K[k][:pf[k] + skip[k]] + K[k][pf[k] + skip[k] + 1:] for k in (0, 1))
    return [", ".join(K), ", ".join(S), ", ".join(W), ", ".join(K2)]


def main() -> None:
    df = load_items(check=False)
    rng = np.random.default_rng(0)
    edits, check = {}, {}
    for fam in FAMS:
        g = df[df.subtask == fam]
        ids = sorted(g.id)
        order = list(rng.permutation(ids))
        done = []
        fails = 0
        for i in order:
            if len(done) >= N_PER:
                break
            r = g[g.id == i].iloc[0]
            if fam.startswith("Prop"):
                opts, central = edit_gc(r)
            elif fam.startswith("ORF"):
                opts, central = edit_aaseq(r)
            else:
                opts, central = edit_pcr(r)
            if opts is None:
                fails += 1
                continue
            sc = option_scores(opts)
            rule = "num_center" if "num_center" in sc else "centroid"
            key_credit = credit(*sc[rule][:1], key=0, higher=True)
            cen_credit = credit(*sc[rule][:1], key=central, higher=True)
            orig = option_scores([r.ideal] + list(r.distractors))
            orule = "num_center" if "num_center" in orig else "centroid"
            if key_credit > 0 or cen_credit < 1:
                fails += 1
                continue
            edits[i] = {"family": fam, "options": opts, "central": central}
            if "gibs" in fam:
                po = placebo_pcr(r)
                ps = option_scores(po)["centroid"][0]
                if credit(ps, key=0) == 1.0 and len(set(po)) == 4:
                    edits[i]["placebo_options"] = po
            done.append({"id": i, "rule": rule, "orig_rule_key_credit": credit(*orig[orule][:1], key=0),
                         "edit_rule_key_credit": key_credit, "edit_rule_central_credit": cen_credit})
        check[fam] = {"n": len(done), "skipped": fails, "items": done}
    (AUDIT / "data" / "edits.json").write_text(json.dumps(edits))
    (RESULTS / "edits_check.json").write_text(json.dumps(check, indent=1))
    print({f: (c["n"], c["skipped"]) for f, c in check.items()})


if __name__ == "__main__":
    main()
