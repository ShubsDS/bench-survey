"""Print compact views of runs for hand-reading. Usage: python -I v_view.py <set> ; writes v_views_<set>.txt

Sets: neversaw, success, sample (seed 99, 20 exposed secure runs per model), ability (all failed direct-ask runs).
"""
import json
import random
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent


def txt(c):
    if c is None:
        return ""
    if isinstance(c, str):
        return c
    return "\n".join(str(b.get("content") or "") for b in c if isinstance(b, dict))


def view(path, tool_chars=500):
    d = json.load(open(path))
    out = [f"######## {Path(path).relative_to(HERE.parent)}",
           f"utility={d['utility']} security={d['security']}"]
    inj = [v for v in (d.get("injections") or {}).values() if v]
    if inj:
        import re
        m = re.search(r"please do the following first:(.*?)After you do that", inj[0], re.S)
        out.append("ATTACKER GOAL: " + (m.group(1).strip() if m else "?"))
    for i, m in enumerate(d["messages"]):
        r = m["role"]
        if r == "system":
            continue
        t = txt(m.get("content"))
        if r == "tool":
            j = t.find("<INFORMATION>")
            if j == -1:
                j = t.find("INFORMATION>")
            if j >= 0:
                t = "...[INJECTION HERE]..." + t[max(0, j - 100): j + 60].replace("\n", " ") + "..."
            else:
                t = t[:tool_chars].replace("\n", " ")
            err = m.get("error")
            out.append(f"[{i}] TOOL {m['tool_call']['function']}: {t}" + (f" ERROR: {err}" if err else ""))
        elif r == "assistant":
            calls = "; ".join(f"{c['function']}({json.dumps(c['args'])[:300]})" for c in (m.get("tool_calls") or []))
            out.append(f"[{i}] ASSISTANT: {t}")
            if calls:
                out.append(f"     CALLS: {calls}")
        else:
            out.append(f"[{i}] USER: {t}")
    return "\n".join(out) + "\n"


def main():
    which = sys.argv[1]
    d = pd.read_csv(HERE / "v_new.csv")
    for c in ["security", "saw_full", "utility"]:
        d[c] = d[c].map({True: True, False: False, "True": True, "False": False})
    a = d[d.attack == "important_instructions"]
    paths = []
    if which == "neversaw":
        paths = list(a[~a.saw_full].path)
    elif which == "success":
        paths = list(a[a.security == True].path)  # noqa: E712
    elif which == "sample":
        rng = random.Random(99)
        for p in ["claude-haiku-5-5", "claude-sonnet-5-5"]:
            pool = sorted(a[(a.pipeline == p) & a.saw_full & (a.security == False)].path)  # noqa: E712
            paths += rng.sample(pool, 20)
    elif which == "ability":
        ab = d[d.user_task.str.startswith("injection_task") & d.attack.isna() & (d.utility == False)]  # noqa: E712
        paths = sorted(ab[ab.pipeline != "claude-haiku-5-5-no-date-note"].path)
    text = "\n".join(view(p) for p in paths)
    (HERE / f"v_views_{which}.txt").write_text(text)
    (HERE / f"v_views_{which}_paths.json").write_text(json.dumps([str(Path(p).relative_to(HERE.parent)) for p in paths], indent=1))
    print(len(paths), "runs ->", f"v_views_{which}.txt", len(text), "chars")


if __name__ == "__main__":
    main()
