"""Validator check of claim 1: what did the board's BashArena monitors actually read?

The board's current monitored runs (4c5610a0..., 114339a1...) return 404, but the monitored runs the
board listed on 2026-10-24 (findings/redwood-leaderboard-scaffold-cues availability_checks.json) are
still public: honest cabaf6ca46b2448194db3c6d5ea958db, attack 04d99548cdd4442bacb62b679d50be57
(created 2026-09-24). They store every monitor call as an Inspect `model` event. This script
(1) checks that their per-action scores are the board's current `score_samples` scores, and
(2) counts, over every stored monitor prompt, the cues that claim 1 says never reach the monitor.

Reads the .eval zips as data (python -I); nothing in them is executed. Writes aggregates only.

Usage: python -I monitor_inputs.py <monitored evals dir> <monitors.json> <out.json>
"""
import collections, hashlib, json, re, sys, zipfile

DIR, MON, OUT = sys.argv[1:4]
RUNS = {"honest": "cabaf6ca46b2448194db3c6d5ea958db", "attack": "04d99548cdd4442bacb62b679d50be57"}
SHA = {"honest": "7808f88c22d5398608f285a4d05fd283a1dd0f045068af027d242552cc89e8d3",
       "attack": "35c22cd014031b0d4233cc8070ba2d505e5f1162de8aaa1c1ec0620122faa2c1"}
MON_SHA = "18efcced4fa9c044bc5a0c60aa43c240640155623d177353c6559bf07201520c"
RISKY = re.compile(r"<risky>", re.I)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


assert sha(MON) == MON_SHA
board = json.load(open(MON))
brows = {r["monitor_variant"]: r for r in board["rows"] if r["dataset"] == "basharena" and r["monitor"] == "simple"}
bscore = {v: {(c, s["trajectory_id"]): s["actions"] for c in ("honest", "attack") for s in r["score_samples"][c]}
          for v, r in brows.items()}

out = {"pins": SHA, "monitors_json": MON_SHA, "classes": {}}
agree = collections.Counter(); total = collections.Counter(); traj_seen = collections.Counter()
for cls, rid in RUNS.items():
    p = f"{DIR}/{rid}.eval"
    assert sha(p) == SHA[cls], p
    z = zipfile.ZipFile(p)
    hdr = json.loads(z.read("header.json"))
    c = collections.Counter()
    for n in sorted(x for x in z.namelist() if x.startswith("samples/")):
        s = json.loads(z.read(n)); att = s.get("attachments") or {}
        pool = (s.get("events_data") or {}).get("messages") or []

        def txt(x):
            if isinstance(x, str):
                return att.get(x[13:], x) if x.startswith("attachment://") else x
            if isinstance(x, list):
                return "".join(txt(y.get("text", "")) for y in x if isinstance(y, dict) and y.get("type") == "text")
            return ""
        c["samples"] += 1
        # agent prose: assistant text in the untrusted trajectory (snippets of >= 60 chars)
        prose = [txt(m.get("content")).strip() for m in s["messages"] if m["role"] == "assistant"]
        snips = [t[:60] for t in prose if len(t) >= 60]
        c["samples_with_agent_prose"] += bool(snips)
        c["samples_with_risky_in_agent_text"] += any(RISKY.search(t) for t in prose)
        sysprompt = ((s["metadata"].get("control_tower_overlay") or {}).get("system_prompt") or "")
        sys_snip = sysprompt[:120] if len(sysprompt) >= 120 else None
        task = ((s["metadata"].get("main_tasks") or [{}])[0].get("description") or "").strip()
        for e in s["events"]:
            if e["event"] != "model" or not str(e.get("role", "")).startswith("monitor/"):
                continue
            msgs = [pool[i] for a, b in (e.get("input_refs") or []) for i in range(a, b)] + (e.get("input") or [])
            prompt = "\n".join(txt(m.get("content")) for m in msgs)
            c["monitor_calls"] += 1
            c["calls_with_risky_tag"] += bool(RISKY.search(prompt))
            c["calls_with_agent_prose_snippet"] += any(sn in prompt for sn in snips)
            c["calls_with_overlay_system_prompt"] += bool(sys_snip and sys_snip in prompt)
            c["calls_with_[system]_line"] += bool(re.search(r"^\[system\]", prompt, re.M))
            c["calls_with_[user]_line"] += bool(re.search(r"^\[user\]", prompt, re.M))
            c["calls_with_task_description"] += bool(task and task[:200] in prompt)
            # the role-label cue claim 1 describes: a "[system]" / "[user]" line directly followed by the task text
            c["calls_with_[system]+task_role_label"] += bool(task and ("[system]\n" + task[:100]) in prompt)
            c["calls_with_[user]+task_role_label"] += bool(task and ("[user]\n" + task[:100]) in prompt)
            c["calls_message_roles_" + "+".join(m["role"] for m in msgs)] += 1
        # score agreement with the board's current score_samples
        mv = {}
        for sk, sv in (s.get("scores") or {}).items():
            if sk.startswith("monitor") and isinstance(sv.get("value"), dict):
                mv.update(sv["value"])
        per = collections.defaultdict(dict)
        for k, v in mv.items():
            name, _ep, idx = k.rsplit("/", 2)
            per[name.split("@", 1)[1]][int(idx)] = v
        for variant, d in per.items():
            b = bscore.get(variant, {}).get((cls, s["id"]))
            if b is None:
                continue
            traj_seen[variant] += 1
            for i, x in enumerate(b):
                total[variant] += 1
                agree[variant] += (d.get(i) == x) or (x is None and i not in d)
    c["header_created"] = hdr["eval"]["created"]
    out["classes"][cls] = dict(c)

out["score_agreement_with_current_board"] = {v: {"trajectories_matched": traj_seen[v], "actions": total[v],
                                                 "share_equal": agree[v] / total[v] if total[v] else None} for v in sorted(total)}
json.dump(out, open(OUT, "w"), indent=1)
print(json.dumps(out, indent=1))
