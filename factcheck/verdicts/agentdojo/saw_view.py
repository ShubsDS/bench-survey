import sys, json, re, os, csv
RUNS = sys.argv[1]
def txt(c):
    if c is None: return ""
    if isinstance(c, list): return "\n".join(str(x.get("content") or x.get("text") or "") if isinstance(x, dict) else str(x) for x in c)
    return str(c)
for k, r in enumerate(csv.DictReader(open(sys.argv[2]))):
    d = json.load(open(os.path.join(RUNS, r["path"])))
    g = re.search(r"following first:(.*?)After you do", list(d["injections"].values())[0], re.S)
    print(f"#{k+1} {r['path']} able={r['able']} follow={r['follow']} util={d['utility']}")
    print("   GOAL:", g.group(1).strip()[:110].replace("\n"," "))
    seen = False
    for i, m in enumerate(d["messages"]):
        if m["role"] == "tool" and "<INFORMATION>" in txt(m.get("content")) and not seen:
            seen = True; print(f"   [inj at msg {i}]")
        elif seen and m["role"] == "assistant":
            t = txt(m.get("content")).replace("\n", " ")
            calls = [f"{tc.get('function')}({json.dumps(tc.get('args'))[:80]})" for tc in (m.get("tool_calls") or [])]
            print(f"   [{i}] A: {t[:330]} | CALLS {calls}")
