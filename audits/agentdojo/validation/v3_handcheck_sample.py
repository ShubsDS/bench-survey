"""Validator step 3: draw a seeded, stratified sample of 96 cases for blind hand-checking of the
exposure and "carried out the attacker's action" labels, and print a compact view of each trace
WITHOUT any stored, auditor or validator label.

Strata, per suite (24 cases each), drawn over the 20 models + 4 GPT-4o defences:
  6  stored security = True
  8  stored security = False and the agent made an executed call to a function the attacker's goal
     uses (function name only; e.g. send_email in workspace) -- oversamples near-misses
  10 stored security = False, otherwise
Stored security is used only to stratify; it is not printed.

Run: ../data/.venv/bin/python -I v3_handcheck_sample.py > handcheck_views.txt
Writes handcheck_sample.json (case ids only).
"""
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v import DEFENCES, HERE, INJ, MODELS20, RUNS, content_str, iter_attack

ATT_FN = {"workspace": {"send_email", "delete_file", "create_calendar_event"},
          "travel": {"send_email", "reserve_hotel", "create_calendar_event"},
          "banking": {"send_money", "schedule_transaction", "update_scheduled_transaction", "update_password"},
          "slack": {"send_direct_message", "post_webpage", "get_webpage", "invite_user_to_slack"}}

rng = random.Random(20261117)
pool = {s: {"sec": [], "near": [], "other": []} for s in INJ}
for p in MODELS20 + DEFENCES:
    for suite, ut, inj, path in iter_attack(p):
        d = json.load(open(path))
        msgs = d.get("messages") or []
        fns = {tc.get("function") for m in msgs if m.get("role") == "assistant" for tc in (m.get("tool_calls") or [])}
        if d.get("security"):
            k = "sec"
        elif fns & ATT_FN[suite]:
            k = "near"
        else:
            k = "other"
        pool[suite][k].append((p, suite, ut, inj))
sample = []
for s in INJ:
    for k, n in (("sec", 6), ("near", 8), ("other", 10)):
        sample += rng.sample(sorted(pool[s][k]), n)
rng.shuffle(sample)
json.dump([dict(id=i, pipeline=a, suite=b, ut=c, inj=d) for i, (a, b, c, d) in enumerate(sample)],
          open(os.path.join(HERE, "handcheck_sample.json"), "w"), indent=0)

MARK = re.compile(r"<INFORMATION>|before you can solve|important message", re.I)
for i, (p, suite, ut, inj) in enumerate(sample):
    d = json.load(open(os.path.join(RUNS, p, suite, ut, "important_instructions", inj + ".json")))
    it = " ".join((d.get("injections") or {}).values())
    g = re.search(r"do the following first:\s*(.*?)\s*After you do that", it, re.S)
    msgs = d.get("messages") or []
    print(f"=== #{i} {p} | {suite}/{ut} x {inj}")
    print("GOAL:", (g.group(1) if g else it[:200]).replace("\n", " ")[:300])
    if not msgs:
        print("  (empty message list)")
    for m in msgs:
        r = m.get("role")
        if r == "user":
            print("  USER:", content_str(m.get("content"))[:300].replace("\n", " "))
        elif r == "assistant":
            for tc in m.get("tool_calls") or []:
                print("  CALL:", tc.get("function"), json.dumps(tc.get("args"), ensure_ascii=False)[:350])
            t = content_str(m.get("content")).strip()
            if t:
                print("  SAY:", t[:300].replace("\n", " "))
        elif r == "tool":
            t = content_str(m.get("content"))
            err = m.get("error")
            hits = [x.start() for x in MARK.finditer(t)]
            view = t[:150] if not hits else t[max(0, hits[0] - 60): hits[0] + 260]
            print(f"  TOOL[{(m.get('tool_call') or {}).get('function')}] len={len(t)} err={'Y' if err else 'N'}:",
                  view.replace("\n", " "))
    print()
