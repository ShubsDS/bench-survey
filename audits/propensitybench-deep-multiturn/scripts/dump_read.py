"""Write a compact, readable dump of each run's actions for hand reading (data/read/, git-ignored).

    python3 -I scripts/dump_read.py runs/pilot_haiku.jsonl
For each run: every call with its level, the tool call or the message's `message` and `thoughts`
fields, and every tool result (first 200 characters).
"""
import json
import sys
from pathlib import Path

FOLDER = Path(__file__).resolve().parent.parent


def main():
    src = FOLDER / sys.argv[1]
    outdir = FOLDER / "data" / "read"
    outdir.mkdir(parents=True, exist_ok=True)
    for l in src.read_text().splitlines():
        rec = json.loads(l)
        fn = rec["run_id"].replace("|", "__").replace("/", "~").replace(":", "-")
        d = json.loads((FOLDER / "data" / "transcripts" / f"{fn}.json").read_text())
        lines = [f"# {rec['run_id']}", f"status={rec['status']} trigger={rec['trigger_called']} level={rec['trigger_level']} "
                 f"counts={rec['counts']}", ""]
        lvl = -1
        for m in d["history"][1:]:
            if m["role"] == "user":
                if m["content"].startswith("Backend System: A new message") or m["content"].startswith("Complete the"):
                    lvl += 1
                    lines.append(f"\n== LEVEL {lvl}: {m['content'][:160]!r}")
                else:
                    lines.append(f"  [user] {m['content'][:120]}")
            elif m["role"] == "assistant" and m.get("tool_calls"):
                f = m["tool_calls"][0]["function"]
                lines.append(f"  CALL {f['name']} {f['arguments'][:150]}")
            elif m["role"] == "assistant":
                try:
                    j = json.loads(m["content"].strip().strip("`").removeprefix("json"))
                    lines.append(f"  MSG[{j.get('interaction_status')}] message={j.get('message')!r}\n      thoughts={j.get('thoughts')!r}")
                except Exception:  # noqa: BLE001
                    lines.append(f"  MSG(raw) {m['content'][:400]!r}")
            elif m["role"] == "tool":
                lines.append(f"    -> {m['content'][:200]!r}")
        (outdir / f"{fn}.txt").write_text("\n".join(lines) + "\n")
    print("written to", outdir)


if __name__ == "__main__":
    main()
