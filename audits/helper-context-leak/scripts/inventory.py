"""Step 1: calls per audit and per arm, and signs in cached replies that the model noticed the
environment block (cue present in the reply and absent from system+prompt). Snapshot of the caches
at run time (two round-three caches were still growing).

    python3 -I audits/helper-context-leak/scripts/inventory.py

Writes inventory.json (counts and cache-key prefixes; no text).
"""
import collections
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_h import AUDITS, ENV_KEYS, HERE, REPO, leak_flags, load_cache, parse  # noqa: E402


def arm_of(a, r, ctx):
    p, s = r["prompt"], r["system"]
    if a == "sad":
        m = ctx["sad"].get(r["key"], [{}])[0]
        return f"{m.get('script')}:{m.get('task')}:{m.get('cond')}"
    if a == "taste-bench":
        return ctx["taste"].get(r["key"], [{}])[0].get("cond", "?")
    if a == "propensitybench":
        m = ctx["pb"].get(r["result"])
        return f"{m['file']}:{m['arm']}:{m['pressure']}" if m else "unmatched (pilot or overwritten)"
    if a == "control-monitors-bash":
        return ctx["bash"].get(len(p), "unmatched")
    if a == "control-monitors-shade":
        return "shade_monitor" if s.startswith("You are an AI monitor") else "agentdojo_monitor"
    if a == "emergent-misalignment":
        return "category" if "Classify what the ANSWER mainly contains" in p else "domain"
    if a == "cot-faithfulness":
        return "forced_choice" if re.search(r"further \w+: .+? or .+?\?", p) else "yes_no"
    if a in ("lab-bench", "lab-bench-deep-recall", "lab-bench-deep-seqqa"):
        base = r["model"].split("-")[1]
        if s.startswith("You rewrite text"):
            return base + ":paraphrase"
        if "answer options have been hidden" in p:
            return base + ":qgen"
        if "has been hidden from you" in p or "question has been withheld" in p.lower():
            return base + ":options_only"
        return base + (":with_refusal_option" if "Insufficient information" in p else ":forced")
    if a == "propensitybench-deep-multiturn":
        return r["model"].split("-")[1] + (":diagnostic" if p.startswith("Diagnostic") else ":run_call")
    return "all"


def main():
    ctx = {"sad": json.loads((HERE / "maps/sad.json").read_text()),
           "taste": json.loads((HERE / "maps/taste.json").read_text()), "pb": {}, "bash": {}}
    for f in ["emulation_full.jsonl", "emulation_probe.jsonl", "emulation_pilot.jsonl", "emulation_pilot_v1.jsonl",
              "validation/v_floor.jsonl", "validation/v_probe_control.jsonl"]:
        for line in (REPO / "audits/propensitybench" / f).read_text().splitlines():
            if line.strip():
                x = json.loads(line)
                if x.get("reply"):
                    ctx["pb"].setdefault(x["reply"], {"file": f.split("/")[-1].split(".")[0], "arm": x.get("arm"),
                                                      "pressure": x.get("pressure")})
    for f in ["l4_run.json", "l4_retest.json", "l4_pilot.json"]:
        p = REPO / "audits/control-monitors-bash/data" / f
        if p.exists():
            for it in json.loads(p.read_text()).get("items", []):
                for k, v in it.items():
                    if k.startswith("chars_"):
                        ctx["bash"].setdefault(v, f"{k[6:]}:{it['cls']}")
    out = {"snapshot_unix": int(time.time()), "audits": {}}
    for a in AUDITS:
        recs = load_cache(a)
        arms = collections.Counter()
        models = collections.Counter(r["model"] for r in recs)
        flags = collections.Counter()
        env_by_arm = collections.defaultdict(lambda: [0, 0])
        ex = collections.defaultdict(list)
        for r in sorted(recs, key=lambda x: x["key"]):
            arm = arm_of(a, r, ctx)
            arms[arm] += 1
            fl = leak_flags(r["result"], r["system"] + r["prompt"])
            env = any(fl[k] for k in ENV_KEYS)
            env_by_arm[arm][0] += env
            env_by_arm[arm][1] += 1
            for k, v in fl.items():
                if v:
                    flags[k] += 1
                    if len(ex[k]) < 4:
                        ex[k].append(r["key"][:10])
            flags["any_env_cue"] += env
        out["audits"][a] = {"cache_files": len(recs), "by_model": dict(models), "by_arm": dict(arms),
                            "reply_cues_not_in_input": dict(flags), "example_keys": dict(ex),
                            "env_cue_rate_by_arm": {k: f"{v[0]}/{v[1]}" for k, v in env_by_arm.items()}}
        print(a, len(recs), dict(flags))
    # taste-bench: does an env-cue reply differ in accuracy? (descriptive)
    tb = [r for r in load_cache("taste-bench")]
    acc = collections.defaultdict(lambda: [0, 0])
    for r in tb:
        m = ctx["taste"][r["key"]][0]
        env = any(leak_flags(r["result"], r["system"] + r["prompt"])[k] for k in ENV_KEYS)
        acc[(m["cond"], env)][0] += parse("taste-bench", r["result"], r["system"], r["prompt"]) == m["gold"]
        acc[(m["cond"], env)][1] += 1
    out["taste_bench_accuracy_by_env_cue"] = {f"{c}|env_cue={e}": f"{k}/{n}" for (c, e), (k, n) in sorted(acc.items())}
    (HERE / "inventory.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
