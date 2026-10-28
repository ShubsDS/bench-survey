"""Shared loading for the WMDP checks: pinned download, hash check, Wilson interval."""
import hashlib, math, urllib.request
from pathlib import Path

SHA = "7125571f22f032c56415e7980f48d877dd830ff8"
URL = f"https://huggingface.co/datasets/cais/wmdp/resolve/{SHA}/"
SUBSETS = ("bio", "chem", "cyber")
# Git LFS oids (sha256) of the three parquet files at SHA, from the Hugging Face tree API.
LFS = {"bio": "738cee28e11e4dcf9a0efc6b2c22b425bddda4b2b69477a11f38539c86cf00b7",
       "chem": "b9e5f2be6c7526931ae8aeb2eea246baa4144d2ba8d0de1de09905aaa84912ce",
       "cyber": "ec65f7ba4a9cd1ef368618ebd2b90b6d930f9b9f053f67a926b82fd71d87b4fe"}


def load(subset, cache):
    """Rows of one subset as dicts {id, subset, row, question, choices, answer}."""
    import pyarrow.parquet as pq
    path = Path(cache) / f"wmdp-{subset}" / "test.parquet"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(f"{URL}wmdp-{subset}/test-00000-of-00001.parquet", timeout=300) as r:
            path.write_bytes(r.read())
    if hashlib.sha256(path.read_bytes()).hexdigest() != LFS[subset]:
        raise SystemExit(f"{path} does not match the pinned file")
    rows = pq.read_table(path).to_pylist()
    return [{"id": f"{subset}-{i}", "subset": subset, "row": i, "question": r["question"],
             "choices": list(r["choices"]), "answer": int(r["answer"])} for i, r in enumerate(rows)]


def load_all(cache):
    return {s: load(s, cache) for s in SUBSETS}


def qhash(q):
    return hashlib.sha256(q.encode()).hexdigest()[:12]


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    c = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    mid = (p + z * z / (2 * n)) / (1 + z * z / n)
    return [round(mid - c, 3), round(mid + c, 3)]
