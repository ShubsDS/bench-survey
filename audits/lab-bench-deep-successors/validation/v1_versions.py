"""Validator, claim 1: options-only rules on every pinned SeqQA/DbQA release, own code.

Written without reading the auditor's scripts/versions.py. Rules (all see only the option strings):
  J3   : centroid by mean character-3-gram Jaccard to the other options (own re-implementation of
         the parent's idea).
  LEV  : summed Levenshtein distance to the other options, smallest wins (medoid).
  KMER : a third, new rule: number of distinct 8-mers an option shares with any other option,
         largest wins (meant to catch "distractors are edits of the key").
  NUM  : when every option parses as a number: the median (middle) value; ties split.
  SHA  : placebo, smallest sha1 of the option text.
For each subtask, the rule used for the "carries the cue" test is NUM if all options of all items
are numeric, else the best of J3/LEV (the auditor's threshold rule: >= 0.90 and p < 0.01).
Ties get fractional credit. Permutation null: the key drawn uniformly among an item's options,
1,000 draws, seed 0. Bootstrap over subtasks, 2,000 draws, seed 0.

Run: ../lab-bench/data/.venv/bin/python -I validation/v1_versions.py
Writes validation/v1_versions.json (aggregates and ids only, no item text).
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
AUD = HERE.parent
DATA = AUD / "data"
PARENT = AUD.parent / "lab-bench" / "data" / "hf"

REVS = {
    # earliest SeqQA parquet (sha256 09c7b26e...), live 2024-07-13 to 2024-07-16; not in the audit
    "983956ce": ("2024-07-13/16", DATA / "val_hfrev_983956ce"),
    "7268767a": ("2024-07-16", DATA / "hfrev_7268767a"),
    "10866fa8": ("2024-08-20", DATA / "hfrev_10866fa8"),
    "8e6bb002": ("2024-12-18", DATA / "hfrev_8e6bb002"),
    "4709d14f": ("2025-02-19", DATA / "hfrev_4709d14f"),
    "8137378e": ("2025-07-15", DATA / "hfrev_8137378e"),
    "5c77cec6": ("2025-09-27", PARENT),
}
S6 = ["ORF-seq-AAseq", "PCR-gene-enzprimers", "PCR-seq-enzprimers", "PCR-gene-gibshindprimers",
      "PCR-gene-gibssmaprimers", "Prop-seq-gcpercent"]


def lev(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    bv = np.frombuffer(b.encode("latin-1", "replace"), dtype=np.uint8)
    prev = np.arange(len(b) + 1)
    for i, ca in enumerate(a.encode("latin-1", "replace"), 1):
        sub = prev[:-1] + (bv != ca)
        cur = np.empty_like(prev)
        cur[0] = i
        cur[1:] = np.minimum(sub, prev[1:] + 1)
        # insertion pass (left-to-right running minimum)
        cur = np.minimum.accumulate(cur - np.arange(len(b) + 1)) + np.arange(len(b) + 1)
        prev = cur
    return int(prev[-1])


def grams(s, k):
    return {s[i:i + k] for i in range(max(1, len(s) - k + 1))}


def credit_from_scores(scores, best="max"):
    s = np.asarray(scores, dtype=float)
    tgt = s.max() if best == "max" else s.min()
    win = np.isclose(s, tgt)
    return win / win.sum()


def isnum(x):
    try:
        float(str(x).strip().rstrip("%"))
        return True
    except ValueError:
        return False


def rule_credits(opts):
    """Return dict rule -> credit vector over options (sums to 1)."""
    n = len(opts)
    out = {}
    g3 = [grams(o, 3) for o in opts]
    j = [np.mean([len(g3[i] & g3[k]) / max(1, len(g3[i] | g3[k])) for k in range(n) if k != i]) for i in range(n)]
    out["J3"] = credit_from_scores(j, "max")
    d = np.zeros((n, n))
    for i in range(n):
        for k in range(i + 1, n):
            d[i, k] = d[k, i] = lev(opts[i], opts[k])
    out["LEV"] = credit_from_scores(d.sum(1), "min")
    g8 = [grams(o, 8) for o in opts]
    sh = [len(g8[i] & set().union(*[g8[k] for k in range(n) if k != i])) for i in range(n)]
    out["KMER"] = credit_from_scores(sh, "max")
    if all(isnum(o) for o in opts):
        v = np.array([float(str(o).strip().rstrip("%")) for o in opts])
        med = np.median(v)
        dist = np.abs(v - med)
        out["NUM"] = credit_from_scores(dist, "min")
        # NB1: derived from the paper's disclosed GC generator (App. C.7: distractors k-1, k+1, k/2):
        # the option with the most other options exactly 1 away wins.
        out["NB1"] = credit_from_scores([int(np.sum(np.isclose(np.abs(v - x), 1))) for x in v], "max")
    out["SHA"] = credit_from_scores([int(hashlib.sha1(o.encode()).hexdigest(), 16) for o in opts], "min")
    return out


def load(path, subset):
    df = pd.read_parquet(path / subset / "train-00000-of-00001.parquet")
    items = []
    for r in df.itertuples():
        opts = [str(r.ideal)] + [str(x) for x in list(r.distractors)]
        items.append({"id": r.id, "subtask": r.subtask.replace("-v1-public", "").replace("_task-v1-public", ""),
                      "opts": opts, "key": 0})
    return items


def score_subtask(items, rng):
    rules = {}
    per = [rule_credits(it["opts"]) for it in items]
    names = set.intersection(*[set(p) for p in per])
    res = {"n": len(items), "chance": round(float(np.mean([1 / len(it["opts"]) for it in items])), 4)}
    for nm in sorted(names):
        obs = float(np.mean([p[nm][0] for p in per]))
        null = np.zeros(1000)
        for t in range(1000):
            null[t] = np.mean([p[nm][rng.integers(len(p[nm]))] for p in per])
        pval = (1 + (null >= obs - 1e-12).sum()) / 1001
        res[nm] = round(obs, 4)
        res[nm + "_p"] = round(float(pval), 4)
    halves = {}
    for nm in sorted(names):
        hv = []
        for par in (0, 1):
            sel = [p[nm][0] for p, it in zip(per, items) if int(hashlib.sha1(it["id"].encode()).hexdigest(), 16) % 2 == par]
            hv.append(round(float(np.mean(sel)), 4) if sel else None)
        halves[nm] = hv
    res["halves"] = halves
    # main rule: numeric subtasks use the better of NUM (median) and NB1; others the better of J3/LEV
    cands = ["NUM", "NB1"] if "NUM" in names else ["J3", "LEV"]
    main = max(cands, key=lambda c: res[c])
    res["main_rule"] = main
    res["carries"] = bool(res[main] >= 0.90 and res[main + "_p"] < 0.01)
    # stricter: the cue counted only if it holds under the generic rules (J3/LEV/NUM-median), not NB1
    gen = ["NUM"] if "NUM" in names else ["J3", "LEV"]
    gm = max(gen, key=lambda c: res[c])
    res["carries_generic_rules"] = bool(res[gm] >= 0.90 and res[gm + "_p"] < 0.01)
    return res


def boot(vals, rng, B=2000):
    vals = np.asarray(vals)
    bs = [vals[rng.integers(len(vals), size=len(vals))].mean() for _ in range(B)]
    return [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)]


def main():
    rng = np.random.default_rng(0)
    out = {}
    ref_ids = None
    ref = {it["id"]: it for it in load(PARENT, "SeqQA")}
    for rev, (date, path) in REVS.items():
        sha = hashlib.sha256((path / "SeqQA" / "train-00000-of-00001.parquet").read_bytes()).hexdigest()
        items = load(path, "SeqQA")
        by = {}
        for it in items:
            by.setdefault(it["subtask"], []).append(it)
        per = {st: score_subtask(v, rng) for st, v in sorted(by.items())}
        carrying = [st for st, r in per.items() if r["carries"]]

        def mainval(r):
            return r[r["main_rule"]]
        S = [mainval(per[s]) for s in S6]
        allv = [mainval(r) for r in per.values()]
        lev_S = [per[s]["LEV"] if "NUM" not in per[s] else per[s]["NUM"] for s in S6]
        generic = [st for st, r in per.items() if r["carries_generic_rules"]]
        # identity vs parent pin
        shared = [i for i in (it["id"] for it in items) if i in ref]
        changed_key = sum(1 for it in items if it["id"] in ref and it["opts"][0] != ref[it["id"]]["opts"][0])
        changed_opts = sum(1 for it in items if it["id"] in ref and sorted(it["opts"]) != sorted(ref[it["id"]]["opts"]))
        new_by = {}
        for it in items:
            if it["id"] not in ref:
                new_by[it["subtask"]] = new_by.get(it["subtask"], 0) + 1
        # DbQA multi-sequence
        db = [it for it in load(path, "DbQA") if "variant_multi_sequence" in it["subtask"]]
        dbr = score_subtask(db, rng) if db else None
        out[rev] = {
            "date": date, "seqqa_sha256": sha, "n_items": len(items), "n_subtasks": len(by),
            "per_subtask_counts": {k: len(v) for k, v in by.items()},
            "carrying": carrying,
            "S6_carrying": [s for s in S6 if s in carrying],
            "carrying_generic_rules_only": generic,
            "S6_mainrule_mean": round(float(np.mean(S)), 4), "S6_mainrule_ci": boot(S, rng),
            "S6_lev_or_num_mean": round(float(np.mean(lev_S)), 4),
            "all15_mainrule_mean": round(float(np.mean(allv)), 4), "all15_ci": boot(allv, rng),
            "placebo_sha_all15": round(float(np.mean([r["SHA"] for r in per.values()])), 4),
            "vs_parent": {"shared_ids": len(shared), "key_changed": changed_key, "option_set_changed": changed_opts,
                          "new_ids_by_subtask": new_by},
            "dbqa_multi_seq": None if dbr is None else {k: dbr[k] for k in ("n", "J3", "LEV", "KMER", "SHA", "chance")},
            "per_subtask": per,
        }
        print(rev, date, len(items), "carrying:", carrying, "S main", out[rev]["S6_mainrule_mean"],
              "S lev/num", out[rev]["S6_lev_or_num_mean"], "placebo", out[rev]["placebo_sha_all15"],
              "db", out[rev]["dbqa_multi_seq"], "new", new_by, "keychg", changed_key, changed_opts)
    # HuggingFaceBio curated subset
    cur = pd.read_parquet(DATA / "hfbio_carbon_data" / "data" / "test-00000-of-00001.parquet")
    citems = []
    for r in cur.itertuples():
        opts = [str(x) for x in list(r.options)]
        k = int(r.answer_index)
        opts = [opts[k]] + [o for i, o in enumerate(opts) if i != k]
        citems.append({"id": r.id, "subtask": str(r.subtask), "opts": opts})
    cby = {}
    for it in citems:
        cby.setdefault(it["subtask"], []).append(it)
    out["hfbio_curated"] = {
        "n": len(citems), "ids_in_parent_pin": sum(1 for it in citems if it["id"] in ref),
        "keys_match_parent": sum(1 for it in citems if it["id"] in ref and it["opts"][0] == ref[it["id"]]["opts"][0]),
        "per_subtask": {st: score_subtask(its, rng) for st, its in sorted(cby.items())},
    }
    print("curated", json.dumps(out["hfbio_curated"], indent=0)[:1500])
    (HERE / "v1_versions.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
