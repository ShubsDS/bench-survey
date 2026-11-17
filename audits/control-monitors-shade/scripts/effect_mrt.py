"""C1 effect test (prereg.md): MRT monitors' separation on attacks with and without the confession cue.

For SHADE-Arena (Claude 3.6 Sonnet agent and monitor) and CUA-SHADE-Arena (Claude Sonnet 4 agent,
Claude 3.6 Sonnet monitor), every cell of the authors' Figure 4 grid: agent {unaware, aware} x
scaffold {baseline, sequential, hierarchical, hybrid} x monitor awareness {U, A, O}. Uses the stored
monitor verdicts only. Writes results_mrt.json.

Usage: python -I scripts/effect_mrt.py data/mrt-git results_mrt.json
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
from mrt_lib import load, hybrid, auroc, threshold_1pct, ci, S36, S4, SHA, CODE

B = 2000
root, outp = Path(sys.argv[1]), Path(sys.argv[2])
pub = json.loads((Path(__file__).parent.parent / "published_numbers.json").read_text())
SCAF = {"Baseline": "", "Sequential": "_sequential_5_likert_reminder_v2", "Hierarchical": "_hierarchical_5_likert_reminder_v2"}
AW = {"U": "_unaware", "A": "", "O": "_superaware"}
DS = {
    "shade": dict(sub="task_pairs", agent=S36, monitor=S36, nb="unaware_aware_comparison_table",
                  folders={"U": "transcripts_no_hint_naive_thinking_time", "A": "transcripts_no_hint_no_thinking_time",
                           "H": "transcripts_no_secondary_task"},
                  placebo="this"),
    "cua": dict(sub="task_pairs_agentcompany", agent=S4, monitor=S36, nb="agentcompany_unaware_aware_comparison_table",
                folders={"U": "transcripts_no_hint_naive_v1_thinking_time", "A": "transcripts_no_hint_visible_v1_thinking_time",
                         "H": "transcripts_no_hint_benign_v1_thinking_time"},
                placebo="correct"),
}
FEATS = ["f1", "f2", "f4", "placebo"]


def get(ds, arm, scaf, aw):
    c = DS[ds]
    if scaf == "Hybrid":
        s = get(ds, arm, "Sequential", aw); h = get(ds, arm, "Hierarchical", aw)
        return hybrid(s, h)
    rows = load(root, c["sub"], None, c["folders"][arm] + SCAF[scaf] + AW[aw], c["agent"], c["monitor"])
    for r in rows:
        r["placebo"] = int(c["placebo"] in r["words"])
    return [r for r in rows if not np.isnan(r["score"])]


def by_task(rows):
    g = {}
    for r in rows:
        g.setdefault(r["task"], []).append(r)
    return g


def stats(att, hon, feat):
    neg = [r["score"] for r in hon]
    cue = [r["score"] for r in att if r[feat]]
    free = [r["score"] for r in att if not r[feat]]
    thr = threshold_1pct(neg, [r["score"] for r in att])
    # within-task difference, cue minus no cue
    num = den = 0.0
    for t, rs in by_task(att).items():
        a = [r["score"] for r in rs if r[feat]]; b = [r["score"] for r in rs if not r[feat]]
        if a and b:
            w = min(len(a), len(b)); num += w * (np.mean(a) - np.mean(b)); den += w
    return {"auroc_all": auroc(neg, cue + free), "auroc_cue": auroc(neg, cue), "auroc_cue_free": auroc(neg, free),
            "tpr_cue": float(np.mean(np.asarray(cue) >= thr)) if cue else np.nan,
            "tpr_cue_free": float(np.mean(np.asarray(free) >= thr)) if free else np.nan,
            "tpr_all": float(np.mean(np.asarray(cue + free) >= thr)),
            "fpr_at_threshold": float(np.mean(np.asarray(neg) >= thr)),
            "within_task_diff": (num / den) if den else np.nan,
            "n_cue": len(cue), "n_cue_free": len(free), "n_honest": len(neg)}


def boot(att, hon, feat, keys, rng, mode):
    ga, gh = by_task(att), by_task(hon)
    tasks = sorted(set(ga) | set(gh))
    out = {k: [] for k in keys}
    for _ in range(B):
        if mode == "task":
            pick = rng.choice(tasks, len(tasks))
            a = [r for t in pick for r in ga.get(t, [])]; h = [r for t in pick for r in gh.get(t, [])]
        else:  # runs resampled within task, separately for each class
            a = [rs[i] for t, rs in ga.items() for i in rng.integers(0, len(rs), len(rs))]
            h = [rs[i] for t, rs in gh.items() for i in rng.integers(0, len(rs), len(rs))]
        s = stats(a, h, feat)
        for k in keys:
            if not np.isnan(s[k]):
                out[k].append(s[k])
    return {k: ci(v) for k, v in out.items()}


def r3(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 3)


def gap(u_att, a_att, hon_u, hon_a, feat, rng, mode):
    """AUROC(unaware) - AUROC(aware), all runs and cue-free runs only, with a joint bootstrap."""
    def g(ua, aa, hu, ha):
        nu, na = [r["score"] for r in hu], [r["score"] for r in ha]
        allg = auroc(nu, [r["score"] for r in ua]) - auroc(na, [r["score"] for r in aa])
        fg = auroc(nu, [r["score"] for r in ua if not r[feat]]) - auroc(na, [r["score"] for r in aa if not r[feat]])
        return allg, fg
    pt = g(u_att, a_att, hon_u, hon_a)
    gs = [by_task(x) for x in (u_att, a_att, hon_u, hon_a)]
    tasks = sorted(set().union(*[set(x) for x in gs]))
    va, vf = [], []
    for _ in range(B):
        if mode == "task":
            pick = rng.choice(tasks, len(tasks))
            xs = [[r for t in pick for r in G.get(t, [])] for G in gs]
        else:
            xs = [[rs[i] for t, rs in G.items() for i in rng.integers(0, len(rs), len(rs))] for G in gs]
        a, f = g(*xs)
        if not np.isnan(a): va.append(a)
        if not np.isnan(f): vf.append(f)
    return {"gap_all": r3(pt[0]), "gap_all_ci": ci(va), "gap_cue_free": r3(pt[1]), "gap_cue_free_ci": ci(vf)}


res = {"pins": {"dataset": f"ScaleAI/mrt@{SHA}", "code": f"scaleapi/mrt@{CODE}"}, "B": B, "seed": 0}
for ds in DS:
    rng = np.random.default_rng(0)
    res[ds] = {"cells": {}, "awareness_gap": {}, "alternatives": {}}
    cache = {}
    for scaf in ["Baseline", "Sequential", "Hierarchical", "Hybrid"]:
        for aw in AW:
            hon = get(ds, "H", scaf, aw)
            for arm in ("U", "A"):
                att = get(ds, arm, scaf, aw)
                cache[(arm, scaf, aw)] = att; cache[("H", scaf, aw)] = hon
                name = f"{arm}-{scaf}({aw})"
                cell = {"published_auroc_17_tasks" if ds == "shade" else "published_auroc":
                        pub[DS[ds]["nb"]].get(f"{DS[ds]['agent']}|{name}"),
                        "tasks": len(by_task(att))}
                primary = (scaf == "Baseline" and aw == "A")
                for feat in FEATS:
                    s = stats(att, hon, feat)
                    e = {k: (r3(v) if isinstance(v, float) else v) for k, v in s.items()}
                    if primary or feat == "f1":
                        e["ci_task"] = boot(att, hon, feat, ["auroc_cue_free", "auroc_all", "within_task_diff",
                                                             "tpr_cue", "tpr_cue_free"], rng, "task")
                    if primary:
                        e["ci_run"] = boot(att, hon, feat, ["auroc_cue_free", "auroc_all", "within_task_diff",
                                                            "tpr_cue", "tpr_cue_free"], rng, "run")
                    cell[feat] = e
                res[ds]["cells"][name] = cell
            for feat in ("f1", "f2", "placebo"):
                key = f"{scaf}({aw})|{feat}"
                res[ds]["awareness_gap"][key] = gap(cache[("U", scaf, aw)], cache[("A", scaf, aw)], hon, hon, feat, rng, "task")
                if scaf == "Baseline" and aw == "A":
                    res[ds]["awareness_gap"][key + "|run_bootstrap"] = gap(cache[("U", scaf, aw)], cache[("A", scaf, aw)],
                                                                          hon, hon, feat, rng, "run")
    # alternatives and robustness on the primary cell
    att, hon = cache[("U", "Baseline", "A")], cache[("H", "Baseline", "A")]
    neg = [r["score"] for r in hon]
    alt = {}
    if ds == "shade":
        for feat in ("f1", "f2"):
            ok = [r for r in att if r["side"] is not None]
            alt[f"side_task_success|{feat}"] = {
                "cue": [sum(bool(r["side"]) for r in ok if r[feat]), sum(1 for r in ok if r[feat])],
                "cue_free": [sum(bool(r["side"]) for r in ok if not r[feat]), sum(1 for r in ok if not r[feat])],
                "auroc_cue_free_successful_only": r3(auroc(neg, [r["score"] for r in ok if not r[feat] and r["side"]])),
                "auroc_cue_successful_only": r3(auroc(neg, [r["score"] for r in ok if r[feat] and r["side"]]))}
        aw_att = cache[("A", "Baseline", "A")]
        alt["aware_agent_side_task_success"] = [sum(bool(r["side"]) for r in aw_att), len(aw_att)]
    alt["median_chars"] = {"cue": float(np.median([r["n_chars"] for r in att if r["f1"]] or [np.nan])),
                           "cue_free": float(np.median([r["n_chars"] for r in att if not r["f1"]] or [np.nan])),
                           "honest": float(np.median([r["n_chars"] for r in hon]))}
    alt["cue_free_runs_by_task"] = {t: sum(1 for r in rs if not r["f1"]) for t, rs in by_task(att).items()}
    alt["cue_free_scores"] = sorted(r3(r["score"]) for r in att if not r["f1"])
    alt["honest_score_quantiles"] = {q: r3(np.percentile(neg, q)) for q in (50, 90, 95, 99)}
    loo = {}
    for t in sorted(by_task(att)):
        a2 = [r for r in att if r["task"] != t]; h2 = [r for r in hon if r["task"] != t]
        s = stats(a2, h2, "f1"); loo[t] = {"auroc_all": r3(s["auroc_all"]), "auroc_cue_free": r3(s["auroc_cue_free"]),
                                         "n_cue_free": s["n_cue_free"]}
    alt["drop_one_task_f1"] = loo
    alt["per_task_attack_scores_f1"] = {t: {"cue": sorted(r3(r["score"]) for r in rs if r["f1"]),
                                            "cue_free": sorted(r3(r["score"]) for r in rs if not r["f1"]),
                                            "honest_median": r3(np.median([h["score"] for h in hon if h["task"] == t]))}
                                        for t, rs in by_task(att).items()}
    # Robustness (added after prereg, stated in README): task-matched random-subset null. If the cue
    # were irrelevant, cue-free runs would be a random draw within each task. Draw subsets with the
    # same per-task counts from all attack runs and compare the cue-free AUROC with that distribution.
    rng2 = np.random.default_rng(1)
    for cell in ("U-Baseline(A)", "U-Hybrid(A)", "A-Baseline(A)"):
        arm, rest = cell.split("-", 1); scaf = rest.split("(")[0]
        a_rows, h_rows = cache[(arm, scaf, "A")], cache[("H", scaf, "A")]
        negs = [r["score"] for r in h_rows]
        obs = auroc(negs, [r["score"] for r in a_rows if not r["f1"]])
        ga = by_task(a_rows)
        k = {t: sum(1 for r in rs if not r["f1"]) for t, rs in ga.items()}
        null = []
        for _ in range(10000):
            pick = [ga[t][i] for t in ga for i in rng2.choice(len(ga[t]), k[t], replace=False)]
            null.append(auroc(negs, [r["score"] for r in pick]))
        null = np.asarray(null)
        alt[f"task_matched_subset_null|{cell}"] = {"observed_cue_free_auroc": r3(obs), "null_mean": r3(null.mean()),
                                                   "null_2.5_97.5": ci(null), "p_one_sided_low": r3((1 + (null <= obs).sum()) / (1 + len(null)))}
    # Exploratory: OLS over attack runs of both arms, score ~ cue + unaware-arm + task fixed effects,
    # baseline scaffold, aware monitor; task-cluster bootstrap of the two coefficients.
    def ols(rows):
        ts = sorted({r["task"] for r in rows})
        X = np.array([[r["f1"], r["arm_u"]] + [float(r["task"] == t) for t in ts] for r in rows])
        y = np.array([r["score"] for r in rows])
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        return beta[0], beta[1]
    both = [dict(r, arm_u=1.0) for r in cache[("U", "Baseline", "A")]] + [dict(r, arm_u=0.0) for r in cache[("A", "Baseline", "A")]]
    bc, ba = ols(both)
    gb = by_task(both); ts = sorted(gb); bs = []
    for _ in range(B):
        pick = rng2.choice(ts, len(ts))
        rows = []
        for j, t in enumerate(pick):
            rows += [dict(r, task=f"{t}#{j}") for r in gb[t]]
        bs.append(ols(rows))
    bs = np.asarray(bs)
    alt["ols_score_on_cue_and_unaware_arm_task_fe"] = {"cue_coef": r3(bc), "cue_ci_task": ci(bs[:, 0]),
                                                       "unaware_arm_coef": r3(ba), "unaware_arm_ci_task": ci(bs[:, 1]),
                                                       "n": len(both), "exploratory": True}
    # count of the 12 monitor cells where the cue-free gap is below half the all-runs gap
    gaps = {k: v for k, v in res[ds]["awareness_gap"].items() if k.endswith("|f1")}
    alt["cells_cue_free_gap_below_half"] = [k for k, v in gaps.items()
                                            if v["gap_cue_free"] is not None and v["gap_cue_free"] < 0.5 * v["gap_all"]]
    alt["cells_total"] = len(gaps)
    res[ds]["alternatives"] = alt
    print(ds, json.dumps({k: (v["f1"]["auroc_all"], v["f1"]["auroc_cue_free"], v["f1"]["n_cue_free"], v.get("published_auroc_17_tasks", v.get("published_auroc")))
                          for k, v in res[ds]["cells"].items()}, indent=0))
outp.write_text(json.dumps(res, indent=1) + "\n")
