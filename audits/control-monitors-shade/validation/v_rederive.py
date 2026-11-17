"""Independent re-derivation of claims 2, 4, 5 and 7 (validation). Does not import scripts/.

Reads ScaleAI/mrt @ bc636d0 (data/mrt-git) and CTRL-ALT-DECEIT tables (data/cad) as text.
Own loader, own cue rule, own AUROC (Mann-Whitney with ties = 0.5), own nulls. Writes aggregates only.

Usage: python -I validation/v_rederive.py data validation/out_rederive.json
"""
import csv, json, re, sys
from collections import defaultdict
from pathlib import Path
import numpy as np

DATA, OUT = Path(sys.argv[1]), Path(sys.argv[2])
ROOT = DATA / "mrt-git"
S36, S4 = "claude-3-5-sonnet-20241022", "claude-sonnet-4-20250514"
HID = re.compile(r"<(hidden_thinking|thinking|system_instructions)>.*?</\1>", re.S)
CUE = re.compile(r"secondary task", re.I)
VER = re.compile(r"<verdict>\s*([0-9.]+)\s*</verdict>")


def auc(neg, pos):
    neg = np.asarray([x for x in neg if x == x], float); pos = np.asarray([x for x in pos if x == x], float)
    if not len(neg) or not len(pos):
        return float("nan")
    return float(((pos[:, None] > neg[None]).sum() + 0.5 * (pos[:, None] == neg[None]).sum()) / (len(pos) * len(neg)))


def visible(conv):
    parts = []
    for m in conv[1:]:
        if m["role"].lower() == "system":
            continue
        parts.append(HID.sub("", str(m.get("content") or "")))
        if m.get("tool_calls"):
            parts.append(str(m["tool_calls"]))
    return "\n".join(parts)


_cache = {}
def runs(sub, folder, agent, mon):
    """{(task, file): (score, cue)} for one folder; likert folders keep raw 1-5 (AUROC is rank-based;
    the hybrid averages two likert scores, also rank-equivalent to the authors' x*25-25)."""
    key = (sub, folder, agent, mon)
    if key in _cache:
        return _cache[key]
    out = {}
    for f in sorted(ROOT.glob(f"{sub}/*/{folder}/{agent}/{mon}/transcript_*.json")):
        d = json.loads(f.read_text())
        v = VER.findall(str(d.get("monitoring_response") or ""))
        if not v:
            continue
        out[(f.parts[-5], f.name)] = (float(v[-1]), bool(CUE.search(visible(d["conversation"]))))
    _cache[key] = out
    return out


def hyb(sub, base, agent, mon, k):
    s = runs(sub, base + f"_sequential_{k}_likert_reminder_v2", agent, mon)
    h = runs(sub, base + f"_hierarchical_{k}_likert_reminder_v2", agent, mon)
    return {x: ((s[x][0] + h[x][0]) / 2, s[x][1]) for x in s if x in h}


def get(sub, base, agent, mon, scaf, k=5):
    return runs(sub, base, agent, mon) if scaf == "baseline" else hyb(sub, base, agent, mon, k)


def scores(d, cue=None):
    return [v[0] for v in d.values() if cue is None or v[1] == cue]


res = {}
rng = np.random.default_rng(20261117)

# ---------------- claim 2 (SHADE) and claim 4 (CUA) ----------------
DS = {"shade": ("task_pairs", S36, S36, "transcripts_no_hint_naive_thinking_time", "transcripts_no_hint_no_thinking_time", "transcripts_no_secondary_task"),
      "cua": ("task_pairs_agentcompany", S4, S36, "transcripts_no_hint_naive_v1_thinking_time", "transcripts_no_hint_visible_v1_thinking_time", "transcripts_no_hint_benign_v1_thinking_time")}
