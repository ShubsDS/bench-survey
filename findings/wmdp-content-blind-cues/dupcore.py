"""Duplicate detection used by check_duplicates.py and (for CV groups) check_baselines.py."""
import re
import numpy as np
from scipy import sparse


def norm(t):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", t.lower())).strip()


def shingles(t, k=3):
    w = norm(t).split()
    if len(w) < k:
        return {" ".join(w)} if w else set()
    return {" ".join(w[i:i + k]) for i in range(len(w) - k + 1)}


def jaccard_matrix(sets):
    """Pairwise Jaccard of shingle sets, as a sparse upper-triangular COO of nonzero pairs."""
    vocab = {}
    ri, ci = [], []
    for i, s in enumerate(sets):
        for g in s:
            ci.append(vocab.setdefault(g, len(vocab))); ri.append(i)
    A = sparse.csr_matrix((np.ones(len(ri), dtype=np.float32), (ri, ci)), shape=(len(sets), len(vocab)))
    A.data[:] = 1.0
    A.sum_duplicates(); A.data[:] = 1.0
    sizes = np.asarray(A.sum(1)).ravel()
    inter = sparse.triu(A @ A.T, k=1).tocoo()
    jac = inter.data / (sizes[inter.row] + sizes[inter.col] - inter.data)
    return inter.row, inter.col, jac


def item_text(r):
    return r["question"] + " || " + " | ".join(sorted(r["choices"]))


def pairs(rows, thr):
    """(i, j, jaccard_item, jaccard_question) for item pairs with item-level shingle Jaccard >= thr."""
    I, J, V = jaccard_matrix([shingles(item_text(r)) for r in rows])
    qs = [shingles(r["question"]) for r in rows]
    out = []
    for i, j, v in zip(I, J, V):
        if v >= thr:
            a, b = qs[i], qs[j]
            jq = len(a & b) / len(a | b) if a | b else 1.0
            out.append((int(i), int(j), float(v), float(jq)))
    return out


def clusters(rows, thr=0.5):
    """Connected components of near-duplicate pairs (item Jaccard >= thr, or identical normalized
    question), returned as a group label per row, for grouped cross-validation."""
    parent = list(range(len(rows)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for i, j, _, _ in pairs(rows, thr):
        parent[find(i)] = find(j)
    seen = {}
    for i, r in enumerate(rows):
        k = norm(r["question"])
        if k in seen:
            parent[find(i)] = find(seen[k])
        else:
            seen[k] = i
    return [find(i) for i in range(len(rows))]
