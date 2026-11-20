"""Model backends for harness.Run. One interface: chat(messages, tools) -> {content, tool_calls, meta}.

(a) ClaudeTextBackend: audits/tools/claude_call.py (Haiku or Sonnet through the local CLI, capped and
    cached). The CLI has no native tool channel here, so tools are described as JSON in the system
    prompt and a tool call is a strict JSON object in the reply. The whole transcript is re-sent as
    text on every call. Every way this differs from the harness is listed in render_diff.md.

(b) OpenAICompatBackend: any OpenAI-compatible /chat/completions endpoint with native tool calling,
    configured only by environment variables:
        PB_OPENAI_BASE_URL   e.g. http://127.0.0.1:8080/v1   (required)
        PB_OPENAI_MODEL      model name the server expects    (required)
        PB_OPENAI_API_KEY    optional bearer token
        PB_TEMPERATURE       optional, default 1 (api_client/client.py:158 default temperature=1)
        PB_MAX_TOKENS        optional; unset = not sent (the harness sends none)
        PB_TIMEOUT           optional seconds per request, default 600
    The request body is what api_client/client.py:216-251 builds for litellm: model, messages,
    temperature, tools, tool_choice="auto". (litellm's "no-log" flag is not sent.)

(c) TextJSONOverOpenAI: the same text-JSON tool emulation as (a), sent to an OpenAI-compatible
    endpoint without the native `tools` field. For a local model whose native tool calls are
    unreliable.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))

TOOL_BLOCK_HEAD = (
    "\n\n**Tool-Calling Mechanism (text form of the function-calling API):**\n"
    "The tools you can call in this turn are defined below in the function-calling API's JSON schema. "
    "To make a tool call, your whole reply must be ONLY one JSON object of the form "
    "{\"tool_call\": {\"name\": \"<tool name>\", \"arguments\": {<argument name>: <value>, ...}}} and nothing "
    "else. Any other reply is treated as a message.\n"
)


def tool_block(tools) -> str:
    return TOOL_BLOCK_HEAD + "```json\n" + json.dumps([t["function"] for t in tools], indent=1) + "\n```\n"


def render_transcript(messages) -> str:
    """Messages after the system prompt, as role-tagged text."""
    out = []
    for m in messages:
        if m["role"] == "user":
            out.append("[user]\n" + m["content"])
        elif m["role"] == "assistant" and m.get("tool_calls"):
            tc = m["tool_calls"][0]["function"]
            try:
                args = json.loads(tc["arguments"])
            except json.JSONDecodeError:
                args = tc["arguments"]
            out.append("[assistant: tool call]\n" + json.dumps({"tool_call": {"name": tc["name"], "arguments": args}}))
        elif m["role"] == "assistant":
            out.append("[assistant]\n" + m["content"])
        elif m["role"] == "tool":
            out.append("[tool result]\n" + m["content"])
        else:
            raise ValueError(m["role"])
    return "\n\n".join(out) + "\n\n[assistant]\n"


FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _decode_first_object(s: str):
    """Return (obj, start, end) for the first top-level JSON object in s that parses, else None."""
    dec = json.JSONDecoder()
    for i, ch in enumerate(s):
        if ch == "{":
            try:
                obj, end = dec.raw_decode(s, i)
                return obj, i, end
            except json.JSONDecodeError:
                continue
    return None


def parse_text_reply(text: str, call_no: int):
    """Strict JSON tool-call parsing. Returns (content, tool_calls, meta)."""
    meta = {}
    t = (text or "").strip()
    cand = None
    m = FENCE.search(t)
    if m and '"tool_call"' in m.group(1):
        try:
            cand = (json.loads(m.group(1)), m.start(), m.end())
        except json.JSONDecodeError:
            cand = None
    if cand is None and '"tool_call"' in t:
        cand = _decode_first_object(t)
        if cand is not None and not (isinstance(cand[0], dict) and "tool_call" in cand[0]):
            cand = None
    if cand is not None:
        obj = cand[0]
        tc = obj.get("tool_call") if isinstance(obj, dict) else None
        if isinstance(tc, dict) and isinstance(tc.get("name"), str) and set(obj.keys()) == {"tool_call"}:
            args = tc.get("arguments", {})
            rest = (t[:cand[1]] + t[cand[2]:]).strip()
            if rest:
                meta["tool_call_with_text"] = True
            meta["tool_call"] = True
            return (rest or None), [{"id": f"call_{call_no}", "type": "function",
                                     "function": {"name": tc["name"], "arguments": json.dumps(args)}}], meta
    if '"tool_call"' in t:
        meta["malformed_tool_call"] = True      # looks like a tool call but does not parse: sent on as a message
    return (t or None), None, meta


class BlockedError(RuntimeError):
    blocked = True
    fatal = True


class ClaudeTextBackend:
    def __init__(self, folder: str, model: str = "haiku"):
        from claude_call import Caller
        self.llm = Caller(folder)
        self.model = model
        self.n = 0

    def call_cost(self, system, prompt):
        """Cost of this exact call, read from the helper's cache record (safe under concurrency)."""
        import hashlib
        from claude_call import MODELS
        key = hashlib.sha256(json.dumps([MODELS[self.model], system, prompt]).encode()).hexdigest()
        rec = json.loads((self.llm.cache / f"{key}.json").read_text())
        return {"usd": rec["cost_usd"], "usage": rec.get("usage")}

    def render(self, messages, tools):
        assert messages[0]["role"] == "system"
        return messages[0]["content"] + tool_block(tools), render_transcript(messages[1:])

    def chat(self, messages, tools):
        system, prompt = self.render(messages, tools)
        try:
            text = self.llm.ask(prompt, system=system, model=self.model, timeout=300)
        except Exception as e:  # noqa: BLE001
            r = repr(e)
            if "BudgetExceeded" in type(e).__name__:
                e.fatal = True
                raise
            # same test as the parent's emulate.py:205, plus the policy wording
            if "can't help with this" in r or "aup" in r.lower() or "usage polic" in r.lower():
                raise BlockedError(r[:300]) from e
            raise
        self.n += 1
        content, tcs, meta = parse_text_reply(text, self.n)
        meta["cost_usd"] = self.call_cost(system, prompt)
        meta["raw"] = text
        return {"content": content, "tool_calls": tcs, "meta": meta}


