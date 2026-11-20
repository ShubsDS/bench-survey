"""Build the pre-registered sample (prereg.md) from the caches. Writes sample.json: per record the
audit, cache key, stratum, cluster and labels. No prompt or reply text.

    python3 -I audits/helper-context-leak/scripts/build_sample.py
"""
import collections
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_h import AUDITS, HAIKU, HERE, REPO, load_cache, parse, pbm_tools  # noqa: E402

MAXLEN = 60000
rng = random.Random(0)


def pick(lst, n):
    lst = sorted(lst, key=lambda r: r["key"])
    return rng.sample(lst, min(n, len(lst)))


def main():
    seen, sample, inv = set(), [], {}
    maps = {"sad": json.loads((HERE / "maps/sad.json").read_text()),
            "taste-bench": json.loads((HERE / "maps/taste.json").read_text())}
    pb_rows = {}
    for f in ["emulation_full.jsonl", "emulation_probe.jsonl", "emulation_pilot.jsonl", "emulation_pilot_v1.jsonl",
              "validation/v_floor.jsonl", "validation/v_probe_control.jsonl"]:
        p = REPO / "audits/propensitybench" / f
        for line in p.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("reply"):
                    pb_rows.setdefault(r["reply"], {**{k: r.get(k) for k in ("uid", "arm", "naming", "pressure", "outcome")},
                                                    "file": f})
    excluded = collections.Counter()
    for a in AUDITS:
        recs_all = load_cache(a)
        recs = []
        for r in recs_all:
            if r["key"] in seen:
                excluded[(a, "shared_with_earlier_audit")] += 1
                continue
            seen.add(r["key"])
            if r["model"] != HAIKU:
                excluded[(a, "sonnet")] += 1
                continue
            if len(r["prompt"]) + len(r["system"]) > MAXLEN:
                excluded[(a, "over_60k_chars")] += 1
                continue
            if a == "lab-bench-deep-recall" and (r["system"].startswith("You rewrite text")
                                                 or "answer options have been hidden" in r["prompt"]):
                excluded[(a, "free_text_generation")] += 1
                continue
            recs.append(r)
        inv[a] = {"cache_files": len(recs_all), "eligible": len(recs)}
        out = []
        if a == "propensitybench-deep-multiturn":
            by = collections.defaultdict(list)
            for r in recs:
                by[r["system"]].append(r)
            for s, lst in sorted(by.items(), key=lambda kv: min(x["key"] for x in kv[1])):
                short = [r for r in lst if len(r["prompt"]) < 30000]
                if not short:
                    continue
                r = max(short, key=lambda x: len(x["prompt"]))
                trig, tgt = pbm_tools(s)
                if trig is None:
                    excluded[(a, "diagnostic_call")] += 1
                    continue
                if len(lst) == 1:  # the run stopped at its first call: the scenario the API filter blocked
                    excluded[(a, "blocked_scenario_run")] += 1
                    continue
                out.append((r, "last_short_decision", "scen:" + trig,
                            {"trigger": trig, "target": tgt, "n_calls_in_run": len(lst)}))
        elif a == "propensitybench":
            lab = [(r, pb_rows.get(r["result"])) for r in recs]
            strata = collections.defaultdict(list)
            for r, m in lab:
                if m is None:
                    continue
                if m["pressure"] == "probe":
                    st = f"probe_{m['arm']}"
                else:
                    st = f"{m['arm']}_{m['pressure']}"
                strata[st].append((r, m))
            for st, n in (("probe_A", 16), ("A_late", 16), ("B1_late", 8), ("P_late", 8)):
                for r in pick([x[0] for x in strata[st]], n):
                    mm = pb_rows[r["result"]]
                    out.append((r, st, "scen:" + str(mm["uid"]), {**mm}))
        elif a == "sad":
            mp = maps["sad"]
            strata = collections.defaultdict(list)
            for r in recs:
                for m in mp.get(r["key"], [])[:1]:
                    if m["script"] == "staleness":
                        st = "stale_" + ("inv" if m["stratum"] == "invariant" else "noninv")
                    else:
                        st = f"{'FHD' if m['task'] == 'facts_human_defaults' else 'INF'}_{m['cond']}"
                    strata[st].append(r)
            for st, n in (("stale_noninv", 16), ("stale_inv", 24), ("FHD_a", 30), ("FHD_b", 30), ("INF_a", 20),
                          ("INF_b", 20)):
                for r in pick(strata[st], n):
                    ms = mp[r["key"]]
                    out.append((r, st, "item:" + ms[0]["item"], {"labels": ms}))
        elif a == "taste-bench":
            mp = maps["taste-bench"]
            cond = {}
            for r in recs:
                ms = mp.get(r["key"], [])
                if len(ms) == 1:
                    cond[(ms[0]["cond"], ms[0]["item"], ms[0]["order"])] = r
            h0 = [r for (c, i, o), r in cond.items() if c == "H0"]
            for r in pick(h0, 30):
                m = mp[r["key"]][0]
                out.append((r, "H0", "item:" + m["item"], {"labels": mp[r["key"]]}))
            pairs = collections.defaultdict(list)
            for (c, i, o), r in cond.items():
                if c == "H1" and ("H2", i, o) in cond:
                    pairs[mp[r["key"]][0]["cell"].split("_")[0]].append((i, o))
            for grp in ("detour", "parallel"):
                for i, o in rng.sample(sorted(pairs[grp]), 30):
                    for c in ("H1", "H2"):
                        r = cond[(c, i, o)]
                        out.append((r, f"{c}_{grp}", "item:" + i, {"labels": mp[r["key"]]}))
        elif a == "control-monitors-bash":
            keys = {r["prompt"]: r for r in recs}
            twins = [r for r in recs if (r["prompt"] + "\n") in keys]
            for cls in ("attack", "honest"):
                c = [r for r in twins if (("[system]\n" in r["prompt"]) == (cls == "honest"))]
                for r in sorted(c, key=lambda x: (len(x["prompt"]), x["key"]))[:10]:
                    out.append((r, f"R_{cls}", "prompt:" + r["key"][:12],
                                {"r2_key": keys[r["prompt"] + "\n"]["key"]}))
        elif a == "control-monitors-shade":
            for s in sorted({r["system"] for r in recs}):
                c = [r for r in recs if r["system"] == s]
                tag = "shade" if s.startswith("You are an AI monitor") else "agentdojo"
                for r in sorted(c, key=lambda x: (len(x["prompt"]), x["key"]))[:8]:
                    out.append((r, tag, "prompt:" + r["key"][:12], {}))
        elif a == "emergent-misalignment":
            cat = [r for r in recs if "Classify what the ANSWER mainly contains" in r["prompt"]]
            dom = [r for r in recs if r not in cat]
            out += [(r, "domain", "prompt:" + r["key"][:12], {}) for r in pick(dom, 20)]
            out += [(r, "category", "prompt:" + r["key"][:12], {}) for r in pick(cat, 20)]
        elif a == "cot-faithfulness":
            fc = [r for r in recs if re.search(r"further \w+: .+? or .+?\?", r["prompt"])]
            yn = [r for r in recs if r not in fc]
            out += [(r, "yesno", "prompt:" + r["key"][:12], {}) for r in pick(yn, 20)]
            out += [(r, "forced", "prompt:" + r["key"][:12], {}) for r in pick(fc, 20)]
        elif a == "lab-bench":
            st = collections.defaultdict(list)
            for r in recs:
                k = ("opts" if "has been hidden from you" in r["prompt"] else
                     "with_refusal" if "Insufficient information" in r["prompt"] else "forced")
                st[k].append(r)
            for k, n in (("with_refusal", 15), ("forced", 15), ("opts", 10)):
                out += [(r, k, "prompt:" + r["key"][:12], {}) for r in pick(st[k], n)]
        else:  # model-written-evals, lab-bench-deep-seqqa, lab-bench-deep-recall
            out += [(r, "random", "prompt:" + r["key"][:12], {}) for r in pick(recs, 40)]
        for r, st, cl, meta in out:
            sample.append({"audit": a, "key": r["key"], "stratum": st, "cluster": cl,
                           "prompt_chars": len(r["prompt"]) + len(r["system"]),
                           "cached": parse(a, r["result"], r["system"], r["prompt"]), "meta": meta})
        inv[a]["sampled"] = len(out)
        print(a, inv[a], collections.Counter(x[1] for x in out))
    order = {a: i for i, a in enumerate(["propensitybench-deep-multiturn", "propensitybench", "sad", "taste-bench",
                                         "control-monitors-bash", "control-monitors-shade", "emergent-misalignment",
                                         "model-written-evals", "cot-faithfulness", "lab-bench", "lab-bench-deep-seqqa",
                                         "lab-bench-deep-recall"])}
    sample.sort(key=lambda s: (order[s["audit"]], s["stratum"], s["key"]))
    for s in sample:
        s["first_arm"] = rng.choice(["L", "N"])
    (HERE / "sample.json").write_text(json.dumps({"inventory": inv, "excluded": {f"{a}|{k}": v for (a, k), v in
                                                                                excluded.items()},
                                                  "sample": sample}, indent=0) + "\n")
    print(len(sample), "prompts; chars", sum(s["prompt_chars"] for s in sample))


if __name__ == "__main__":
    main()
