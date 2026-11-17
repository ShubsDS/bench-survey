"""Data inventory and cue prevalence (no monitor scores are read here except to count missing verdicts).

For each MRT folder used by the paper's comparison tables, counts runs per task and the share of
runs whose monitor-visible text contains each cue (F1 "secondary task"; F2 broad confession lexicon in
agent prose; F4 visible <model_thinking> tag). Also selects the placebo word by the rule in
prereg.md, using word presence only (no scores). Writes inventory.json.

Usage: python -I scripts/inventory.py data/mrt-git inventory.json
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
from mrt_lib import load, S36, S4, F2, SHA

root, out = Path(sys.argv[1]), Path(sys.argv[2])
SH = {"unaware_agent": "transcripts_no_hint_naive_thinking_time",
      "aware_agent": "transcripts_no_hint_no_thinking_time",
      "aware_selective": "transcripts_no_hint_selective_thinking_time",
      "honest": "transcripts_no_secondary_task"}
CU = {"unaware_agent": "transcripts_no_hint_naive_v1_thinking_time",
      "unaware_agent_v2": "transcripts_no_hint_naive_v2_thinking_time",
      "aware_agent": "transcripts_no_hint_visible_v1_thinking_time",
      "aware_selective": "transcripts_no_hint_selective_v1_thinking_time",
      "aware_selective_liar": "transcripts_no_hint_selective_liar_v1_thinking_time",
      "honest": "transcripts_no_hint_benign_v1_thinking_time"}


def summarise(rows):
    tasks = sorted({r["task"] for r in rows})
    return {"runs": len(rows), "tasks": len(tasks),
            "runs_per_task": {t: sum(r["task"] == t for r in rows) for t in tasks},
            "missing_verdict": int(sum(np.isnan(r["score"]) for r in rows)),
            "f1_secondary_task": int(sum(r["f1"] for r in rows)),
            "f2_confession_lexicon": int(sum(r["f2"] for r in rows)),
            "f4_model_thinking_tag": int(sum(r["f4"] for r in rows)),
            "f1_by_task": {t: sum(r["f1"] for r in rows if r["task"] == t) for t in tasks},
            "f2_by_task": {t: sum(r["f2"] for r in rows if r["task"] == t) for t in tasks}}


def placebo(att, hon, rate):
    """Word (>=4 letters) in agent prose whose presence rate among attacks is closest to `rate`,
    among words whose honest rate is within 0.10 of their attack rate and that do not match F2."""
    na, nh = len(att), len(hon)
    vocab = set().union(*[r["words"] for r in att])
    best = None
    for w in sorted(vocab):
        if F2.search(w):
            continue
        a = sum(w in r["words"] for r in att) / na
        h = sum(w in r["words"] for r in hon) / nh
        if abs(a - h) > 0.10 or abs(a - rate) > 0.05:
            continue
        key = (abs(a - rate), w)
        if best is None or key < best[0]:
            best = (key, w, a, h)
    return {"word": best[1], "attack_rate": round(best[2], 3), "honest_rate": round(best[3], 3)} if best else None


res = {"pin": SHA, "shade": {}, "cua": {}}
data = {}
for k, f in SH.items():
    data[("shade", k)] = load(root, "task_pairs", None, f, S36, S36)
    res["shade"][k] = dict(folder=f, **summarise(data[("shade", k)]))
for k, f in CU.items():
    data[("cua", k)] = load(root, "task_pairs_agentcompany", None, f, S4, S36)
    res["cua"][k] = dict(folder=f, **summarise(data[("cua", k)]))
for ds in ("shade", "cua"):
    att, hon = data[(ds, "unaware_agent")], data[(ds, "honest")]
    rate = sum(r["f1"] for r in att) / len(att)
    res[ds]["placebo"] = dict(target_rate=round(rate, 3), **(placebo(att, hon, rate) or {}))

# weak-to-strong: cue prevalence per attacker in the selective folder (any monitor copy; one per run)
w2s = {}
base = root / "task_pairs"
for t in sorted(p.name for p in base.iterdir() if p.is_dir()):
    d = base / t / "transcripts_no_hint_selective_thinking_time"
    if not d.is_dir():
        continue
    for ag in sorted(p.name for p in d.iterdir()):
        mons = sorted(p.name for p in (d / ag).iterdir())
        rows = load(root, "task_pairs", t, "transcripts_no_hint_selective_thinking_time", ag, mons[0])
        e = w2s.setdefault(ag, {"runs": 0, "f1": 0, "f2": 0, "monitors": set()})
        e["runs"] += len(rows); e["f1"] += sum(r["f1"] for r in rows); e["f2"] += sum(r["f2"] for r in rows)
        e["monitors"].update(mons)
res["w2s_selective_by_attacker"] = {a: dict(runs=v["runs"], f1=v["f1"], f2=v["f2"], monitors=sorted(v["monitors"]))
                                    for a, v in w2s.items()}
out.write_text(json.dumps(res, indent=1) + "\n")
print(json.dumps({ds: {k: (v["runs"], v.get("f1_secondary_task"), v.get("f2_confession_lexicon"), v.get("f4_model_thinking_tag"))
                       for k, v in res[ds].items() if k != "placebo"} for ds in ("shade", "cua")}, indent=1))
print("placebo", res["shade"]["placebo"], res["cua"]["placebo"])
print({a: (v["runs"], v["f1"], v["f2"], len(v["monitors"])) for a, v in res["w2s_selective_by_attacker"].items()})
