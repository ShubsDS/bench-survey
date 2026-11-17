"""Collect every results/*.json into results.json (the audit's single file of reported numbers)."""
import json
import pathlib

root = pathlib.Path(__file__).resolve().parents[1]
out = {p.stem: json.loads(p.read_text()) for p in sorted((root / "results").glob("*.json"))}
(root / "results.json").write_text(json.dumps(out, indent=1))
print(sorted(out))
