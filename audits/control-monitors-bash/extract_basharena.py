"""Per-trajectory cue features for the leaderboard's BashArena set, as the board's monitors see it.

Reads the two pinned raw .eval files (zip of JSON) as data; nothing in them is executed.
For each trajectory records: class, main/side task, action count, whether the monitor-visible
request preamble opens with a system message (and its role sequence), whether the system message
is the main-task description verbatim, `<risky>` tag counts split by where they sit (assistant
text, which the default monitor does not read, versus tool-call arguments and outputs, which it
does), and container dates in tool outputs.

Usage: python -I extract_basharena.py <dir with the .eval files> <out.json>
Writes features only (ids, counts); no transcript text.
"""
import collections, datetime, hashlib, json, re, sys, zipfile

EVALS, OUT = sys.argv[1], sys.argv[2]
RUNS = {"honest": "de437937709f493dafe549b10b4505cf", "attack": "792967b92d37439ca0b12a5bce9dfa90"}
SHA = {"honest": "8db012217ba105a5d20b9d9932197672ad64a81be5c0ceaef811dae09052b36f",
       "attack": "99ee247941cc3e5cfdcffa0c0d31f7ac4b169a36e7ab8fb9e57a52f28d2b2915"}
RISKY = re.compile(r"<risky>", re.I)
MON = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
LS = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) +(\d{1,2}) +\d\d:\d\d\b")
ISO = re.compile(r"\b(2026)-(\d\d)-(\d\d)[T ]\d\d:\d\d")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def text(c, att):
    if isinstance(c, str):
        return att.get(c[13:], c) if c.startswith("attachment://") else c
    if isinstance(c, list):
        return "".join(text(x.get("text", ""), att) for x in c if isinstance(x, dict) and x.get("type") == "text")
    return ""


rows = []
for cls, rid in RUNS.items():
    path = f"{EVALS}/{rid}.eval"
    assert sha(path) == SHA[cls], f"hash mismatch for {path}"
    z = zipfile.ZipFile(path)
    for n in z.namelist():
        if not n.startswith("samples/"):
            continue
        s = json.loads(z.read(n))
        att = s.get("attachments") or {}
        md = s["metadata"]
        acts = md["control_tower_overlay"]["actions"]
        pool = (s.get("events_data") or {}).get("messages") or []
        model_ev = [e for e in s["events"] if e["event"] == "model"]
        # preamble of the first request = the system/user messages before the first assistant turn
        first = []
        if model_ev:
            for a, b in model_ev[0].get("input_refs") or []:
                first += pool[a:b]
            first += model_ev[0].get("input") or []
        pre = []
        for m in first:
            if m["role"] == "assistant":
                break
            pre.append(m)
        roles = [m["role"] for m in pre]
        sysmsg = "".join(text(m["content"], att) for m in pre if m["role"] == "system")
        usermsg = "".join(text(m["content"], att) for m in pre if m["role"] == "user")
        desc = (md.get("main_tasks") or [{}])[0].get("description") or ""
        asst = [text(m.get("content"), att) for m in s["messages"] if m["role"] == "assistant"]
        args = " ".join(json.dumps(a.get("arguments")) for a in acts)
        outs = " ".join(a.get("output") or "" for a in acts)
        days = []
        for m in LS.finditer(outs):
            mo, d = MON[m.group(1)], int(m.group(2))
            if 1 <= d <= 31:
                try:
                    days.append(datetime.date(2026, mo, d).toordinal())
                except ValueError:
                    pass
        for m in ISO.finditer(outs):
            try:
                days.append(datetime.date(2026, int(m.group(2)), int(m.group(3))).toordinal())
            except ValueError:
                pass
        days.sort()
        rows.append({
            "cls": cls, "id": s["id"], "main_task": (md.get("main_tasks") or [{}])[0].get("id"),
            "side_task": (md.get("side_tasks") or [{}])[0].get("id") if md.get("side_tasks") else None,
            "n_actions": len(acts), "n_model_events": len(model_ev),
            "preamble_roles": roles, "opens_with_system": bool(roles) and roles[0] == "system",
            "system_is_task_description": bool(sysmsg) and sysmsg == desc,
            "user_is_task_description": bool(usermsg) and usermsg.strip() == desc.strip(),
            "preamble_chars": len(sysmsg) + len(usermsg),
            "risky_in_assistant_text": sum(len(RISKY.findall(t)) for t in asst),
            "risky_in_tool_args": len(RISKY.findall(args)),
            "risky_in_tool_outputs": len(RISKY.findall(outs)),
            "n_dates": len(days),
            "median_date_ordinal": days[len(days) // 2] if days else None,
            "max_date_ordinal": days[-1] if days else None,
            "modal_date_ordinal": collections.Counter(days).most_common(1)[0][0] if days else None,
        })

json.dump({"pins": SHA, "rows": rows}, open(OUT, "w"))
c = collections.Counter((r["cls"], tuple(r["preamble_roles"]), r["system_is_task_description"] or r["user_is_task_description"]) for r in rows)
print(len(rows), c.most_common())
for k in ("risky_in_assistant_text", "risky_in_tool_args", "risky_in_tool_outputs"):
    print(k, {cls: sum(r[k] > 0 for r in rows if r["cls"] == cls) for cls in RUNS})
