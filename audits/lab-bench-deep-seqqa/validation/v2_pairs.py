"""Validator: paired K vs D analysis from validation/v1_rows.csv (my own rescoring).

Exact paired tests (McNemar binomial, two-sided), item bootstrap, subtask-cluster bootstrap,
drop-one-subtask, and the pick-rate of the new D centre against the other distractors.
Run: ../lab-bench/data/.venv/bin/python -I validation/v2_pairs.py
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from math import comb
from pathlib import Path

import numpy as np

AUD = Path(__file__).resolve().parent.parent
SUBTASKS = ["Prop-seq-gcpercent-v1", "ORF-seq-AAseq-v1", "PCR-gene-enzprimers-v1",
            "PCR-seq-enzprimers-v1", "PCR-gene-gibshindprimers-v1", "PCR-gene-gibssmaprimers-v1"]
GENE_ABSENT = {"PCR-gene-enzprimers-v1", "PCR-gene-gibshindprimers-v1", "PCR-gene-gibssmaprimers-v1"}


def rows():
    with open(AUD / "validation" / "v1_rows.csv") as fh:
        return list(csv.DictReader(fh))


def binom_two_sided(b: int, c: int) -> float:
    """Exact McNemar: P(|X - n/2| >= |b - n/2|) under Bin(n, 1/2), n = b + c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def holm(ps):
    idx = np.argsort(ps)
    out = [0.0] * len(ps)
    run = 0.0
    for rank, i in enumerate(idx):
        v = (len(ps) - rank) * ps[i]
        run = max(run, v)
        out[i] = min(1.0, run)
    return out


def boot_items(pairs, rng, B=2000):
    d = np.array([k - dd for k, dd, _ in pairs], float)
    n = len(d)
    s = np.array([d[rng.integers(0, n, n)].mean() for _ in range(B)])
    return float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))


def boot_subtasks(pairs, rng, B=2000):
    by = defaultdict(list)
    for k, dd, st in pairs:
        by[st].append(k - dd)
    keys = list(by)
    arrs = [np.array(by[k], float) for k in keys]
    out = []
    for _ in range(B):
        pick = rng.integers(0, len(keys), len(keys))
        vals = []
        for j in pick:
            a = arrs[j]
            vals.append(a[rng.integers(0, len(a), len(a))].mean())
        out.append(np.mean(vals))
    out = np.array(out)
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def sign_flip_p(pairs, B=20000, seed=0):
    """Permutation over the 6 subtask-level differences (sign flips): two-sided."""
    by = defaultdict(list)
    for k, dd, st in pairs:
        by[st].append(k - dd)
    d = np.array([np.mean(v) for v in by.values()])
    obs = abs(d.mean())
    rng = np.random.default_rng(seed)
    cnt = 0
    for _ in range(B):
        s = rng.choice([-1, 1], len(d))
        if abs((d * s).mean()) >= obs - 1e-12:
            cnt += 1
    return (cnt + 1) / (B + 1)


def main():
    R = rows()
    out = {}
    for model in ("sonnet", "haiku"):
        kd = defaultdict(dict)
        for r in R:
            if r["model"] != model:
                continue
            arm = r["arm"]
            if arm in ("K", "O/K"):
                kd[r["id"]]["K"] = r
            elif arm == "D":
                kd[r["id"]]["D"] = r
        pairs, picks = [], []
        arms = json.loads((AUD / "data" / "arms.json").read_text())
        for iid, v in kd.items():
            if "K" not in v or "D" not in v:
                continue
            st = v["K"]["subtask"]
            pairs.append((v["K"]["bucket"] == "correct", v["D"]["bucket"] == "correct", st))
            centre = arms[iid].get("D_centre") or []
            role = v["D"]["role"]
            picks.append((st, role, centre))
        rng = np.random.default_rng(0)
        res = {"n_pairs": len(pairs),
               "K": round(np.mean([p[0] for p in pairs]), 4),
               "D": round(np.mean([p[1] for p in pairs]), 4),
               "diff": round(np.mean([p[0] - p[1] for p in pairs]), 4),
               "ci_items": [round(x, 4) for x in boot_items(pairs, np.random.default_rng(0))],
               "ci_subtasks": [round(x, 4) for x in boot_subtasks(pairs, np.random.default_rng(1))],
               "b_K_only": sum(1 for a, b, _ in pairs if a and not b),
               "c_D_only": sum(1 for a, b, _ in pairs if b and not a)}
        res["mcnemar_exact_p"] = round(binom_two_sided(res["b_K_only"], res["c_D_only"]), 5)
        res["sign_flip_p_6_subtasks"] = round(sign_flip_p(pairs), 5)
        # per subtask
        per = {}
        ps = []
        for st in SUBTASKS:
            sub = [p for p in pairs if p[2] == st]
            b = sum(1 for a, c, _ in sub if a and not c)
            c = sum(1 for a, cc, _ in sub if cc and not a)
            per[st] = {"n": len(sub), "K": round(np.mean([x[0] for x in sub]), 4),
                       "D": round(np.mean([x[1] for x in sub]), 4), "K_only": b, "D_only": c,
                       "p_exact": round(binom_two_sided(b, c), 5)}
            ps.append(per[st]["p_exact"])
        for st, h in zip(SUBTASKS, holm(ps)):
            per[st]["p_holm"] = round(h, 4)
        res["per_subtask"] = per
        # drop one subtask
        res["drop_one_subtask"] = {st: round(np.mean([a - b for a, b, s in pairs if s != st]), 4)
                                   for st in SUBTASKS}
        # strata
        for name, sel in (("gene_absent", lambda s: s in GENE_ABSENT),
                          ("gene_present", lambda s: s not in GENE_ABSENT)):
            sub = [p for p in pairs if sel(p[2])]
            res[name] = {"n": len(sub), "diff": round(np.mean([a - b for a, b, _ in sub]), 4),
                         "ci_items": [round(x, 4) for x in boot_items(sub, np.random.default_rng(2))]}
        # centre pick rate under D among non-GC items (4 options: key + 3 distractors)
        cen = oth = cn = on = 0
        for st, role, centre in picks:
            if role == "" or role == "refuse":
                continue
            role = int(role)
            n_dist = 4 if st == "ORF-seq-AAseq-v1" else 3
            for j in range(1, n_dist + 1):
                if j in centre:
                    cn += 1
                    cen += int(role == j)
                else:
                    on += 1
                    oth += int(role == j)
        res["pick_centre"] = {"centre_rate": round(cen / cn, 4) if cn else None, "centre_n": cn,
                              "other_rate": round(oth / on, 4) if on else None, "other_n": on}
        out[model] = res
    print(json.dumps(out, indent=1))
    (AUD / "validation" / "v2_pairs.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
