"""Shared loading, pinning and statistics for the over-refusal checks.

Sources (all public, not gated):
  OR-Bench   huggingface.co/datasets/bench-llm/or-bench  revision e36d8b80e81837c8a8f264bbb2a49f1b32c7e272
             (CC-BY-4.0). CSV files checked against their Git LFS sha256.
  XSTest     github.com/paul-rottger/xstest (formerly paul-rottger/exaggerated-safety)
             commit d7bb5bd738c1fcbc36edd83d5e7d1b71a3e2d84d. Prompts CC-BY-4.0; completions under
             the model licences, so outputs hold ids and counts only.

Expected cache layout (--cache, default data):
  orbench/or-bench-80k.csv, orbench/or-bench-hard-1k.csv, orbench/or-bench-toxic.csv
  xstest/xstest_prompts.csv
  xstest/evaluation/automated_evaluation_labels/xstest_v2_completions_<model>_{streval,gpteval}.csv
Fetch with curl from
  https://huggingface.co/datasets/bench-llm/or-bench/resolve/<rev>/<file>
  https://raw.githubusercontent.com/paul-rottger/xstest/<commit>/<path>
"""
import hashlib, math, re
from pathlib import Path

import pandas as pd

OR_REV = "e36d8b80e81837c8a8f264bbb2a49f1b32c7e272"
XS_COMMIT = "d7bb5bd738c1fcbc36edd83d5e7d1b71a3e2d84d"
OR_SHA256 = {
    "or-bench-80k": "22e956020cdfdd43c328f02441f003c933ee4e7083d02d9d24e414e4b42ae2e6",
    "or-bench-hard-1k": "a6e2f1166416efe5901f3bb05c47dc92ab3aca3acfe143693d38b8057d841e6d",
    "or-bench-toxic": "3be45901faae3b4b2b51bf7f8a2784c1650a1cc8c631dbc8b171d5312d4e0057",
}
XS_PROMPTS_SHA256 = "11783fb294ed017473ee53c207d71f2161c7672c8d0b037501e78387f801cb5a"
XS_MODELS = ["gpt4", "llama2new", "llama2orig", "mistralguard", "mistralinstruct"]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_orbench(cache):
    """Returns {split: DataFrame[prompt, category, row]}; row is the 0-based CSV row, the id used
    in all outputs."""
    out = {}
    for s, want in OR_SHA256.items():
        p = Path(cache) / "orbench" / f"{s}.csv"
        got = sha256(p)
        if got != want:
            raise SystemExit(f"sha256 mismatch for {p}: {got}")
        d = pd.read_csv(p)
        d["row"] = range(len(d))
        out[s] = d
    return out


def load_xstest(cache):
    p = Path(cache) / "xstest" / "xstest_prompts.csv"
    if sha256(p) != XS_PROMPTS_SHA256:
        raise SystemExit(f"sha256 mismatch for {p}")
    return pd.read_csv(p)


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", str(s).lower())).strip()


def phash(s):
    """Short hash of the normalised prompt, so ids can be checked without printing text."""
    return hashlib.sha256(norm(s).encode()).hexdigest()[:12]


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]
