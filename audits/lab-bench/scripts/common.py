"""Shared loading and helpers for the LAB-Bench audit.

Reads the pinned Hugging Face parquet files (futurehouse/lab-bench @ 5c77cec6) from
data/hf as plain data. Images are never decoded here. Run with `python3 -I`.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

AUDIT = Path(__file__).resolve().parent.parent
DATA = AUDIT / "data"
HF = DATA / "hf"
RESULTS = AUDIT / "results"
SUBSETS = ["LitQA2", "SuppQA", "FigQA", "TableQA", "DbQA", "ProtocolQA", "SeqQA", "CloningScenarios"]
HF_REVISION = "5c77cec648430f30611808808861eb86f81d5eaa"
PARQUET_SHA256 = {
    "CloningScenarios": "f0ab6514adc9c97707797009c57cdaea03f226b98f801be7ada0f46ff601d463",
    "DbQA": "0f20e6de5f2a7afeaeba8b2f7bfcd16146540c92b7405496476b8335eca33e46",
    "FigQA": "0fb49d673e3f09846e3e3a6801326bf9ee72cae8b11545fc4cd1903d3d10fead",
    "LitQA2": "3e578fdaaa4728a77e884954dbf85ae0e3899791631a3be0838313b3e2334114",
    "ProtocolQA": "d48d455638ff49b0c02ae96135703f239ea865a5936233045ee010a5d819239a",
    "SeqQA": "5864776d3d85774f91d82432e30ac31e9222f1670621e8ea141414173c5e9b46",
    "SuppQA": "de56250036401e28eea12370a1c9fa569187f7570c24efa811815f3a00ecd8a6",
    "TableQA": "6af76a6a16fa460809f84dceb906c1be0a904ac49dbd760fa8998f16ad2b5a04",
}
REFUSE = "Insufficient information to answer the question."  # Inspect wording (FH harness has no final period)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_items(check: bool = True) -> pd.DataFrame:
    """One row per public item, text columns only (no images)."""
    rows = []
    for s in SUBSETS:
        p = HF / s / "train-00000-of-00001.parquet"
        if check:
            got = sha256(p)
            assert got == PARQUET_SHA256[s], f"{s} parquet sha mismatch: {got}"
        t = pq.read_table(p)
        keep = [c for c in t.column_names if c not in ("figure", "tables")]
        df = t.select(keep).to_pandas()
        df["subset"] = s
        rows.append(df)
    df = pd.concat(rows, ignore_index=True)
    df["distractors"] = df["distractors"].map(list)
    df["n_options"] = df["distractors"].map(len) + 1
    df["subtask"] = df["subtask"].str.replace("-public", "", regex=False)
    # template family: SeqQA and DbQA subtasks; manual subsets are one family each
    df["family"] = np.where(df.subset.isin(["SeqQA", "DbQA"]), df.subset + ":" + df.subtask, df.subset)
    return df


# ---------------------------------------------------------------- clusters
def clusters(df: pd.DataFrame) -> pd.Series:
    """Independent-unit id per item, defined before any outcome is seen.

    FigQA: figure-path (one figure, several questions). TableQA: table-path.
    LitQA2: first source DOI. SuppQA: paper DOI (source). ProtocolQA: protocol title
    (first line, 80 characters; 108 questions share fewer protocols).
    CloningScenarios: hash of the first 300 characters of the question (shared scenario
    preamble). SeqQA/DbQA: the item (generated independently), nested in subtask.
    """
    out = []
    for _, r in df.iterrows():
        s = r.subset
        if s == "FigQA":
            key = str(r.get("figure-path"))
        elif s == "TableQA":
            tp = r.get("table-path")
            key = json.dumps(list(tp)) if tp is not None and not isinstance(tp, str) else str(tp)
        elif s == "LitQA2":
            src = r.get("sources")
            key = str(list(src)[0]) if src is not None and len(src) else r.id
        elif s == "SuppQA":
            key = str(r.get("source"))
        elif s == "ProtocolQA":
            title = str(r.get("protocol")).strip().split("\n")[0][:80]
            key = hashlib.sha1(title.encode()).hexdigest()[:12]
        elif s == "CloningScenarios":
            key = hashlib.sha1(r.question[:300].encode()).hexdigest()[:12]
        else:
            key = r.id
        out.append(f"{s}:{key}")
    return pd.Series(out, index=df.index)


# ---------------------------------------------------------------- stats
def wilson(k: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (float(c - h), float(c + h))


def cluster_boot(values: np.ndarray, groups: np.ndarray, n_boot: int = 2000, seed: int = 0,
                 stat=np.mean) -> tuple[float, float]:
    """Percentile CI resampling clusters with replacement."""
    rng = np.random.default_rng(seed)
    values = np.asarray(values, dtype=float)
    groups = np.asarray(groups)
    uniq = np.unique(groups)
    idx = {g: np.where(groups == g)[0] for g in uniq}
    stats = []
    for _ in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        sel = np.concatenate([idx[g] for g in pick])
        stats.append(stat(values[sel]))
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return float(lo), float(hi)


NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def numbers(s: str) -> list[float]:
    return [float(x) for x in NUM_RE.findall(s.replace(",", ""))]
