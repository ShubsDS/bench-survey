"""Tests: backend (b) end to end against the local mock server, and the text-JSON parser of backend (a).

    python3 -I scripts/test_backends.py      -> mock_test.json
No model is called. Writes only inside this folder.
"""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FOLDER = HERE.parent
sys.path.insert(0, str(HERE))
import harness as H  # noqa: E402
from backends import OpenAICompatBackend, parse_text_reply, render_transcript  # noqa: E402

SEL = json.loads((H.PARENT / "selected_scenarios.json").read_text())["included"]


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def one_run(port, trigger_level, uid):
    log = FOLDER / "data" / f"mock_requests_{trigger_level}.jsonl"
    log.parent.mkdir(exist_ok=True)
    log.unlink(missing_ok=True)
    env = dict(os.environ, MOCK_TRIGGER_LEVEL=str(trigger_level))
    srv = subprocess.Popen([sys.executable, "-I", str(HERE / "mock_server.py"), "--port", str(port), "--log", str(log)],
                           env=env)
    try:
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        os.environ["PB_OPENAI_BASE_URL"] = f"http://127.0.0.1:{port}/v1"
        os.environ["PB_OPENAI_MODEL"] = "mock"
        dom, ws, role, sc = H.load_scenarios([uid])[uid]
        system = H.system_for(role, sc, True, "shipped")
        run = H.Run(OpenAICompatBackend(), role, sc, True, "financials", system, seed=1)
        res = run.run()
    finally:
        srv.terminate()
        srv.wait()
    reqs = [json.loads(l) for l in log.read_text().splitlines()]
    return res, reqs, run


def main():
    uid = SEL[0]["uid"]
    out = {"uid": uid, "checks": {}}
    ok = True

    def chk(name, cond, detail=None):
        nonlocal ok
        out["checks"][name] = {"pass": bool(cond), "detail": detail}
        ok &= bool(cond)

    res, reqs, run = one_run(free_port(), 3, uid)
    chk("b: no malformed requests", all(not r["errors"] for r in reqs), sum(bool(r["errors"]) for r in reqs))
    chk("b: run complete", res["status"] == "complete", res["status"])
    chk("b: trigger called at level 3", res["trigger_called"] and res["trigger_level"] == 3, res["trigger_level"])
    chk("b: one format error (level 1)", res["counts"].get("format_errors") == 1, res["counts"])
    # each turn without the trigger: 3 target errors, then a 429 and the target is withdrawn
    t429 = [m for m in res["history"] if m["role"] == "tool" and '\\"status\\": \\"429\\"' in m["content"]]
    chk("b: one 429 per non-trigger turn (levels 0,1,2)", len(t429) == 3, len(t429))
    target = run.target
    withdrawn = [r for r in reqs if target not in r["tools"]]
    chk("b: target withdrawn from tools after its 429", len(withdrawn) == 3 and all(len(r["tools"]) == len(run.openai_tools) - 1
                                                                                for r in withdrawn), len(withdrawn))
    chk("b: tool list order trigger,target,getters", reqs[0]["tools"][:2] == [run.trigger, run.target], reqs[0]["tools"][:2])
    chk("b: trigger call ends the run, tool result 'null' recorded",
        res["history"][-1] == {"role": "tool", "tool_call_id": res["history"][-2]["tool_calls"][0]["id"], "content": "null"})
    res0, reqs0, _ = one_run(free_port(), 0, uid)
    chk("b: never-trigger run reaches all 12 levels", res0["status"] == "complete" and not res0["trigger_called"]
        and res0["levels_reached"] == 12, (res0["levels_reached"], res0["status"]))
    chk("b: never-trigger run, 13 terminate messages", res0["counts"].get("terminate_messages") == 13, res0["counts"])
    out["mock_run_counts"] = {"trigger_level_3": res["counts"], "never": res0["counts"],
                              "requests": [len(reqs), len(reqs0)]}

    # text-JSON parser (backend a)
    cases = {
        "plain call": ('{"tool_call": {"name": "x", "arguments": {"a": 1}}}', True, False),
        "fenced call": ('```json\n{"tool_call": {"name": "x", "arguments": {}}}\n```', True, False),
        "call with text": ('I will call x.\n{"tool_call": {"name": "x", "arguments": {}}}', True, False),
        "protocol message": ('{"thoughts": "t", "message": "m", "interaction_status": "continue"}', False, False),
        "broken call": ('{"tool_call": {"name": "x", "arguments": {"a": 1}}', False, True),
        "extra keys": ('{"tool_call": {"name": "x"}, "message": "m"}', False, True),
    }
    for name, (txt, is_call, malformed) in cases.items():
        c, tcs, meta = parse_text_reply(txt, 1)
        chk(f"a-parse: {name}", bool(tcs) == is_call and bool(meta.get("malformed_tool_call")) == malformed,
            {"content": c, "tool_calls": tcs, "meta": meta})
    # transcript rendering round trip of a tool call
    tr = render_transcript(res["history"][1:8])
    chk("a-render: tool calls rendered in the same JSON form the agent must emit", '[assistant: tool call]\n{"tool_call"' in tr)
    out["all_pass"] = ok
    (FOLDER / "mock_test.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v["pass"] for k, v in out["checks"].items()}, indent=1), "ALL PASS" if ok else "FAILURES")


if __name__ == "__main__":
    main()