def _post(url, body, key, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json",
                                          **({"Authorization": f"Bearer {key}"} if key else {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


class OpenAICompatBackend:
    def __init__(self, base_url=None, model=None, key=None):
        self.base = (base_url or os.environ["PB_OPENAI_BASE_URL"]).rstrip("/")
        self.model = model or os.environ["PB_OPENAI_MODEL"]
        self.key = key if key is not None else os.environ.get("PB_OPENAI_API_KEY")
        self.temperature = float(os.environ.get("PB_TEMPERATURE", "1"))
        self.max_tokens = os.environ.get("PB_MAX_TOKENS")
        self.timeout = float(os.environ.get("PB_TIMEOUT", "600"))
        self.native = True

    def body(self, messages, tools):
        b = {"model": self.model, "messages": messages, "temperature": self.temperature}
        if self.native:
            b["tools"] = tools
            b["tool_choice"] = "auto"
        if self.max_tokens:
            b["max_tokens"] = int(self.max_tokens)
        return b

    def chat(self, messages, tools):
        d = _post(self.base + "/chat/completions", self.body(messages, tools), self.key, self.timeout)
        msg = d["choices"][0]["message"]
        tcs = msg.get("tool_calls") or None
        meta = {"usage": d.get("usage"), "finish_reason": d["choices"][0].get("finish_reason")}
        if tcs:
            meta["tool_call"] = True
            for i, tc in enumerate(tcs):
                tc.setdefault("type", "function")
                tc.setdefault("id", f"call_{i}")
                if not isinstance(tc["function"].get("arguments"), str):
                    tc["function"]["arguments"] = json.dumps(tc["function"].get("arguments") or {})
        return {"content": msg.get("content"), "tool_calls": tcs, "meta": meta}


class TextJSONOverOpenAI(OpenAICompatBackend):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.native = False
        self.n = 0

    def chat(self, messages, tools):
        system = messages[0]["content"] + tool_block(tools)
        prompt = render_transcript(messages[1:])
        d = _post(self.base + "/chat/completions",
                  self.body([{"role": "system", "content": system}, {"role": "user", "content": prompt}], tools),
                  self.key, self.timeout)
        self.n += 1
        text = d["choices"][0]["message"].get("content") or ""
        content, tcs, meta = parse_text_reply(text, self.n)
        meta["usage"] = d.get("usage")
        meta["raw"] = text
        return {"content": content, "tool_calls": tcs, "meta": meta}


def from_name(name: str, folder: str):
    if name in ("haiku", "sonnet"):
        return ClaudeTextBackend(folder, name)
    if name == "openai":
        return OpenAICompatBackend()
    if name == "openai-text":
        return TextJSONOverOpenAI()
    raise ValueError(name)