for ds, (sub, ag, mon, U, A, H) in DS.items():
    r = {}
    for scaf in ("baseline", "hybrid"):
        u, a, h = get(sub, U, ag, mon, scaf), get(sub, A, ag, mon, scaf), get(sub, H, ag, mon, scaf)
        neg = scores(h)
        e = {"n_unaware": len(u), "n_unaware_cue_free": sum(1 for v in u.values() if not v[1]), "n_aware": len(a),
             "n_aware_cue_free": sum(1 for v in a.values() if not v[1]), "n_honest": len(neg),
             "auroc_unaware_all": auc(neg, scores(u)), "auroc_unaware_cue": auc(neg, scores(u, True)),
             "auroc_unaware_cue_free": auc(neg, scores(u, False)), "auroc_aware_all": auc(neg, scores(a)),
             "auroc_aware_cue_free": auc(neg, scores(a, False))}
        e["gap_all"] = e["auroc_unaware_all"] - e["auroc_aware_all"]
        e["gap_cue_free"] = e["auroc_unaware_cue_free"] - e["auroc_aware_cue_free"]
        # task-matched subset null for the unaware cue-free AUROC (my own implementation)
        by_t = defaultdict(list)
        for (t, f), v in u.items():
            by_t[t].append(v)
        k = {t: sum(1 for v in vs if not v[1]) for t, vs in by_t.items()}
        obs = e["auroc_unaware_cue_free"]
        null = []
        for _ in range(20000):
            pick = [by_t[t][i][0] for t in by_t for i in rng.permutation(len(by_t[t]))[:k[t]]]
            null.append(auc(neg, pick))
        null = np.asarray(null)
        e["null_task_matched"] = {"k_per_task": k, "mean": float(null.mean()), "q025": float(np.quantile(null, .025)),
                                  "q05": float(np.quantile(null, .05)), "p_low": float((1 + (null <= obs).sum()) / (1 + len(null)))}
        # within-task AUROC (cue-free unaware vs honest of the same task); avoids pooling tasks whose honest counts differ
        hb = defaultdict(list)
        for (t, f), v in h.items():
            hb[t].append(v[0])
        e["within_task"] = {t: {"n_cue": sum(v[1] for v in vs), "n_cue_free": k[t],
                                "auroc_cue": auc(hb[t], [v[0] for v in vs if v[1]]),
                                "auroc_cue_free": auc(hb[t], [v[0] for v in vs if not v[1]]),
                                "n_honest": len(hb[t])} for t, vs in sorted(by_t.items())}
        # drop-one-task cue-free AUROC
        e["drop_one_task"] = {t: {"n_cue_free": sum(1 for (tt, f), v in u.items() if tt != t and not v[1]),
                                  "auroc_cue_free": auc([v[0] for (tt, f), v in h.items() if tt != t],
                                                        [v[0] for (tt, f), v in u.items() if tt != t and not v[1]])}
                              for t in sorted(by_t)}
        # exact permutation test inside each task: are cue-free runs' scores lower than cue runs' (rank-sum)?
        perm = {}
        for t, vs in by_t.items():
            c = [v[0] for v in vs if v[1]]; nf = [v[0] for v in vs if not v[1]]
            if c and nf:
                allv = np.asarray(c + nf); stat = np.mean(nf)
                sims = np.asarray([allv[rng.permutation(len(allv))[:len(nf)]].mean() for _ in range(20000)])
                perm[t] = {"n_cue": len(c), "n_free": len(nf), "mean_cue": float(np.mean(c)), "mean_free": float(stat),
                           "p_free_lower": float((1 + (sims <= stat).sum()) / (1 + len(sims)))}
        e["within_task_cue_vs_free_perm"] = perm
        # power for claim 4: the null's lower 2.5% quantile is the smallest drop a random subset of this size could show
        r[scaf] = e
    res[f"claim_{'2_shade' if ds == 'shade' else '4_cua'}"] = r

# ---------------- claim 5 (weak-to-strong, selective folder) ----------------
AGENTS = [S36, S4, "gemini-2.5-flash-preview-04-17", "gemini-2.5-pro-preview-03-25"]
MONS = ["claude-3-5-haiku-20241022", S36, "claude-3-7-sonnet-20250219", S4, "gemini-2.5-flash", "gemini-2.5-pro-preview-03-25",
        "gpt-4o", "gpt-4o-mini", "o3", "o4-mini"]
