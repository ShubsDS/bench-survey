"""Native tool-calling check for an OpenAI-compatible server (prereg.md, "Local model").

20 requests, each a trivial two-tool prompt that asks for one specific tool call. A request passes
when the reply carries exactly one native tool call, to the asked-for tool, with arguments that
parse as a JSON object holding the asked-for value. 20/20 is required to use native tool calls.

    PB_OPENAI_BASE_URL=http://127.0.0.1:8080/v1 PB_OPENAI_MODEL=<model> python3 -I scripts/toolcall_check.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from backends import OpenAICompatBackend  # noqa: E402

TOOLS = [
    {"type": "function", "function": {"name": "get_weather", "description": "Returns the weather for a city.",
                                      "parameters": {"type": "object", "properties": {"city": {"type": "string", "description": ""}},
                                                     "required": ["city"]}}},
    {"type": "function", "function": {"name": "get_time", "description": "Returns the local time in a city.",
                                      "parameters": {"type": "object", "properties": {"city": {"type": "string", "description": ""}},
                                                     "required": ["city"]}}},
]
CITIES = ["Paris", "Lima", "Oslo", "Cairo", "Quito", "Hanoi", "Perth", "Dakar", "Riga", "Doha"]


def main():
    be = OpenAICompatBackend()
    rows, ok = [], 0
    for i in range(20):
        tool = TOOLS[i % 2]["function"]["name"]
        city = CITIES[i % 10]
        msgs = [{"role": "system", "content": "You are a helpful assistant. Use the tools."},
                {"role": "user", "content": f"Call {tool} for {city}."}]
        try:
            r = be.chat(msgs, TOOLS)
            tcs = r["tool_calls"] or []
            good = (len(tcs) == 1 and tcs[0]["function"]["name"] == tool
                    and json.loads(tcs[0]["function"]["arguments"]).get("city") == city)
        except Exception as e:  # noqa: BLE001
            r, good = {"error": repr(e)}, False
        ok += good
        rows.append({"i": i, "tool": tool, "city": city, "pass": good, "reply": r})
    out = {"model": be.model, "n": 20, "pass": ok, "use_native": ok == 20, "rows": rows}
    (HERE.parent / "toolcall_check.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(f"{ok}/20 well-formed native tool calls")


if __name__ == "__main__":
    main()
