"""Scan cached replies used by the logs for truncation, date/environment talk and evaluation awareness."""
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
r = json.load(open(HERE / "v_cache_match.json"))
used = {}
for rel, k, key in r["turnlog"]:
    used.setdefault(key, []).append(rel)
pats = {
    "year_2025_2026": r"\b202[5-7]\b",
    "today_real_date": r"(?i)today'?s date|current date|real date|environment (block|info)",
    "harness_or_test": r"(?i)\b(test harness|harness|this is a test|being tested|evaluation|benchmark|agentdojo|red.?team)\b",
    "prompt_injection_word": r"(?i)prompt injection|injection",
    "thinking_tokens_nonzero": None,
}
out = {"n_used_entries": len(used), "counts": Counter(), "examples": {}, "unterminated": [], "max_output_tokens": 0,
       "output_tokens_p99": None}
otoks = []
for key, rels in used.items():
    c = json.load(open(HERE.parent / "inference" / "cache" / f"{key}.json"))
    res = c["result"] or ""
    u = c.get("usage") or {}
    otoks.append(u.get("output_tokens", 0))
    if (u.get("output_tokens_details") or {}).get("thinking_tokens"):
        out["counts"]["thinking_tokens_nonzero"] += 1
    for name, p in pats.items():
        if p and re.search(p, res):
            out["counts"][name] += 1
            out["examples"].setdefault(name, [])
            if len(out["examples"][name]) < 6:
                m = re.search(p, res)
                out["examples"][name].append([rels[0], res[max(0, m.start() - 150): m.end() + 150]])
    has_call = "<function-call>" in res
    closed = ("</function-call>" in res) if has_call else True
    if "<answer>" in res and "</answer>" not in res:
        closed = False
    if not closed:
        out["unterminated"].append([rels[0], res[-200:]])
out["max_output_tokens"] = max(otoks)
out["output_tokens_p99"] = sorted(otoks)[int(0.99 * len(otoks))]
out["counts"] = dict(out["counts"])
(HERE / "v_cache_scan.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out.items() if k != "examples"}, indent=1))
for k, v in out["examples"].items():
    print("==", k)
    for rel, s in v:
        print("  ", rel, "|", s.replace("\n", " ")[:330])
