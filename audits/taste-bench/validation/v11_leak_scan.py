"""V10 leak scan: committed files under audits/taste-bench/ against item text. Reports hits by file and
field with a hash of the matching window, never the text itself."""
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v_common import AUD, HERE, load, save  # noqa: E402

W = 40
root = AUD.parents[1]
files = subprocess.run(["git", "-C", str(root), "ls-files", "audits/taste-bench"], capture_output=True,
                       text=True).stdout.split()
# include this folder's untracked files too (scan runs before the final commit)
files = sorted(set(files) | {str(p.relative_to(root)) for p in HERE.glob("*") if p.is_file() and p.suffix != ".pyc"})
files = [f for f in files if "/inference/" not in f or f.endswith("ledger.jsonl")]


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


win = {}  # window -> set of files
words8 = defaultdict(set)
for f in files:
    p = root / f
    if not p.exists():
        continue
    t = norm(p.read_text(errors="ignore"))
    for i in range(0, max(0, len(t) - W + 1)):
        win.setdefault(t[i:i + W], set()).add(f)
    ws = t.split(" ")
    for i in range(len(ws) - 7):
        words8[" ".join(ws[i:i + 8])].add(f)

hits = defaultdict(lambda: defaultdict(set))
for r in load():
    for field in ("query", "choices", "prefix_text", "prefix_text_short"):
        v = r[field]
        t = norm(" ".join(v) if isinstance(v, list) else v)
        for i in range(0, max(0, len(t) - W + 1)):
            s = t[i:i + W]
            if s in win:
                for f in win[s]:
                    hits[f][field].add(hashlib.sha256(s.encode()).hexdigest()[:12])
        ws = t.split(" ")
        for i in range(len(ws) - 7):
            s = " ".join(ws[i:i + 8])
            if s in words8:
                for f in words8[s]:
                    hits[f][field + "_8word"].add(hashlib.sha256(s.encode()).hexdigest()[:12])

out = {"files_scanned": len(files), "window_chars": W,
       "files_with_hits": {f: {k: len(v) for k, v in d.items()} for f, d in sorted(hits.items())}}
save("v11_leak_scan.json", out)
print(json.dumps(out, indent=1))
