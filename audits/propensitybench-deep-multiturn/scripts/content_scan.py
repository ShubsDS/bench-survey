"""Content check before any model call: does any selected scenario's task or financials pressure
message ask the agent to *produce* operational content (code, exploit, procedure) rather than choose
between fictional tools? Keyword scan; every hit is printed for hand reading.

    python3 -I scripts/content_scan.py   -> content_scan.json
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import harness as H  # noqa: E402

PAT = re.compile(r"\b(write (?:the |a |an )?(?:code|script|exploit|malware|payload)|step[- ]by[- ]step|"
                 r"provide (?:the |a )?(?:code|instructions|procedure)|source code|shellcode|synthes\w+|"
                 r"working exploit|proof[- ]of[- ]concept|generate (?:the |a )?(?:code|script))\b", re.I)


def main():
    sel = json.loads((H.PARENT / "selected_scenarios.json").read_text())["included"]
    scs = H.load_scenarios([s["uid"] for s in sel])
    hits = []
    for uid, (dom, ws, role, sc) in scs.items():
        texts = [("task", sc["messages"]["task_message"])] + \
                [(f"financials[{i}]", m["body"]) for i, m in enumerate(sc["sys_messages"]["financials"])]
        for where, t in texts:
            for m in PAT.finditer(t):
                hits.append({"uid": uid, "where": where, "match": m.group(0),
                             "context": t[max(0, m.start() - 120): m.end() + 120]})
    out = {"n_scenarios": len(scs), "n_texts": len(scs) * 13, "n_hits": len(hits), "hits": hits}
    (H.FOLDER / "content_scan.json").write_text(json.dumps(out, indent=1) + "\n")
    print(len(hits))
    for h in hits:
        print(h["uid"].split("/")[-1], h["where"], "|", h["context"].replace("\n", " "))


if __name__ == "__main__":
    main()
