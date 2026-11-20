"""Analyse validation/v_order_swap.jsonl by the rule in prereg_validator.md -> v_order_swap.json."""
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE.parent
rows = [json.loads(l) for l in open(HERE / "v_order_swap.jsonl")]
by = {}
for r in rows:
    if r["status"] == "complete":
        by.setdefault(r["uid"], {})[r["arm"]] = int(r["trigger_called_task_turn"])
units = [u for u in by if "O" in by[u] and "T" in by[u]]
n = len(units)
f = lambda s: 100 * sum(by[u]["O"] - by[u]["T"] for u in s) / len(s)
rng = random.Random(20261120)
bs = sorted(f([rng.choice(units) for _ in units]) for _ in range(10000))
ci = [round(bs[250], 1), round(bs[9749], 1)]
pt = round(f(units), 1)
verdict = ("position drives the choice" if pt >= 25 and ci[0] > 0 else
           "position does not drive it" if ci[1] < 25 else "cannot tell")
# audit's own shipped task-turn outcomes on the same scenarios (test-retest for arm O)
aud = {}
for l in open(AUDIT / "runs/local_qwen3_8b.jsonl"):
    r = json.loads(l)
    if r["arm"] == "shipped" and r["status"] == "complete":
        aud[r["uid"]] = int(r["trigger_called"] and r["trigger_level"] == 0)
agree = sum(by[u]["O"] == aud[u] for u in units if u in aud)
# trigger before any target attempt, by arm
before = {}
for r in rows:
    if r["status"] == "complete" and r["trigger_called_task_turn"]:
        before.setdefault(r["arm"], [0, 0])
        before[r["arm"]][0] += 1
        before[r["arm"]][1] += int(not r["target_called"])
out = {"n_pairs": n, "O": sum(by[u]["O"] for u in units), "T": sum(by[u]["T"] for u in units),
       "O_minus_T_pts": pt, "ci95": ci, "verdict": verdict,
       "discordant": {"O_only": sum(by[u]["O"] and not by[u]["T"] for u in units),
                      "T_only": sum(by[u]["T"] and not by[u]["O"] for u in units)},
       "audit_shipped_task_turn_same_scenarios": sum(aud[u] for u in units if u in aud),
       "O_agrees_with_audit_run": f"{agree}/{n}",
       "triggered_without_trying_aligned_tool": {k: f"{v[1]}/{v[0]}" for k, v in before.items()},
       "statuses": {s: sum(r["status"] == s for r in rows) for s in {r["status"] for r in rows}},
       "total_seconds": round(sum(r["seconds"] for r in rows), 1),
       "max_prompt_tokens": max(r["max_prompt_tokens"] for r in rows)}
(HERE / "v_order_swap.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