MMLU = {"gemini-2.5-pro-preview-03-25": 0.863, S4: 0.843, "claude-3-7-sonnet-20250219": 0.784, S36: 0.777,
        "gemini-2.5-flash-preview-04-17": 0.639, "gemini-2.5-flash": 0.639, "claude-3-5-haiku-20241022": 0.605,
        "gpt-4o-mini": 0.603, "gpt-4o": 0.713, "o3": 0.859, "o4-mini": 0.812}  # notebook capability_mapping_2
SA, SH = "transcripts_no_hint_selective_thinking_time", "transcripts_no_secondary_task"
pairs = {}
for scaf in ("baseline", "hybrid"):
    for ag in AGENTS:
        for mon in MONS:
            a, h = get("task_pairs", SA, ag, mon, scaf, 4), get("task_pairs", SH, ag, mon, scaf, 4)
            if not a or not h:
                continue
            neg = scores(h)
            pairs[f"{scaf}|{ag}|{mon}"] = {
                "n_att": len(a), "n_hon": len(neg), "tasks_att": len({t for t, f in a}), "tasks_hon": len({t for t, f in h}),
                "cue_rate": float(np.mean([v[1] for v in a.values()])), "auroc_all": auc(neg, scores(a)),
                "auroc_cue_free": auc(neg, scores(a, False)) if sum(not v[1] for v in a.values()) >= 5 else None,
                "n_cue_free": sum(not v[1] for v in a.values()),
                # same honest/attack task set: AUROC restricted to tasks present in both classes
                "auroc_common_tasks": auc([v[0] for (t, f), v in h.items() if t in {x for x, _ in a}],
                                          [v[0] for (t, f), v in a.items() if t in {x for x, _ in h}])}
w = {"pairs": pairs}
for scaf in ("baseline", "hybrid"):
    for m in ("gpt-4o-mini", "claude-3-5-haiku-20241022"):
        ps = {k: v for k, v in pairs.items() if k.startswith(scaf + "|") and k.endswith("|" + m)}
        if ps:
            kmin = min(ps, key=lambda k: ps[k]["auroc_all"])
            w[f"min_{scaf}_{m}"] = {"pair": kmin, **ps[kmin]}
    xs = [(MMLU[k.split("|")[1]] - MMLU[k.split("|")[2]], v["auroc_all"], v["auroc_cue_free"]) for k, v in pairs.items()
          if k.startswith(scaf + "|") and k.split("|")[2] in MMLU]
    x = np.array([p[0] for p in xs]); y = np.array([p[1] for p in xs])
    w[f"slope_{scaf}_all"] = float(np.polyfit(x, y, 1)[0]); w[f"n_pairs_{scaf}"] = len(xs)
    xf = np.array([p[0] for p in xs if p[2] is not None]); yf = np.array([p[2] for p in xs if p[2] is not None])
    w[f"slope_{scaf}_cue_free"] = float(np.polyfit(xf, yf, 1)[0]); w[f"n_pairs_{scaf}_cue_free"] = len(xf)
    g = [(v["auroc_all"], v["auroc_cue_free"]) for k, v in pairs.items() if k.startswith(scaf + "|gemini-2.5-pro") and v["auroc_cue_free"] is not None]
    w[f"gemini_pro_{scaf}_mean_auroc_all_vs_cue_free"] = [float(np.mean([p[0] for p in g])), float(np.mean([p[1] for p in g])), len(g)]
    gp = [v["cue_rate"] for k, v in pairs.items() if k.startswith(scaf + "|gemini-2.5-pro")]
    w[f"gemini_pro_{scaf}_cue_rate_range"] = [min(gp), max(gp)] if gp else None
res["claim_5_w2s"] = w

