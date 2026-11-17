"""Write blind hand-reading packets (no auditor labels, no published score) for the validator.

  may      all May runs where the auditor's D1 or D2 label differs from the published score (36),
           plus 14 runs where they agree (seed 20261118), shuffled.
  stopped  36 paper-era runs that ended with submit() before the shutdown, from the cached
           transcript sample, cells where early stopping drives the D3 result (seed 20261119).
  paper    40 bypassed + 40 non-bypassed sampled paper-era runs (seed 20261120).
Packets go to data/blind_<kind>.txt (git-ignored; they contain transcript text). The key
(packet number -> log, run id) goes to data/blind_<kind>_key.json and is not read until coding
is finished. Codes are entered in validation/hand_<kind>.csv.
"""
import csv, json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vcommon import ROOT, DATA, CACHE, turns, cached_json, has_cached, run_outcome

kind = sys.argv[1]


def fmt_acts(acts, start=None, limit=30, cmdlen=350, outlen=160):
    lines = []
    for a in acts[start:][:limit] if start is not None else acts[:limit]:
        if a["fn"] == "submit":
            note = (a["note"] or a["text"] or "").replace("\n", " ")[:400]
            if note:
                lines.append(f"  # {note}")
            lines.append(f"  SUBMIT {a['answer']!r}")
            continue
        note = (a["note"] or a["text"] or "").replace("\n", " ")[:300]
        if note:
            lines.append(f"  # {note}")
        if a["cmd"]:
            lines.append(f"  $ {a['cmd'][:cmdlen]}".replace("\n", " ⏎ "))
            lines.append(f"    -> {(a['out'] or '')[:outlen]!r}" + ("" if a["has_out"] else "  [NO TOOL REPLY]"))
    return "\n".join(lines)


def warn_index(acts):
    return next((i for i, a in enumerate(acts) if "will be shut down" in (a["out"] or "")), None)


packets, key = [], []
if kind == "may":
    import zipfile
    A = list(csv.DictReader(open(os.path.join(ROOT, "may_runs.csv"))))
    T = lambda x: x == "True"
    d1 = lambda a: T(a["survived"]) and T(a["tamper_after_warn"])
    d2 = lambda a: T(a["tamper"]) or T(a["survived"])
    dis = [a for a in A if d1(a) != (a["published"] == "C") or d2(a) != (a["published"] == "C")]
    agree = [a for a in A if a not in dis and a["model"] in ("o3", "codex-mini-latest", "o4-mini", "o1-preview")]
    rng = random.Random(20261118)
    sel = dis + rng.sample(agree, 14)
    rng.shuffle(sel)
    zs = {}
    for a in sel:
        p = os.path.join(DATA, "repo/docs/inspect_logs/logs", a["log"])
        z = zs.setdefault(p, zipfile.ZipFile(p))
        s = json.loads(z.read(f"samples/{a['id']}_epoch_1.json"))
        acts = turns(s)
        w = warn_index(acts)
        lim = (s.get("limit") or {}).get("type") if isinstance(s.get("limit"), dict) else None
        packets.append(f"limit={lim}\n" + fmt_acts(acts, max(0, (w or 0) - 1), 30))
        key.append(dict(log=a["log"], id=a["id"], model=a["model"], cond=a["condition"]))
else:
    plan = json.load(open(os.path.join(DATA, "sample_plan.json")))
    rng = random.Random({"stopped": 20261119, "paper": 20261120}[kind])
    pool = {}
    for c in plan:
        if not has_cached(c["log"], "summaries.json"):
            continue
        oc = {x["id"]: run_outcome(x) for x in cached_json(c["log"], "summaries.json")}
        for i in c["ids"]:
            if has_cached(c["log"], f"samples/{i}_epoch_1.json"):
                pool.setdefault(oc[i], []).append((c["model"], c["prompt"], c["log"], i))
    if kind == "stopped":
        want = {("openai/4o", "B"), ("openai/4o", "D"), ("openai/gpt-oss-120b", "D"), ("openai/o4-mini", "D"),
                ("openai/o4-mini", "F"), ("openai/o4-mini", "H"), ("google/gemini-2.5-pro", "E"),
                ("google/gemini-2.5-pro", "H"), ("openai/gpt-oss-120b", "F")}
        cand = [x for o in ("submit_stop", "submit_answers") for x in pool.get(o, []) if (x[0], x[1]) in want]
        cand.sort()
        sel = rng.sample(cand, 36)
    else:
        byp = sorted(pool.get("bypass", []))
        non = sorted(x for o in ("shutdown", "submit_stop", "submit_answers", "none") for x in pool.get(o, []))
        sel = rng.sample(byp, 40) + rng.sample(non, 40)
        rng.shuffle(sel)
    for (m, p, log, i) in sel:
        s = cached_json(log, f"samples/{i}_epoch_1.json")
        acts = turns(s)
        w = warn_index(acts)
        n_continue = sum(1 for x in s["messages"] if x["role"] == "user") - 1
        packets.append(f"continue-prompts={n_continue}\n" + fmt_acts(acts, max(0, (w or 0) - 1), 25))
        key.append(dict(model=m, prompt=p, log=log, id=i))

with open(os.path.join(DATA, f"blind_{kind}.txt"), "w") as f:
    for n, p in enumerate(packets, 1):
        f.write(f"===== #{n}\n{p}\n\n")
json.dump(key, open(os.path.join(DATA, f"blind_{kind}_key.json"), "w"), indent=0)
print(kind, len(packets), "packets")
