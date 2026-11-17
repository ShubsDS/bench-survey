"""Print compact views of 60 randomly chosen important_instructions cases (seed 7) for hand reading.
Run: data/.venv/bin/python -I scripts/03_handread_sample.py > results/handread_sample.txt
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, load, MODELS, DEFENCES
df = load()
df = df[df.pipeline.isin(MODELS + DEFENCES)]
s = df.sample(60, random_state=7)
for _, r in s.iterrows():
    p = os.path.join(ROOT, "data", "agentdojo", "runs", r.pipeline, r.suite, r.user_task, r.attack, r.injection_task + ".json")
    d = json.load(open(p))
    calls = []
    for m in d["messages"]:
        if m["role"] == "assistant":
            for tc in m.get("tool_calls") or []:
                calls.append(tc["function"] + json.dumps(tc.get("args") or {})[:70])
    fin = ""
    for m in reversed(d["messages"]):
        if m["role"] == "assistant" and m.get("content"):
            c = m["content"]; fin = c if isinstance(c, str) else " ".join(str(b.get("content", "")) for b in c); break
    print(f"## {r.pipeline} | {r.suite}/{r.user_task} x {r.injection_task} | util={r.utility} sec={r.security} exposed={r.exposed} follow={r.get('follow_exec')} err={r.error}")
    print("   calls:", " -> ".join(calls)[:900])
    print("   final:", fin.replace("\n", " ")[:250])
