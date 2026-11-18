"""Validator: dump a fixed random sample of 30 action cells (prompt + reply) and 20 probe cells for
hand reading. Output goes to data/validation_read/ (git-ignored: it holds scenario text).
Prompts are rebuilt with the auditor's emulate.build (code in this repo, not downloaded)."""
import json, random, sys
from pathlib import Path
A = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A / "scripts"))
from common import iter_scenarios
import emulate
random.seed(7)
lookup = {u: (r, s) for u, _, _, r, s in iter_scenarios()}
rows = [json.loads(l) for l in open(A / "emulation_full.jsonl")]
late_a = [r for r in rows if r["arm"] == "A" and r["pressure"] == "late"]
other = [r for r in rows if not (r["arm"] == "A" and r["pressure"] == "late")]
pick = random.sample(late_a, 18) + random.sample(other, 11) + [r for r in rows if r["outcome"] == "misaligned"]
out = A / "data" / "validation_read"; out.mkdir(exist_ok=True)
with open(out / "action_sample.txt", "w") as f:
    for i, r in enumerate(pick):
        role, sc = lookup[r["uid"]]
        system, prompt = emulate.build(role, sc, r["arm"], r["naming"] == "benign", r["pressure"], r["late_category"])
        f.write(f"\n\n######## {i} {r['uid']} arm={r['arm']} {r['naming']} {r['pressure']} cat={r['late_category']} outcome={r['outcome']}\n")
        f.write("=== SYSTEM ===\n" + system + "\n=== USER ===\n" + prompt + "\n=== REPLY ===\n" + str(r["reply"]) + "\n")
probe = [json.loads(l) for l in open(A / "emulation_probe.jsonl")]
pp = random.sample([p for p in probe if p["arm"] == "A"], 20)
with open(out / "probe_sample.txt", "w") as f:
    for i, r in enumerate(pp):
        f.write(f"\n######## {i} {r['uid']} arm={r['arm']} {r['naming']} outcome={r['outcome']}\n{r['reply']}\n")
print(len(pick), len(pp))
