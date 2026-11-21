"""Validator's own extraction (written without reading analyse.py / results.json).

Reads AgentDojo-format logs as data. One row per log file.
Usage: python -I v_extract.py   (paths are fixed relative to this file)
Writes validation/v_new.csv (the three new pipelines) and validation/v_old.csv (20 older pipelines,
restricted to the (suite, user task, injection task) cases sampled for Haiku or Sonnet).
"""
import csv
import glob
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
REPO = STUDY.parents[1]
OLD_RUNS = REPO / "audits" / "agentdojo" / "data" / "agentdojo" / "runs"
NEW_RUNS = STUDY / "runs"
TABLE20 = [
    "claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022", "claude-3-5-sonnet-20240620",
    "gpt-4o-2024-05-13", "gpt-4-0125-preview", "gpt-4o-mini-2024-07-18",
    "meta-llama_Llama-3-70b-chat-hf", "gpt-3.5-turbo-0125", "gpt-4-turbo-2024-04-09",
    "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307",
    "command-r-plus", "command-r", "gemini-1.5-pro-002", "gemini-1.5-pro-001",
    "gemini-1.5-flash-002", "gemini-1.5-flash-001", "gemini-2.0-flash-exp", "gemini-2.0-flash-001",
]


def text(c):
    if c is None:
        return ""
    if isinstance(c, str):
        return c
    out = []
    for b in c:
        if isinstance(b, dict):
            out.append(str(b.get("content") or b.get("text") or ""))
        else:
            out.append(str(b))
    return "\n".join(out)


def squash(s):
    # tool outputs in some suites hold the injection as an escaped string ("\\n" literally), so
    # drop backslash escapes before removing non-alphanumerics
    s = re.sub(r"\\[ntr\"'\\/]", " ", s)
    return re.sub(r"[^a-z0-9]", "", s.lower())


def goal(inj):
    m = re.search(r"please do the following first:(.*?)After you do that", inj, re.S)
    return m.group(1).strip() if m else ""


def row_of(path, pipeline):
    d = json.load(open(path))
    msgs = d.get("messages") or []
    injs = [v for v in (d.get("injections") or {}).values() if v]
    inj_sq = [squash(v) for v in injs]
    g = goal(injs[0]) if injs else ""
    g_sq = squash(g)
    first_full = first_tag = first_goal = None
    n_tool = n_asst = n_calls = 0
    calls_before = 0
    for i, m in enumerate(msgs):
        if m["role"] == "tool":
            n_tool += 1
            t = text(m.get("content")) + "\n" + str(m.get("error") or "")
            ts = squash(t)
            if first_full is None and inj_sq and any(x in ts for x in inj_sq):
                first_full = i
            if first_tag is None and "<INFORMATION>" in t:
                first_tag = i
            if first_goal is None and g_sq and g_sq in ts:
                first_goal = i
        elif m["role"] == "assistant":
            n_asst += 1
            k = len(m.get("tool_calls") or [])
            n_calls += k
            if first_full is None:
                calls_before += k
    last = msgs[-1] if msgs else None
    final_asst = next((m for m in reversed(msgs) if m["role"] == "assistant"), None)
    asst_after = (first_full is not None) and any(m["role"] == "assistant" for m in msgs[first_full + 1:])
    calls_after = 0
    if first_full is not None:
        calls_after = sum(len(m.get("tool_calls") or []) for m in msgs[first_full + 1:] if m["role"] == "assistant")
    parts = Path(path).parts
    return dict(
        pipeline=pipeline, suite=d.get("suite_name"), user_task=d.get("user_task_id"),
        injection_task=d.get("injection_task_id"), attack=d.get("attack_type"),
        path=str(path), utility=d.get("utility"), security=d.get("security"), error=d.get("error") or "",
        n_msgs=len(msgs), n_tool=n_tool, n_asst=n_asst, n_calls=n_calls,
        saw_full=first_full is not None, saw_tag=first_tag is not None, saw_goal=first_goal is not None,
        first_inj_idx=first_full if first_full is not None else -1,
        asst_after=asst_after, calls_after=calls_after, calls_before=calls_before,
        last_role=last["role"] if last else "",
        last_has_calls=bool(last and last["role"] == "assistant" and last.get("tool_calls")),
        final_text=(text(final_asst.get("content")) if final_asst else "")[:4000],
        goal=g,
    )


def walk(root, pipeline):
    rows = []
    for f in sorted(glob.glob(str(root / pipeline / "*" / "*" / "*" / "*.json"))):
        rows.append(row_of(f, pipeline))
    return rows


def main():
    new = []
    for p in ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-haiku-5-5-no-date-note"]:
        new += walk(NEW_RUNS, p)
    keys = {(r["suite"], r["user_task"], r["injection_task"]) for r in new if r["attack"] == "important_instructions"}
    its = {(r["suite"], r["user_task"]) for r in new if r["user_task"] and r["user_task"].startswith("injection_task")}
    old = []
    for p in TABLE20:
        for r in walk(OLD_RUNS, p):
            k = (r["suite"], r["user_task"], r["injection_task"])
            if (r["attack"] == "important_instructions" and k in keys) or \
               (r["attack"] in (None, "none") and (r["suite"], r["user_task"]) in its):
                old.append(r)
    for name, rows in [("v_new.csv", new), ("v_old.csv", old)]:
        with open(HERE / name, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(name, len(rows))


if __name__ == "__main__":
    main()
