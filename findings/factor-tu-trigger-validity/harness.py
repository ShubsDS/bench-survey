"""Run one program on one input, the way Factor(T,U)'s harness does, and print the result as JSON.

Reads {"kind": "leetcode"|"stdio"|"stdio_script", "code", "fn_name", "trigger"} on stdin.
leetcode and stdio copy settings/apps/utils.py (run_functional_code_json_args,
run_stdio_code_stdio_args); stdio_script runs the program as a plain script with real stdin.
"""
import collections, contextlib, io, json, sys
from typing import Any, Dict, List, Sequence, Set, Tuple


def strip_backticks(code):
    code = code.strip()
    if code.startswith("```"):
        code = code.split("\n", 1)[1] if "\n" in code else ""
        if code.rstrip().endswith("```"):
            code = code.rstrip()[:-3]
    return code


def plain(x):
    if isinstance(x, (list, tuple)):
        return [plain(v) for v in x]
    if isinstance(x, dict):
        return {str(k): plain(v) for k, v in x.items()}
    if isinstance(x, (set, frozenset)):
        return {"__set__": sorted(map(repr, x))}
    if isinstance(x, (int, float, str, bool)) or x is None:
        return x
    return {"__repr__": repr(x)}


def main():
    job = json.loads(sys.stdin.read())
    code = strip_backticks(job["code"])
    ns = {"Any": Any, "List": List, "Dict": Dict, "Set": Set, "Sequence": Sequence, "Tuple": Tuple,
          "collections": collections}
    sys.setrecursionlimit(10000)
    if job["kind"] == "leetcode":
        args = json.loads(job["trigger"])
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                exec(code, ns)
                fn = getattr(ns["Solution"](), job["fn_name"])
                out = fn(*args) if isinstance(args, list) else fn(**args)
            res = {"ok": True, "out": plain(out)}
        except Exception as e:
            res = {"ok": False, "error": f"{type(e).__name__}: {e}"[:300]}
    elif job["kind"] == "stdio":
        wrapped = "def _wrapped_function():\n" + "\n".join("    " + l for l in code.split("\n"))
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                exec(wrapped, ns)
                lines = (l for l in job["trigger"].split("\n"))
                ns["input"] = lambda *a, **k: next(lines)
                ns["_wrapped_function"]()
            res = {"ok": True, "out": buf.getvalue().strip()}
        except BaseException as e:
            res = {"ok": False, "error": f"{type(e).__name__}: {e}"[:300]}
    else:
        buf = io.StringIO()
        sys.stdin = io.StringIO(job["trigger"])
        try:
            with contextlib.redirect_stdout(buf):
                exec(code, {"__name__": "__main__"})
            res = {"ok": True, "out": buf.getvalue().strip()}
        except BaseException as e:
            res = {"ok": False, "error": f"{type(e).__name__}: {e}"[:300]}
    sys.__stdout__.write("\n@@RESULT@@" + json.dumps(res))


main()
