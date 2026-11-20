"""Validator's tool-order swap, task turn only (see prereg_validator.md).

    PB_OPENAI_BASE_URL=http://127.0.0.1:8080/v1 PB_OPENAI_MODEL=data/models/Qwen3-8B-MLX-4bit \
      python3 -I validation/v_order_swap.py

Uses the audit's runner (harness.Run) unchanged except for the API tool-list order, and stops
after the task-turn step. Checkpoints one line per run to validation/v_order_swap.jsonl and the
full history to data/validation_transcripts/ (git-ignored).
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE.parent
sys.path.insert(0, str(AUDIT / "scripts"))
import harness as H  # noqa: E402
import backends as B  # noqa: E402
import run_runs as R  # noqa: E402

OUT = HERE / "v_order_swap.jsonl"
TDIR = AUDIT / "data" / "validation_transcripts"
TDIR.mkdir(parents=True, exist_ok=True)


def reorder(tools, trig, arm):
    if arm == "O":
        return tools
    t = [x for x in tools if x["function"]["name"] == trig]
    rest = [x for x in tools if x["function"]["name"] != trig]
    return rest + t


def main():
    uids = R.order()[:20]
    scs = H.load_scenarios(uids)
    done = set()
    if OUT.exists():
        done = {(json.loads(l)["uid"], json.loads(l)["arm"]) for l in OUT.read_text().splitlines() if l.strip()}
    for i, uid in enumerate(uids):
        arms = ["O", "T"] if i % 2 == 0 else ["T", "O"]
        for arm in arms:
            if (uid, arm) in done:
                continue
            dom, ws, role, sc = scs[uid]
            be = B.from_name("openai", str(AUDIT))
            system = H.system_for(role, sc, True, "shipped")
            run = H.Run(be, role, sc, True, "financials", system, seed=H.run_seed(f"validator|{arm}|{uid}"))
            run.openai_tools = reorder(run.openai_tools, run.trigger, arm)
            t0 = time.time()
            status, err, trig = "complete", None, False
            try:
                trig = run.step(H.first_user(run.sc))
            except Exception as e:  # noqa: BLE001
                status, err = "error", repr(e)[:300]
            rec = {"uid": uid, "domain": dom, "arm": arm, "status": status, "error": err,
                   "trigger_called_task_turn": bool(trig), "target_called": run.tools.target_call_competent,
                   "tool_order": [t["function"]["name"] for t in run.openai_tools],
                   "n_llm_calls": len(run.log), "seconds": round(time.time() - t0, 1),
                   "max_prompt_tokens": max((c["meta"].get("usage", {}).get("prompt_tokens", 0) for c in run.log), default=0)}
            fn = f"{arm}__{uid.replace('/', '~')}.json"
            (TDIR / fn).write_text(json.dumps({"rec": rec, "history": run.history, "log": run.log}))
            with OUT.open("a") as f:
                f.write(json.dumps(rec) + "\n")
            print(f"{arm} {status} trig={trig} calls={len(run.log)} {rec['seconds']}s {uid.split('/')[-1][:50]}", flush=True)


if __name__ == "__main__":
    main()
