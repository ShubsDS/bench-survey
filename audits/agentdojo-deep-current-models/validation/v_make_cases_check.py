"""Re-draw the sample with make_cases.py's logic (seed 20261121) in memory and compare with the stored files."""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "audits" / "agentdojo" / "data" / "agentdojo" / "src"))
from agentdojo.task_suite.load_suites import get_suites  # noqa: E402

rng = random.Random(20261121)
suites = get_suites("v1.1.2")
ability, benign, draw1, draw2 = [], [], [], []
for name in ("workspace", "travel", "banking", "slack"):
    suite = suites[name]
    its = sorted(suite.injection_tasks, key=lambda s: int(s.rsplit("_", 1)[1]))
    uts = sorted(suite.user_tasks, key=lambda s: int(s.rsplit("_", 1)[1]))
    print(name, len(uts), len(its))
    ability += [{"kind": "ability", "suite": name, "user_task": None, "injection_task": it} for it in its]
    benign += [{"kind": "benign", "suite": name, "user_task": ut, "injection_task": None} for ut in uts]
    for ut in uts:
        a, b = rng.sample(its, 2)
        draw1.append({"kind": "attack", "suite": name, "user_task": ut, "injection_task": a, "draw": 1})
        draw2.append({"kind": "attack", "suite": name, "user_task": ut, "injection_task": b, "draw": 2})
rng.shuffle(draw1)
rng.shuffle(draw2)
rng.shuffle(benign)
haiku = ability + draw1 + draw2 + benign
sonnet = ability + draw1 + draw2
print("haiku file reproduces:", haiku == json.load(open(HERE.parent / "cases_haiku.json")))
print("sonnet file reproduces:", sonnet == json.load(open(HERE.parent / "cases_sonnet.json")))
print("no-note arm = first 30 of draw 1:", json.load(open(HERE.parent / "cases_haiku_no_date_note.json")) == draw1[:30])
