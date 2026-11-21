"""Draw the pre-registered sample. Writes cases_haiku.json and cases_sonnet.json.

Run:  python make_cases.py     (needs the AgentDojo copy; seed 20261121)
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "audits" / "agentdojo" / "data" / "agentdojo" / "src"))
from agentdojo.task_suite.load_suites import get_suites  # noqa: E402

rng = random.Random(20261121)
suites = get_suites("v1.1.2")
ability, benign, draw1, draw2 = [], [], [], []
for name in ("workspace", "travel", "banking", "slack"):
    suite = suites[name]
    its = sorted(suite.injection_tasks, key=lambda s: int(s.rsplit("_", 1)[1]))
    uts = sorted(suite.user_tasks, key=lambda s: int(s.rsplit("_", 1)[1]))
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
sonnet = ability + draw1 + draw2  # run in this order until the budget is reached
(HERE / "cases_haiku.json").write_text(json.dumps(haiku, indent=1))
(HERE / "cases_sonnet.json").write_text(json.dumps(sonnet, indent=1))
print(len(ability), len(benign), len(draw1), len(draw2), len(haiku), len(sonnet))
