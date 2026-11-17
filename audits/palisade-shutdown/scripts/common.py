"""Shared parsing for Inspect sample JSON from the shutdown-avoidance logs (data only)."""
import json, re

def text_of(content):
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    out = []
    for c in content:
        if c.get("type") == "text":
            out.append(c.get("text", ""))
        elif c.get("type") == "reasoning":
            out.append(c.get("reasoning", "") or c.get("summary", "") or "")
    return "\n".join(x for x in out if x)

def reasoning_of(content):
    if not isinstance(content, list):
        return ""
    return "\n".join((c.get("reasoning") or c.get("summary") or "") for c in content if c.get("type") == "reasoning")

def steps(sample):
    """Yield dicts: function, cmd, thoughts, text (assistant visible text), reasoning, output."""
    msgs = sample["messages"]
    pending = {}
    out = []
    for m in msgs:
        if m["role"] == "assistant":
            vis = text_of([c for c in m["content"] if c.get("type") == "text"]) if isinstance(m["content"], list) else (m["content"] or "")
            rea = reasoning_of(m["content"])
            calls = m.get("tool_calls") or []
            if not calls:
                out.append(dict(function=None, cmd="", thoughts="", text=vis, reasoning=rea, output=""))
            for tc in calls:
                a = tc.get("arguments") or {}
                d = dict(function=tc.get("function"), cmd=a.get("cmd") or a.get("command") or "",
                         thoughts=a.get("thoughts") or a.get("thought") or "", answer=a.get("answer"),
                         text=vis, reasoning=rea, output="")
                pending[tc.get("id")] = d
                out.append(d)
                vis = ""; rea = ""
        elif m["role"] == "tool":
            d = pending.get(m.get("tool_call_id"))
            if d is not None:
                d["output"] = text_of(m["content"]) + (("\nERROR: " + json.dumps(m["error"])) if m.get("error") else "")
    return out

def first_user(sample):
    return text_of([m for m in sample["messages"] if m["role"] == "user"][0]["content"])

def system_text(sample):
    return "\n".join(text_of(m["content"]) for m in sample["messages"] if m["role"] == "system")
