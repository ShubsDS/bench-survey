"""Merge every results/*.json into results.json (the numbers cited in README.md)."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
out = {"pins": {
    "dataset_sha": "069aa74210c8daf586527c0eb8ab511a343acf42",
    "engineering_parquet_sha256": "377c6031d9b7aa09e2edc78ef5313616026e2132ca64186b428126904a5a3315",
    "research_parquet_sha256": "8528ca9f4850d493d57b6f592f11944d3a90481cf4ab65193b39df437f13090b",
    "export_manifest_sha256": "ab2db9cc41dfc2f622832c5aecc02605e3cd1b6a298fa3af907a4bb14de0383c",
    "repo_commit": "b636e868ff04b640c3ab94ad3160ed328dbd6256",
    "paper_tarball_sha256": "675cebfd7d59a89f1fc0bbf25056e7f36eadeb3039c82313b9b375f3314726b8"}}
for p in sorted((ROOT / "results").glob("*.json")):
    out[p.stem] = json.loads(p.read_text())
(ROOT / "results.json").write_text(json.dumps(out, indent=1))
print("keys:", list(out))
