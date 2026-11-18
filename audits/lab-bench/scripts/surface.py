"""Content-blind answer-surface rules on the public LAB-Bench items (L1/L2).

Every rule sees only the option strings of one item: never the question, figure, table,
paper or sequence in the question. Ties get fractional credit (1/|ties| if the key is
among them). Chance for an item is 1/n_options (the harness's added "Insufficient
information" option is not offered to rules; rules never abstain).

Rules (fixed before computing any accuracy; see prereg.md):
  longest, shortest        by character length
  centroid                 option with the highest mean character-3-gram Jaccard similarity
                           to the other options ("the option the distractors were built from")
  num_median               items whose options are all single numbers: option nearest the
                           median of the option values
  num_neighbors            items whose options are all single numbers: option with the most
                           other options within +-2 of it (construction docs: +-1/+-2 perturbations)
Held-out selection: for each template family, the best of {longest, shortest, centroid}
is chosen on a random half of items and scored on the other half (and vice versa).

Outputs: results/surface.json (aggregates) and results/surface_items.csv (ids, flags; no text).
"""
from __future__ import annotations

import json
import sys
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import RESULTS, cluster_boot, clusters, load_items, numbers  # noqa: E402

SEED = 0
GENERIC = ["longest", "shortest", "centroid"]


def grams(s: str, n: int = 3) -> Counter:
    s = " ".join(s.lower().split())
    if len(s) < n:
        return Counter([s])
    return Counter(s[i:i + n] for i in range(len(s) - n + 1))


def jacc(a: Counter, b: Counter) -> float:
    inter = sum((a & b).values())
    union = sum((a | b).values())
    return inter / union if union else 1.0


def credit(scores: list[float], key: int = 0, higher: bool = True) -> float:
    s = np.asarray(scores, dtype=float)
    best = s.max() if higher else s.min()
    ties = np.where(np.isclose(s, best))[0]
    return (1.0 / len(ties)) if key in ties else 0.0


def item_rules(opts: list[str]) -> dict[str, float]:
    out = {}
    lens = [len(o) for o in opts]
    out["longest"] = credit(lens, higher=True)
    out["shortest"] = credit(lens, higher=False)
    g = [grams(o) for o in opts]
    cen = [np.mean([jacc(g[i], g[j]) for j in range(len(opts)) if j != i]) for i in range(len(opts))]
    out["centroid"] = credit(cen, higher=True)
    nums = [numbers(o) for o in opts]
    stripped = [o.strip().rstrip("%").strip() for o in opts]
    single = all(len(n) == 1 for n in nums) and all(
        s.replace(".", "", 1).replace("-", "", 1).isdigit() for s in stripped)
    if single:
        v = np.array([n[0] for n in nums])
        med = np.median(v)
        out["num_median"] = credit(np.abs(v - med), higher=False)
        neigh = [int(np.sum((np.abs(v - v[i]) <= 2) & (np.arange(len(v)) != i))) for i in range(len(v))]
        out["num_neighbors"] = credit(neigh, higher=True)
        # symmetric centre: number of pairs (x-d, x+d), d > 0, among the other options.
        # Defined after reading 14 ORF-seq-numlen and 14 gcpercent items (see prereg.md).
        cen_pairs = []
        for i in range(len(v)):
            others = [v[j] for j in range(len(v)) if j != i]
            cen_pairs.append(sum(1 for a in others for b in others
                                 if a < v[i] < b and np.isclose(v[i] - a, b - v[i])))
        out["num_center"] = credit(cen_pairs, higher=True) if max(cen_pairs) > 0 else 1.0 / len(v)
    else:
        out["num_median"] = np.nan
        out["num_neighbors"] = np.nan
        out["num_center"] = np.nan
    return out


def cross_item_leak(df: pd.DataFrame) -> pd.Series:
    """Dataset-level leak, not a single-item rule: within a template family, pick the
    option that appears least often as a *distractor* of other items (ties fractional)."""
    out = pd.Series(np.nan, index=df.index)
    for fam, g in df.groupby("family"):
        cnt = Counter(d for ds in g.distractors for d in ds)
        for idx, r in g.iterrows():
            opts = [r.ideal] + list(r.distractors)
            own = Counter(r.distractors)
            score = [cnt[o] - own[o] for o in opts]
            out[idx] = credit(score, higher=False)
    return out


def option_scores(opts: list[str]) -> dict[str, tuple[list[float], bool]]:
    """Per-option score vectors for the rules used in held-out selection (higher flag)."""
    out = {"longest": ([len(o) for o in opts], True), "shortest": ([len(o) for o in opts], False)}
    g = [grams(o) for o in opts]
    out["centroid"] = ([float(np.mean([jacc(g[i], g[j]) for j in range(len(opts)) if j != i]))
                        for i in range(len(opts))], True)
    nums = [numbers(o) for o in opts]
    stripped = [o.strip().rstrip("%").strip() for o in opts]
    if all(len(n) == 1 for n in nums) and all(
            x.replace(".", "", 1).replace("-", "", 1).isdigit() for x in stripped):
        v = [n[0] for n in nums]
        pairs = []
        for i in range(len(v)):
            others = [v[j] for j in range(len(v)) if j != i]
            pairs.append(float(sum(1 for a in others for b in others
                                   if a < v[i] < b and np.isclose(v[i] - a, b - v[i]))))
        out["num_center"] = (pairs, True)
    return out