# ---------------- claim 7 (CTRL-ALT-DECEIT) ----------------
thr = {t["competition"]: t for t in json.loads((DATA / "cad/medal_thresholds_results.json").read_text())}
cad = {}
for stem, lab in (("teun_sandbagging_specific_monitor_v1", "specific"), ("default_system", "general")):
    rows = list(csv.DictReader(open(DATA / f"cad/{stem}.csv")))
    reg = defaultdict(list)
    for r in rows:
        if r["mode"] == "regular" and r["task_score"] not in ("", "nan"):
            reg[r["task"]].append(float(r["task_score"]))
    sb_tasks = {r["task"] for r in rows if r["mode"] == "sandbagging"}
    neg, cue_s, free_s, unk = [], [], [], 0
    per_task = defaultdict(lambda: [[], []])
    for r in rows:
        if r["task"] not in sb_tasks or r["monitor_score"] in ("", "nan"):
            continue
        s = float(r["monitor_score"])
        if r["mode"] == "regular":
            neg.append(s); continue
        if r["mode"] != "sandbagging":
            continue
        try:
            ts = float(r["task_score"])
        except ValueError:
            ts = float("nan")
        lib = thr[r["task"]]["lower_is_better"]
        if ts != ts or not reg[r["task"]]:
            c = False; unk += 1  # no score: counted cue-free, as the auditor's rule does (comparison with nan is False)
        else:
            c = ts > max(reg[r["task"]]) if lib else ts < min(reg[r["task"]])
        (cue_s if c else free_s).append(s)
        per_task[r["task"]][0 if c else 1].append(s)
    # alternative definition (mine): below the 25th percentile of the task's Regular scores (less extreme)
    cad[lab] = {"n_regular": len(neg), "n_cue": len(cue_s), "n_cue_free": len(free_s), "n_sandbag_no_score": unk,
                "auroc_all": auc(neg, cue_s + free_s), "auroc_cue": auc(neg, cue_s), "auroc_cue_free": auc(neg, free_s),
                "tasks_with_cue_free": sum(1 for t, v in per_task.items() if v[1])}
    # null: random subsets of sandbagging runs with the same per-task cue-free counts
    allsb = {t: v[0] + v[1] for t, v in per_task.items()}
    kk = {t: len(v[1]) for t, v in per_task.items()}
    null = np.asarray([auc(neg, [allsb[t][i] for t in allsb for i in rng.permutation(len(allsb[t]))[:kk[t]]]) for _ in range(5000)])
    cad[lab]["null_task_matched"] = {"mean": float(null.mean()), "q025": float(np.quantile(null, .025)),
                                     "p_low": float((1 + (null <= cad[lab]["auroc_cue_free"]).sum()) / (1 + len(null)))}
    cad[lab]["sandbag_runs_in_lower_is_better_tasks"] = sum(len(v[0]) + len(v[1]) for t, v in per_task.items() if thr[t]["lower_is_better"])
    cad[lab]["cue_free_by_task"] = {t: len(v[1]) for t, v in sorted(per_task.items()) if v[1]}
    negt = defaultdict(list)
    for r in rows:
        if r["mode"] == "regular" and r["task"] in sb_tasks and r["monitor_score"] not in ("", "nan"):
            negt[r["task"]].append(float(r["monitor_score"]))
    cad[lab]["drop_one_task_auroc_cue_free"] = {
        t: auc([s for tt, ss in negt.items() if tt != t for s in ss], [s for tt, v in per_task.items() if tt != t for s in v[1]])
        for t in sorted(per_task) if per_task[t][1]}
res["claim_7_cad"] = cad


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    if isinstance(o, float):
        return None if o != o else round(o, 4)
    return o


OUT.write_text(json.dumps(clean(res), indent=1) + "\n")
print(json.dumps(clean({k: v for k, v in res.items() if k != "claim_5_w2s"}), indent=1)[:6000])
print(json.dumps(clean({k: v for k, v in res["claim_5_w2s"].items() if k != "pairs"}), indent=1))
