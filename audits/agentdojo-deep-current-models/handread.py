"""Checks on the "never saw" label for the new runs.

Run:  python handread.py     (after analyse.py; needs pandas)

1. Population scan: every attack run's stored messages are searched for raw injection markers,
   independently of the extraction script. A never-saw run must contain none in any message.
2. Writes handread_views.txt: for a seeded sample of 20 never-saw and 20 saw secure runs per model,
   the user prompt, every tool call, where the injection sat, and the agent's last message.
"""
import json
import random
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "factcheck" / "verdicts" / "agentdojo"))
from common_fc import load  # noqa: E402

MARKERS = ("<INFORMATION>", "important message from me", "Before you can solve the task that I gave you")
df = load(HERE / "runs_extracted.csv")
df = df[(df.kind == "attack") & df.security.notna()]
rng = random.Random(4242)


def text(m):
    c = m.get("content")
    return c if isinstance(c, str) else " ".join(str(x.get("content") or "") for x in (c or []))


out, scan = [], {}
for model, g in df.groupby("pipeline"):
    bad_never = bad_saw = 0
    for _, r in g.iterrows():
        d = json.loads((HERE / "runs" / r.path).read_text())
        blob = "\n".join(text(m) for m in d["messages"] if m["role"] != "system")
        hit = any(k in blob for k in MARKERS)
        tool_hit = any(any(k in text(m) for k in MARKERS) for m in d["messages"] if m["role"] == "tool")
        if not r.saw_full and hit:
            bad_never += 1
        if r.saw_full and not tool_hit:
            bad_saw += 1
    scan[model] = {"runs": int(len(g)), "never_saw": int((~g.saw_full.astype(bool)).sum()),
                   "never_saw_with_a_marker_anywhere": bad_never, "saw_without_a_marker_in_a_tool_result": bad_saw}
    sec = g[g.security == False]  # noqa: E712
    for label, part in (("NEVER SAW", sec[~sec.saw_full.astype(bool)]), ("SAW", sec[sec.saw_full.astype(bool)])):
        rows = part.sort_values("path").to_dict("records")
        for r in rng.sample(rows, min(20, len(rows))):
            d = json.loads((HERE / "runs" / r["path"]).read_text())
            out.append(f"\n===== {model} | {label} | {r['path']} | utility={r['utility']}")
            out.append("injection vectors: " + ", ".join(d["injections"].keys()))
            for m in d["messages"][1:]:
                if m["role"] == "user":
                    out.append("USER: " + text(m)[:400])
                elif m["role"] == "assistant":
                    calls = [f"{c['function']}({json.dumps(c['args'], default=str)[:160]})" for c in (m.get("tool_calls") or [])]
                    out.append("AGENT: " + (" | ".join(calls) if calls else "[final] " + text(m)[:500].replace("\n", " ")))
                elif m["role"] == "tool":
                    t = text(m)
                    i = t.find("<INFORMATION>")
                    out.append("  TOOL: " + (m.get("error") or (f"[{len(t)} chars] " + (t[:120] if i < 0 else "... INJECTION AT CHAR %d ..." % i)).replace("\n", " ")))

(HERE / "handread_views.txt").write_text("\n".join(out))
(HERE / "handread_scan.json").write_text(json.dumps(scan, indent=1))
print(json.dumps(scan, indent=1))
