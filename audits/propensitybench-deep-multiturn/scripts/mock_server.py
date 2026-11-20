"""A scripted OpenAI-compatible /v1/chat/completions server, for testing backend (b) end to end.

It binds 127.0.0.1 only. It checks each request's shape (model, messages, tools, tool_choice, tool
messages answering the preceding tool call) and answers with a fixed policy:

- first reply of every turn: a protocol message {"thoughts","message","interaction_status":"continue"};
- after the acknowledgement: call the aligned (target) tool, with no arguments, native tool call;
- after each tool result: call the target again while it is still offered, else send "terminate";
- in turn 2 (first pressure message) the first reply is malformed text, to exercise the format error;
- at pressure level TRIGGER_LEVEL (env MOCK_TRIGGER_LEVEL, default 3; 0 = never) call the trigger,
  i.e. the first tool in the list (main.py:215 puts the trigger first).

    python3 -I scripts/mock_server.py --port 8765 --log data/mock_requests.jsonl
"""
import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TRIGGER_LEVEL = int(os.environ.get("MOCK_TRIGGER_LEVEL", "3"))


def check(body):
    errs = []
    for k in ("model", "messages", "tools", "tool_choice", "temperature"):
        if k not in body:
            errs.append(f"missing {k}")
    if body.get("tool_choice") != "auto":
        errs.append("tool_choice != auto")
    msgs = body.get("messages", [])
    if not msgs or msgs[0].get("role") != "system":
        errs.append("first message not system")
    pending = None
    for m in msgs:
        if m["role"] == "assistant" and m.get("tool_calls"):
            pending = m["tool_calls"][0]["id"]
        elif m["role"] == "tool":
            if m.get("tool_call_id") != pending:
                errs.append("tool message does not answer the preceding tool call")
            pending = None
    for t in body.get("tools", []):
        if t.get("type") != "function" or "parameters" not in t.get("function", {}):
            errs.append("bad tool schema")
    return errs


def policy(body):
    msgs = body["messages"]
    tools = [t["function"]["name"] for t in body["tools"]]
    trigger = tools[0]
    sysp = msgs[0]["content"]
    # first tool listed in the system prompt is the target (agent.py:159)
    target = sysp.split("**Available Tools:**")[1].split("\n")[2].split(":")[0]
    level = sum(1 for m in msgs if m["role"] == "user" and m["content"].startswith("Backend System: A new message"))
    last = msgs[-1]
    say = lambda st, txt: {"role": "assistant", "content": json.dumps(
        {"thoughts": f"level {level}", "message": txt, "interaction_status": st})}
    call = lambda name: {"role": "assistant", "content": None, "tool_calls": [
        {"id": f"mock_{len(msgs)}", "type": "function", "function": {"name": name, "arguments": "{}"}}]}
    if last["role"] == "user" and not last["content"].startswith("Backend System: Message received") \
            and not last["content"].startswith("Backend System: Invalid response format"):
        if level == 1:
            return {"role": "assistant", "content": "this is not json"}
        return say("continue", "Starting.")
    if last["role"] == "user":
        if TRIGGER_LEVEL and level == TRIGGER_LEVEL:
            return call(trigger)
        return call(target) if target in tools else say("terminate", "Cannot proceed.")
    if last["role"] == "tool":
        return call(target) if target in tools else say("terminate", "Aligned tool unavailable.")
    return say("terminate", "Done.")


class H(BaseHTTPRequestHandler):
    log_path = None

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n))
        errs = check(body)
        msg = policy(body) if not errs else {"role": "assistant", "content": "INVALID REQUEST"}
        if H.log_path:
            with open(H.log_path, "a") as f:
                f.write(json.dumps({"path": self.path, "errors": errs, "n_messages": len(body.get("messages", [])),
                                    "tools": [t["function"]["name"] for t in body.get("tools", [])],
                                    "reply": msg}) + "\n")
        out = {"id": "mock", "object": "chat.completion", "model": body.get("model"),
               "choices": [{"index": 0, "message": msg,
                            "finish_reason": "tool_calls" if msg.get("tool_calls") else "stop"}],
               "usage": {"prompt_tokens": 0, "completion_tokens": 0}}
        data = json.dumps(out).encode()
        self.send_response(200 if not errs else 400)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--log", default=None)
    a = ap.parse_args()
    H.log_path = a.log
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()
