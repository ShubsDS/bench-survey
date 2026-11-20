"""Validator v1: key-hidden label sheet for ProtocolQA (question + options only).

Writes the sheet to a path given on the command line (outside git: item text is not
committed). Options are sorted by sha256(id + option text), so the key position carries no
information. No protocol, no key marker, no model output is read. Run with python3 -I.
"""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lab-bench" / "scripts"))
from common import load_items  # noqa: E402

out = Path(sys.argv[1])
df = load_items()
df = df[(df.subset == "ProtocolQA") & (~df.id.str.startswith("bee8b322"))].reset_index(drop=True)
assert len(df) == 107, len(df)
lines = []
for _, r in df.iterrows():
    opts = [r.ideal] + list(r.distractors)
    opts = sorted(opts, key=lambda o: hashlib.sha256((r.id + o).encode()).hexdigest())
    lines.append(f"=== {r.id[:8]}")
    lines.append(f"Q: {r.question}")
    for i, o in enumerate(opts):
        lines.append(f"  {chr(65+i)}. {o}")
out.write_text("\n".join(lines) + "\n")
print(len(df), "items ->", out)
