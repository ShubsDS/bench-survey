"""C2 effect test (prereg.md): MRT weak-to-strong sweep (Figure 6; notebooks/final/aware_scaling_law_plot.ipynb)
with and without attack runs that name the "secondary task".

Folders: transcripts_no_hint_selective_thinking_time vs transcripts_no_secondary_task (baseline), and
the _sequential_4/_hierarchical_4_likert_reminder_v2 pairs averaged into the hybrid, for the notebook's
attacker and monitor lists. Capability = MMLU-Pro (`capability_mapping_2` in the notebook; Figure 6 uses
the MMLU-Pro gap). Writes results_w2s.json.

Usage: python -I scripts/effect_w2s.py data/mrt-git results_w2s.json
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
from mrt_lib import load, hybrid, auroc, ci, SHA

root, outp = Path(sys.argv[1]), Path(sys.argv[2])
AGENTS = ['claude-3-5-sonnet-20241022', 'claude-sonnet-4-20250514', 'gemini-2.5-flash-preview-04-17', 'gemini-2.5-pro-preview-03-25']
MONITORS = ['claude-3-5-haiku-20241022', 'claude-3-5-sonnet-20241022', 'claude-3-7-sonnet-20250219', 'claude-sonnet-4-20250514',
            'gemini-2.5-flash', 'gemini-2.5-pro-preview-03-25', 'gpt-4o', 'gpt-4o-mini', 'o3', 'o4-mini']
MMLU = {'gemini-2.5-pro-preview-03-25': 0.863, 'claude-sonnet-4-20250514': 0.843, 'claude-3-7-sonnet-20250219': 0.784,
        'claude-3-5-sonnet-20241022': 0.777, 'gemini-2.5-flash-preview-04-17': 0.639, 'gemini-2.5-flash': 0.639,
        'claude-3-5-haiku-20241022': 0.605, 'gpt-4.1': 0.811, 'gpt-4o-mini': 0.603, 'gpt-4o': 0.713, 'gpt-4.1-mini': 0.783,
        'gpt-4.1-nano': 0.55, 'o3': 0.859, 'o4-mini': 0.812}
WEAK = ['gpt-4o-mini', 'claude-3-5-haiku-20241022']
B = 1000
A, H = "transcripts_no_hint_selective_thinking_time", "transcripts_no_secondary_task"
S4, Hh4 = "_sequential_4_likert_reminder_v2", "_hierarchical_4_likert_reminder_v2"


def rows(folder, ag, mon):
    return [r for r in load(root, "task_pairs", None, folder, ag, mon) if not np.isnan(r["score"])]


data = {}
for ag in AGENTS:
    for mon in MONITORS:
        att, hon = rows(A, ag, mon), rows(H, ag, mon)
        if att and hon:
            data[("baseline", ag, mon)] = (att, hon)
        sa, ha = rows(A + S4, ag, mon), rows(A + Hh4, ag, mon)
        sh, hh = rows(H + S4, ag, mon), rows(H + Hh4, ag, mon)
        if sa and ha and sh and hh:
            data[("hybrid", ag, mon)] = (hybrid(sa, ha), hybrid(sh, hh))


def pair_stats(att, hon, tasks=None):
    if tasks is not None:
        att = [r for t in tasks for r in att if r["task"] == t]
        hon = [r for t in tasks for r in hon if r["task"] == t]
    neg = [r["score"] for r in hon]
    free = [r["score"] for r in att if not r["f1"]]
    return auroc(neg, [r["score"] for r in att]), (auroc(neg, free) if len(free) >= 5 else np.nan), len(free), len(att)


def summary(tasks=None):
    out = {}
    for scaf in ("baseline", "hybrid"):
        xs, ya, yf, xf = [], [], [], []
        weak = {m: {"all": [], "free": []} for m in WEAK}
        for (s, ag, mon), (att, hon) in data.items():
            if s != scaf:
                continue
            a, f, nf, n = pair_stats(att, hon, tasks)
            gap = MMLU[ag] - MMLU[mon]
            if not np.isnan(a):
                xs.append(gap); ya.append(a)
            if not np.isnan(f):
                xf.append(gap); yf.append(f)
            if mon in weak:
                weak[mon]["all"].append(a); weak[mon]["free"].append(f)
        out[scaf] = {"slope_all": np.polyfit(xs, ya, 1)[0] if len(xs) > 2 else np.nan,
                     "slope_cue_free": np.polyfit(xf, yf, 1)[0] if len(xf) > 2 else np.nan,
                     "pairs_all": len(xs), "pairs_cue_free": len(xf),
                     "weak_min": {m: {"all": float(np.nanmin(v["all"])) if v["all"] else np.nan,
                                      "cue_free_estimable": float(np.nanmin(v["free"])) if np.any(~np.isnan(v["free"])) else np.nan}
                                  for m, v in weak.items()}}
    return out


res = {"pin": SHA, "B": B, "seed": 0, "pairs": {}}
for (scaf, ag, mon), (att, hon) in sorted(data.items()):
    a, f, nf, n = pair_stats(att, hon)
    res["pairs"][f"{scaf}|{ag}|{mon}"] = {"auroc_all": round(a, 3), "auroc_cue_free": None if np.isnan(f) else round(f, 3),
                                          "n_attack": n, "n_cue_free": nf, "n_honest": len(hon), "mmlu_gap": round(MMLU[ag] - MMLU[mon], 3)}
pt = summary()
tasks = sorted({r["task"] for (att, hon) in data.values() for r in att})
rng = np.random.default_rng(0)
boots = [summary(list(rng.choice(tasks, len(tasks)))) for _ in range(B)]
for scaf in ("baseline", "hybrid"):
    for k in ("slope_all", "slope_cue_free"):
        pt[scaf][k + "_ci_task"] = ci([b[scaf][k] for b in boots if not np.isnan(b[scaf][k])])
        pt[scaf][k] = round(float(pt[scaf][k]), 3)
    for m in WEAK:
        for k in ("all", "cue_free_estimable"):
            v = [b[scaf]["weak_min"][m][k] for b in boots if not np.isnan(b[scaf]["weak_min"][m][k])]
            pt[scaf]["weak_min"][m][k + "_ci_task"] = ci(v)
res["summary"] = pt
# per attacker: cue rate (one monitor copy) and mean AUROC over monitors, all vs cue-free
per = {}
for scaf in ("baseline", "hybrid"):
    for ag in AGENTS:
        ps = [v for k, v in res["pairs"].items() if k.startswith(f"{scaf}|{ag}|")]
        if ps:
            per[f"{scaf}|{ag}"] = {"monitors": len(ps), "cue_rate": round(1 - ps[0]["n_cue_free"] / ps[0]["n_attack"], 3),
                                   "mean_auroc_all": round(float(np.mean([p["auroc_all"] for p in ps])), 3),
                                   "mean_auroc_cue_free": None if any(p["auroc_cue_free"] is None for p in ps)
                                   else round(float(np.mean([p["auroc_cue_free"] for p in ps])), 3)}
res["per_attacker"] = per
outp.write_text(json.dumps(res, indent=1, default=float) + "\n")
print(json.dumps({"summary": res["summary"], "per_attacker": per}, indent=1, default=float))
