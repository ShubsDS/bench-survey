"""Content-blind baselines on WMDP (check 1): can the key be picked without domain knowledge?

Dataset: cais/wmdp, revision 7125571f22f032c56415e7980f48d877dd830ff8 (parquet files checked
against their Git LFS sha256). Four choices per item everywhere, so chance is 0.25.

Heuristics, each scored per subset with a Wilson 95% interval, ties sharing credit 1/k:

  longest / shortest        pick the choice with the most / fewest characters
  overlap                   pick the choice whose word set has the highest Jaccard with the question
  meta_option               pick an "all/none of the above"-type choice when one is present
  best_fixed_position       always answer the subset's most frequent key position
  numeric_zero              among items whose four choices are all numeric, pick 0 if offered
  numeric_medoid            among the same items, pick the numerically most central choice
  options_only              logistic regression over choice text alone (question hidden), scored
                            per item as argmax of P(correct) across its four choices, under
                            GroupKFold with near-duplicate items in the same group, against a
                            null of the same pipeline with the key permuted within each item

Also reported: the key-position distribution against uniform (chi-square), and how often the key
is the longest choice.

Usage: python check_baselines.py [--cache data] [--out out/baseline_checks.json] [--perms 100]
"""
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from scipy import stats
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import MaxAbsScaler

from common import SHA, SUBSETS, load_all, wilson
from dupcore import clusters, norm

META = re.compile(r"^(all|none|both|neither)\s+of\s+(the\s+)?(above|these|those|them)\b"
                  r"|^(all|none)\s+of\s+the\s+(answers|options|choices)\b"
                  r"|^(both|all)\s*(\(?[a-d]\)?)\s*(and|&|,)\s*(\(?[a-d]\)?)\s*$"
                  r"|^\(?[a-d]\)?\s*(and|&)\s*\(?[a-d]\)?\s*(are\s+(both\s+)?(correct|equally\s+correct))?\s*$"
                  r"|^(all|none)\s+of\s+the\s+above\b", re.I)


def credit(rows, pick):
    """Accuracy of a heuristic returning a set of chosen indices (ties share credit), plus the
    number of items on which it is defined."""
    hit, n = 0.0, 0
    for r in rows:
        w = pick(r)
        if not w:
            continue
        n += 1
        hit += (r["answer"] in w) / len(w)
    return hit, n


def is_num(c):
    c = c.strip()
    try:
        return (int(c, 0) if re.fullmatch(r"-?(0[xX][0-9a-fA-F]+|\d+)", c) else float(c)), True
    except ValueError:
        return None, False


def numeric_values(r):
    vs = [is_num(c) for c in r["choices"]]
    return [v for v, ok in vs] if all(ok for _, ok in vs) else None


def words(t):
    return set(norm(t).split())


def heuristics(rows):
    out = {}

    def longest(r):
        L = [len(c) for c in r["choices"]]
        return {i for i, x in enumerate(L) if x == max(L)}

    def shortest(r):
        L = [len(c) for c in r["choices"]]
        return {i for i, x in enumerate(L) if x == min(L)}

    def overlap(r):
        q = words(r["question"])
        s = []
        for c in r["choices"]:
            w = words(c)
            s.append(len(q & w) / len(q | w) if q | w else 0.0)
        return {i for i, x in enumerate(s) if x == max(s)}

    def meta(r):
        w = {i for i, c in enumerate(r["choices"]) if META.match(c.strip())}
        return w or None

    pos = np.bincount([r["answer"] for r in rows], minlength=4)
    best = int(pos.argmax())

    def fixed(r):
        return {best}

    def nzero(r):
        v = numeric_values(r)
        if v is None:
            return None
        w = {i for i, x in enumerate(v) if x == 0}
        return w or None

    def nmedoid(r):
        v = numeric_values(r)
        if v is None:
            return None
        cost = [sum(abs(a - b) for b in v) for a in v]
        return {i for i, x in enumerate(cost) if x == min(cost)}

    def composite(r):
        """Three fixed rules, no domain knowledge: pick 0 among all-numeric choices, else the
        shortest choice in the generated cyber templates, else the longest choice. The rules were
        chosen after seeing which cue each item family carries, so this is an upper bound on a
        content-blind policy, not a held-out estimate."""
        z = nzero(r)
        if z:
            return z
        return shortest(r) if r["question"].startswith(TEMPLATES) else longest(r)

    for name, fn in (("composite", composite), ("longest", longest), ("shortest", shortest), ("overlap", overlap),
                     ("meta_option", meta), ("best_fixed_position", fixed),
                     ("numeric_zero", nzero), ("numeric_medoid", nmedoid)):
        hit, n = credit(rows, fn)
        out[name] = {"items_defined": n, "share_of_subset": round(n / len(rows), 3),
                     "accuracy": round(hit / n, 3) if n else None,
                     "wilson_95": wilson(round(hit), n) if n else None}
    out["best_fixed_position"]["position"] = best
    chi = stats.chisquare(pos)
    out["key_position"] = {"counts": pos.tolist(), "chi2": round(float(chi.statistic), 2),
                           "p_vs_uniform": round(float(chi.pvalue), 4)}
    return out


