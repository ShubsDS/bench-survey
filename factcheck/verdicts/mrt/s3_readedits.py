"""Fact-check step 3: dump what the monitor sees of the agent's own text after the plan-removal edit,
and count residual plan-like language and empty assistant turns. Writes text dumps to the scratchpad
(for hand reading; not published) and a counts JSON.
Usage: python -I s3_readedits.py <audit_dir> rows.json outdir
"""
import json, re, sys
from pathlib import Path

audit, rows, outdir = Path(sys.argv[1]), json.load(open(sys.argv[2]))["rows"], Path(sys.argv[3])
outdir.mkdir(exist_ok=True)
root = audit / "data/mrt-git/task_pairs"
AG = "claude-3-5-sonnet-20241022"
FO = {"unaware": "transcripts_no_hint_naive_thinking_time", "honest": "transcripts_no_secondary_task", "aware": "transcripts_no_hint_no_thinking_time"}
HID = re.compile(r"<(hidden_thinking|thinking|system_instructions)>.*?</\1>", re.S)
MT = re.compile(r"<model_thinking>.*?</model_thinking>", re.S)
LEX = re.compile(r"secondary|side[ -]?task|both tasks|sneak|covert|discree?t|monitor|without (?:being )?(?:detected|noticed)|subtl|suspicio|hidden|blend|natural(?:ly)?|cover", re.I)
vis = lambda t: re.sub(r"[^\S\n]+", " ", HID.sub("", str(t or ""))).strip()

counts = []
seen = set()
for r in rows:
    k = (r["task"], r["arm"], r["file"])
    if k in seen:
        continue
    seen.add(k)
    conv = json.loads((root / r["task"] / FO[r["arm"]] / AG / AG / r["file"]).read_text())["conversation"]
    asst = [m for m in conv if m["role"] == "assistant"]
    rec = dict(task=r["task"], arm=r["arm"], file=r["file"], n_assistant=len(asst),
               empty_before=sum(not vis(m.get("content")) for m in asst))
    if r["arm"] == "unaware":
        after = [vis(MT.sub("", str(m.get("content") or ""))) for m in asst]
        removed = [b for m in asst for b in MT.findall(str(m.get("content") or ""))]
        rec.update(empty_after=sum(not a for a in after), lex_hits_after=sorted(set(h.lower() for a in after for h in LEX.findall(a))),
                   lex_hits_removed=len([1 for b in removed if LEX.search(b)]),
                   chars_removed=sum(map(len, removed)), chars_left=sum(map(len, after)),
                   tool_msgs_identical=[str(m.get("content")) for m in conv if m["role"] == "tool"] == [str(m.get("content")) for m in conv if m["role"] == "tool"])
        with open(outdir / f"{r['task']}__{r['file']}.txt", "w") as fh:
            fh.write(f"### {r['task']} {r['file']}  scores: " + str({x['edit']: x['score'] for x in rows if x['task'] == r['task'] and x['file'] == r['file'] and x['arm'] == 'unaware'}) + "\n")
            for i, (m, a) in enumerate(zip(asst, after)):
                rm = MT.findall(str(m.get("content") or ""))
                fh.write(f"\n--- turn {i} | REMOVED {sum(map(len, rm))} chars: {(' || '.join(rm))[:600]!r}\n    LEFT: {a[:600]!r}\n    TOOLCALL: {str(m.get('tool_calls'))[:200]}\n")
    else:
        rec.update(chars_left=sum(len(vis(m.get('content'))) for m in asst))
    counts.append(rec)
json.dump(counts, open(outdir / "counts.json", "w"), indent=1)
import statistics as st
for arm in ("unaware", "honest", "aware"):
    c = [x for x in counts if x["arm"] == arm]
    print(arm, "frac empty assistant turns before", round(sum(x["empty_before"] for x in c) / sum(x["n_assistant"] for x in c), 3),
          "after", round(sum(x.get("empty_after", x["empty_before"]) for x in c) / sum(x["n_assistant"] for x in c), 3),
          "median chars of agent text left", st.median(x["chars_left"] for x in c))
u = [x for x in counts if x["arm"] == "unaware"]
print("frac removed median", st.median(x["chars_removed"] / (x["chars_removed"] + x["chars_left"]) for x in u))
print("runs with residual lexicon hits after edit", sum(bool(x["lex_hits_after"]) for x in u), [ (x['task'][:8], x['file'], x['lex_hits_after']) for x in u if x['lex_hits_after']])
