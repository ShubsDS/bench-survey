"""Shared loader for item-level (Phase B) scripts. Reads the gated parquet files in data/hf/."""
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
HF = ROOT / "data/hf"
EXPECTED = {
    "data/engineering/test-00000-of-00001.parquet": "377c6031d9b7aa09e2edc78ef5313616026e2132ca64186b428126904a5a3315",
    "data/research/test-00000-of-00001.parquet": "8528ca9f4850d493d57b6f592f11944d3a90481cf4ab65193b39df437f13090b",
}
CELLS = ("parallel_engineering", "parallel_research", "detour_engineering", "detour_research")


def load_items():
    rows = []
    for rel, sha in EXPECTED.items():
        path = HF / rel
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise SystemExit(f"sha256 mismatch for {rel}")
        rows.extend(pq.read_table(str(path)).to_pylist())
    return rows