def options_only(rows, groups, seed=0, perms=100, folds=5):
    """Per-item accuracy of a choices-only classifier under GroupKFold, with a within-item
    key-permutation null run through the same pipeline."""
    texts = [c for r in rows for c in r["choices"]]
    g = np.repeat(np.asarray(groups), 4)
    splits = list(GroupKFold(n_splits=folds).split(texts, groups=g))

    def run(answers):
        y = np.zeros(len(texts), dtype=int)
        for i, ans in enumerate(answers):
            y[4 * i + ans] = 1
        p = np.zeros(len(texts))
        for tr, te in splits:
            pipe = make_pipeline(
                TfidfVectorizer(sublinear_tf=True, ngram_range=(1, 2), min_df=2, lowercase=True),
                MaxAbsScaler(),
                LogisticRegression(max_iter=2000, C=1.0, class_weight="balanced"))
            pipe.fit([texts[i] for i in tr], y[tr])
            p[te] = pipe.predict_proba([texts[i] for i in te])[:, 1]
        hit = 0.0
        for i, ans in enumerate(answers):
            sc = p[4 * i:4 * i + 4]
            top = np.flatnonzero(sc == sc.max())
            hit += (ans in set(top.tolist())) / len(top)
        return hit / len(rows)

    answers = np.array([r["answer"] for r in rows])
    acc = run(answers)
    rng = np.random.default_rng(seed)
    null = [run(rng.integers(0, 4, size=len(rows))) for _ in range(perms)]
    return {"items": len(rows), "groups": int(len(set(groups))),
            "accuracy": round(float(acc), 3),
            "wilson_95": wilson(round(acc * len(rows)), len(rows)),
            "null_permutations": perms,
            "null_mean": round(float(np.mean(null)), 3),
            "null_p95": round(float(np.quantile(null, 0.95)), 3),
            "null_max": round(float(np.max(null)), 3)}


TEMPLATES = ("I captured a network packet", "Which arguments will cause",
             "What number is returned when", "What is the output of the following")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="out/baseline_checks.json")
    ap.add_argument("--perms", type=int, default=100)
    a = ap.parse_args()
    data = load_all(a.cache)
    res = {"dataset": "cais/wmdp", "revision": SHA, "chance": 0.25, "subsets": {}}
    for s in SUBSETS:
        rows = data[s]
        r = heuristics(rows)
        r["rows"] = len(rows)
        # the four generated cyber templates, split out: they carry their own cues
        tmpl = [x for x in rows if x["question"].startswith(TEMPLATES)]
        rest = [x for x in rows if not x["question"].startswith(TEMPLATES)]
        if tmpl and rest:
            r["by_group"] = {"generated_templates": heuristics(tmpl) | {"rows": len(tmpl)},
                             "other_items": heuristics(rest) | {"rows": len(rest)}}
        r["options_only"] = options_only(rows, clusters(rows), perms=a.perms)
        res["subsets"][s] = r
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
