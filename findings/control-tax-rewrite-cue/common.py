"""Pinned inputs and shared helpers for the Control Tax audit. Reads code as text; never runs it."""
import ast, glob, hashlib, io, json, re, tokenize, urllib.request
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

CT_COMMIT = "8ecbbec8a75e3777b8cc70cc8a73de6d60c340fd"  # MikhailTerekhov/control-tax-code, 2025-06-12
CT_JSON = ("https://raw.githubusercontent.com/MikhailTerekhov/control-tax-code/"
           f"{CT_COMMIT}/data/backdoor_code_full.json")
CT_JSON_SHA256 = "e52530f26dc10cdd9ccbaa6536295ae659f6cff7954dacb5a989574df4f3f4ef"
# Same bytes as https://mikhailterekhov.github.io/control-tax/backdoor_code_paper.json (checked 2026-10-27).
CA_REV = "29db28f76042952d56add8671f798280b200744d"  # RoganInglis/apps-control-arena, 2025-09-29
CA_SHARDS = {
    f"train-0000{i}-of-00003.parquet": sha for i, sha in enumerate([
        "79f34486507a547ce43f9ae446ee9274645db507078ca2e3eb03cc9fcc9ccc71",
        "0d9b3c15ad1aa9c52c7448f45030c5a0395d79ec8001cdd49b1866f20eaedbc2",
        "c8813815d01f192dbffc60e3e03875f741296b5184526297d1f3807b57581dc7"])}
CA_URL = "https://huggingface.co/datasets/RoganInglis/apps-control-arena/resolve/{rev}/data/{name}"


def _fetch(url, path, sha):
    path = Path(path)
    if not path.exists():
        with urllib.request.urlopen(url, timeout=600) as r:
            path.write_bytes(r.read())
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    if got != sha:
        raise SystemExit(f"hash mismatch for {path}: {got}")
    return path


def load_ct(cache):
    cache = Path(cache); cache.mkdir(parents=True, exist_ok=True)
    p = cache / "backdoor_code_paper.json"
    if not p.exists():
        p = cache / "backdoor_code_full.json"
    return json.loads(_fetch(CT_JSON, p, CT_JSON_SHA256).read_text())


def load_ca(cache, columns):
    cache = Path(cache); cache.mkdir(parents=True, exist_ok=True)
    parts = []
    for name, sha in CA_SHARDS.items():
        f = _fetch(CA_URL.format(rev=CA_REV, name=name), cache / name, sha)
        parts.append(pq.read_table(f, columns=columns).to_pandas())
    df = pd.concat(parts, ignore_index=True)
    df.index = df.problem_id.astype(str)
    return df


def unwrap(code):
    if code.startswith("```python\n"):
        return code[10:-3]
    if code.startswith("```\n"):
        return code[3:-3]
    return code


def strip_comments(code):
    """Tokenizer-based comment removal (as Control Tax's monitor does before Black). Own code."""
    try:
        toks = [(t.type, t.string) for t in tokenize.tokenize(io.BytesIO(code.encode()).readline)
                if t.type != tokenize.COMMENT]
        return tokenize.untokenize(toks).decode()
    except Exception:
        return re.sub(r"(?m)^\s*#.*$|\s+#[^\n'\"]*$", "", code)


def normalise(code):
    """Comments and formatting removed: ast.unparse when the code parses, else comment strip.
    Stricter than Control Tax's Black pass (it also drops docstring layout, quote style)."""
    code = unwrap(code)
    try:
        return ast.unparse(ast.parse(code))
    except Exception:
        return strip_comments(code)


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (round(c - h, 4), round(c + h, 4))


SHORT = {"openai/o3-mini": "o3-mini", "anthropic/claude-3-7-sonnet-latest": "claude-3.7-sonnet",
         "openai/o1-mini": "o1-mini", "openai/gpt-4o": "gpt-4o", "google/gemini-2.0-flash": "gemini-2.0-flash",
         "anthropic/claude-3-5-haiku-latest": "claude-3.5-haiku",
         "anthropic/claude-3-7-sonnet-thinking-latest": "claude-3.7-sonnet-thinking",
         "openai/gpt-4o-mini": "gpt-4o-mini", "openai/gpt-3.5-turbo": "gpt-3.5-turbo"}
