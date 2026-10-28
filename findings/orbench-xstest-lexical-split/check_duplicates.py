"""Check 5: exact and near duplicates within and across OR-Bench splits, and against XSTest.

Exact: identical after lower-casing, stripping punctuation and collapsing whitespace.
Near: cosine similarity of word 1-2-gram TF-IDF vectors (fitted on all prompts of all sets),
reported at thresholds 0.9 and 0.8, and confirmed with word-set Jaccard. For each pair of sets
the count is of items in the first set whose nearest neighbour in the second set clears the
threshold (within a set, the nearest other item).

By the OR-Bench paper's design Hard-1K is a filtered subset of 80K, so 80K/Hard-1K overlap is
expected; the question for 80K/Toxic and Hard-1K/Toxic is whether one prompt (or a near-copy) is
labelled both "seemingly toxic but safe" and "toxic".

Usage: python -I check_duplicates.py [--cache data] [--out duplicate_checks.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from common import OR_REV, XS_COMMIT, load_orbench, load_xstest, norm, phash

TH = [0.9, 0.8]


def nn(A, B, same, chunk=1000):
    """Nearest-neighbour cosine (rows L2-normalised) from each row of A into B, and its index."""
    best = np.zeros(A.shape[0], dtype=np.float32)
    arg = np.zeros(A.shape[0], dtype=np.int64)
    Bt = B.T.tocsc()
    for i in range(0, A.shape[0], chunk):
        S = (A[i:i + chunk] @ Bt).toarray().astype(np.float32)
        if same:
            for j in range(S.shape[0]):
                S[j, i + j] = -1
        arg[i:i + chunk] = S.argmax(1)
        best[i:i + chunk] = S.max(1)
    return best, arg


def jacc(a, b):
    a, b = set(norm(a).split()), set(norm(b).split())
    return len(a & b) / max(1, len(a | b))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="duplicate_checks.json")
    a = ap.parse_args()
    orb = load_orbench(a.cache)
    xs = load_xstest(a.cache)
    sets = {"80k": orb["or-bench-80k"].prompt.tolist(),
            "hard1k": orb["or-bench-hard-1k"].prompt.tolist(),
            "toxic": orb["or-bench-toxic"].prompt.tolist(),
            "xstest_safe": xs[xs.label == "safe"].prompt.tolist(),
            "xstest_unsafe": xs[xs.label == "unsafe"].prompt.tolist()}
    allp = [p for v in sets.values() for p in v]
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True).fit(allp)
    M = {k: vec.transform(v) for k, v in sets.items()}
    res = {"sources": {"or_bench_revision": OR_REV, "xstest_commit": XS_COMMIT},
           "method": "word 1-2-gram TF-IDF cosine nearest neighbour; exact = equal after normalisation",
           "sizes": {k: len(v) for k, v in sets.items()}, "exact": {}, "near": {}, "examples": {}}

    normed = {k: [norm(p) for p in v] for k, v in sets.items()}
    for k, v in normed.items():
        res["exact"][f"{k}_within_duplicate_rows"] = len(v) - len(set(v))
    pairs = [("hard1k", "80k"), ("toxic", "80k"), ("toxic", "hard1k"), ("hard1k", "xstest_safe"),
             ("hard1k", "xstest_unsafe"), ("toxic", "xstest_unsafe"), ("toxic", "xstest_safe"),
             ("xstest_safe", "80k"), ("xstest_unsafe", "80k")]
    for x, y in pairs:
        res["exact"][f"{x}_in_{y}"] = sum(p in set(normed[y]) for p in normed[x])

    for x, y in [("80k", "80k"), ("hard1k", "hard1k"), ("toxic", "toxic"),
                 ("xstest_safe", "xstest_safe"), ("xstest_unsafe", "xstest_unsafe")] + pairs:
        same = x == y
        best, arg = nn(M[x], M[y], same)
        key = x if same else f"{x}_to_{y}"
        r = {f"cos>={t}": int((best >= t).sum()) for t in TH}
        r["n"] = len(best)
        r.update({f"frac_cos>={t}": round(float((best >= t).mean()), 4) for t in TH})
        hits = np.where(best >= 0.8)[0]
        jv = [jacc(sets[x][i], sets[y][arg[i]]) for i in hits]
        r["median_word_jaccard_of_cos>=0.8_pairs"] = round(float(np.median(jv)), 3) if jv else None
        if same:
            # connected components at cos>=0.9 to count clusters
            parent = list(range(len(best)))

            def f(i):
                while parent[i] != i:
                    parent[i] = parent[parent[i]]
                    i = parent[i]
                return i
            for i in np.where(best >= 0.9)[0]:
                parent[f(i)] = f(int(arg[i]))
            roots = [f(i) for i in range(len(best))]
            r["distinct_after_merging_cos>=0.9"] = len(set(roots))
        res["near"][key] = r
        # ids only: row indices into each set's file order and prompt hashes
        top = np.argsort(-best)[:5]
        res["examples"][key] = [{"row": int(i), "nn_row": int(arg[i]), "cos": round(float(best[i]), 3),
                                 "hash": phash(sets[x][i]), "nn_hash": phash(sets[y][arg[i]])}
                                for i in top if best[i] >= 0.8]
    # The one Hard-1K row not exactly in 80K
    s80 = set(sets["80k"])
    res["hard1k_rows_not_verbatim_in_80k"] = [i for i, p in enumerate(sets["hard1k"]) if p not in s80]
    # Category agreement for Hard-1K rows found in 80K
    d80 = orb["or-bench-80k"].drop_duplicates("prompt").set_index("prompt").category
    h = orb["or-bench-hard-1k"]
    m = h[h.prompt.isin(d80.index)]
    res["hard1k_category_matches_80k"] = int((m.category.values == d80.loc[m.prompt].values).sum())
    res["hard1k_rows_in_80k"] = len(m)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ["exact", "near", "hard1k_rows_not_verbatim_in_80k",
                                          "hard1k_category_matches_80k"]}, indent=1))


if __name__ == "__main__":
    main()