def main() -> None:
    df = load_items()
    df["cluster"] = clusters(df)
    rows, vecs = [], {}
    for _, r in df.iterrows():
        opts = [r.ideal] + list(r.distractors)
        d = {"id": r.id, "subset": r.subset, "family": r.family, "cluster": r.cluster,
             "n_options": len(opts), "chance": 1.0 / len(opts)}
        d.update(item_rules(opts))
        rows.append(d)
        vecs[r.id] = option_scores(opts)
    it = pd.DataFrame(rows)
    it["cross_item"] = cross_item_leak(df).values

    def pool(ids):
        rules = list(GENERIC)
        if all("num_center" in vecs[i] for i in ids):
            rules.append("num_center")
        return rules

    def score(i, rule, key=0):
        sc, hi = vecs[i][rule]
        if rule == "num_center" and max(sc) == 0:
            return 1.0 / len(sc)
        return credit(sc, key, hi)

    # held-out best rule per family: choose on one half (by cluster), score on the other
    rng = np.random.default_rng(SEED)
    it["half"] = 0
    for fam, g in it.groupby("family"):
        cl = np.array(sorted(g.cluster.unique()), dtype=object)
        rng.shuffle(cl)
        h1 = set(cl[: len(cl) // 2])
        it.loc[g.index, "half"] = g.cluster.map(lambda c: 1 if c in h1 else 2).values

    def heldout(ids, half, keys):
        rules = pool(ids)
        res, chosen = {}, {}
        for h in (1, 2):
            tr = [i for i in ids if half[i] != h]
            te = [i for i in ids if half[i] == h]
            if not tr or not te:
                continue
            best = max(rules, key=lambda c: np.mean([score(i, c, keys[i]) for i in tr]))
            for i in te:
                res[i] = score(i, best, keys[i])
                chosen[i] = best
        return res, chosen

    it["heldout_best"] = np.nan
    it["heldout_rule"] = ""
    nulls = {}
    prng = np.random.default_rng(SEED + 1)
    for fam, g in it.groupby("family"):
        ids = g.id.tolist()
        half = dict(zip(g.id, g.half))
        res, chosen = heldout(ids, half, {i: 0 for i in ids})
        it.loc[g.index, "heldout_best"] = g.id.map(res).values
        it.loc[g.index, "heldout_rule"] = g.id.map(chosen).values
        vals = []
        for _ in range(1000):  # permutation null: key position shuffled within each item
            keys = {i: int(prng.integers(len(vecs[i]["longest"][0]))) for i in ids}
            r2, _ = heldout(ids, half, keys)
            vals.append(np.mean(list(r2.values())))
        nulls[fam] = vals
    it["num_center"] = [score(i, "num_center") if "num_center" in vecs[i] else np.nan for i in it.id]

    summary = {"families": {}, "subsets": {}}
    for fam, g in it.groupby("family"):
        obs = g.heldout_best.mean()
        nv = np.array(nulls[fam])
        entry = {"n": int(len(g)), "clusters": int(g.cluster.nunique()),
                 "chance": round(float(g.chance.mean()), 4)}
        for c in GENERIC + ["num_median", "num_neighbors", "num_center", "cross_item"]:
            v = g[c].dropna()
            if len(v):
                entry[c] = round(float(v.mean()), 4)
                entry[c + "_n"] = int(len(v))
        entry["heldout_best"] = round(float(obs), 4)
        entry["heldout_best_ci"] = [round(x, 4) for x in cluster_boot(g.heldout_best.values, g.cluster.values)]
        entry["heldout_rules"] = dict(Counter(g.heldout_rule))
        entry["null_heldout_95"] = round(float(np.nanpercentile(nv, 95)), 4)
        entry["p_perm"] = round(float((np.sum(nv >= obs) + 1) / (len(nv) + 1)), 4)
        summary["families"][fam] = entry
    for s, g in it.groupby("subset"):
        entry = {"n": int(len(g)), "clusters": int(g.cluster.nunique()),
                 "chance": round(float(g.chance.mean()), 4)}
        for c in GENERIC + ["cross_item"]:
            entry[c] = round(float(g[c].mean()), 4)
            entry[c + "_ci"] = [round(x, 4) for x in cluster_boot(g[c].values, g.cluster.values)]
        entry["heldout_best"] = round(float(g.heldout_best.mean()), 4)
        entry["heldout_best_ci"] = [round(x, 4) for x in cluster_boot(g.heldout_best.values, g.cluster.values)]
        summary["subsets"][s] = entry
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "surface.json").write_text(json.dumps(summary, indent=1))
    it.to_csv(RESULTS / "surface_items.csv", index=False)
    pd.set_option("display.width", 250)
    print(pd.DataFrame(summary["subsets"]).T[["n", "clusters", "chance", "longest", "shortest", "centroid", "cross_item", "heldout_best", "heldout_best_ci"]].to_string())
    fam = pd.DataFrame(summary["families"]).T
    print(fam[["n", "chance", "longest", "shortest", "centroid", "num_median", "num_center", "cross_item", "heldout_best", "null_heldout_95", "p_perm"]].to_string())


if __name__ == "__main__":
    main()
