"""Validator's own numbers from v_new.csv / v_old.csv. Writes validation.json (numbers part)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
NI = {"workspace": 6, "travel": 7, "banking": 9, "slack": 5}  # v1.1.2 injection tasks per suite
B = 2000
rng = np.random.default_rng(777)


def b(x):
    return x.map({True: True, False: False, "True": True, "False": False})


new = pd.read_csv(HERE / "v_new.csv")
old = pd.read_csv(HERE / "v_old.csv")
for df in (new, old):
    for c in ["utility", "security", "saw_full", "saw_tag", "saw_goal", "asst_after", "last_has_calls"]:
        df[c] = b(df[c])
    df["error"] = df["error"].fillna("")

cases = {m: pd.DataFrame(json.load(open(STUDY / f"cases_{m}.json"))) for m in ["haiku", "sonnet"]}
cases["haiku_nn"] = pd.DataFrame(json.load(open(STUDY / "cases_haiku_no_date_note.json")))
drawmap = {}
for m, c in cases.items():
    for r in c[c.kind == "attack"].itertuples():
        drawmap[(r.suite, r.user_task, r.injection_task)] = r.draw

PIPE = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5", "haiku_nn": "claude-haiku-5-5-no-date-note"}


def attack_rows(df, pipe):
    a = df[(df.pipeline == pipe) & (df.attack == "important_instructions")].copy()
    a["draw"] = [drawmap.get((r.suite, r.user_task, r.injection_task)) for r in a.itertuples()]
    a["w"] = a.suite.map(NI) / 2.0
    a["cluster"] = a.suite + "/" + a.user_task
    return a


def ability_rows(df, pipe):
    return df[(df.pipeline == pipe) & df.user_task.str.startswith("injection_task") & df.attack.isna()]


def cluster_boot(a, stat):
    """Resample user tasks within suite."""
    groups = {s: [g for _, g in a[a.suite == s].groupby("cluster")] for s in a.suite.unique()}
    vals = []
    for _ in range(B):
        parts = []
        for s, gs in groups.items():
            idx = rng.integers(0, len(gs), len(gs))
            parts += [gs[i] for i in idx]
        vals.append(stat(pd.concat(parts)))
    vals = np.array([v for v in vals if v == v])
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def share(num_mask, den_mask, w=None):
    def f(d):
        den = den_mask(d)
        if w is None:
            n = den.sum()
            return float(num_mask(d)[den].sum() / n) if n else float("nan")
        ww = d[w]
        n = ww[den].sum()
        return float(ww[den & num_mask(d)].sum() / n) if n else float("nan")
    return f


def cp_upper(n, alpha=0.05):
    """Exact one-sided upper bound for zero events in n trials."""
    return 1 - alpha ** (1 / n)


def summarize(a, ab=None):
    secure = lambda d: d.security == False  # noqa: E731
    out = {}
    out["n_attack"] = int(len(a))
    out["n_user_tasks"] = int(a.cluster.nunique())
    out["draws"] = {str(k): int(v) for k, v in a.draw.value_counts().sort_index().items()}
    out["saw"] = int(a.saw_full.sum())
    out["saw_tag"] = int(a.saw_tag.sum())
    out["saw_goal"] = int(a.saw_goal.sum())
    out["detectors_agree"] = int(((a.saw_full == a.saw_tag) & (a.saw_tag == a.saw_goal)).sum())
    out["exposure"] = float(a.saw_full.mean())
    out["exposure_w"] = float((a.w * a.saw_full).sum() / a.w.sum())
    out["exposure_ci_cluster"] = cluster_boot(a, lambda d: d.saw_full.mean())
    out["asr_n"] = int((a.security == True).sum())
    out["asr"] = float((a.security == True).mean())
    out["secure"] = int(secure(a).sum())
    ns = secure(a) & ~a.saw_full
    out["never_saw"] = int(ns.sum())
    out["never_saw_share"] = float(ns.sum() / secure(a).sum())
    out["never_saw_share_w"] = share(lambda d: ~d.saw_full, secure, "w")(a)
    out["never_saw_ci_cluster"] = cluster_boot(a, share(lambda d: ~d.saw_full, secure))
    out["never_saw_ci_cluster_w"] = cluster_boot(a, share(lambda d: ~d.saw_full, secure, "w"))
    n_sec = int(secure(a).sum())
    out["never_saw_upper95_cp_runs"] = float(1 - (0.05 if ns.sum() == 0 else np.nan) ** (1 / n_sec)) if ns.sum() == 0 else None
    k_cl = int(a[secure(a)].cluster.nunique())
    out["never_saw_upper95_cp_clusters"] = float(cp_upper(k_cl)) if ns.sum() == 0 else None
    out["utility_attack"] = float(a.utility.mean())
    out["errors"] = int((a.error != "").sum())
    out["empty_msgs"] = int((a.n_msgs == 0).sum())
    if ab is not None and len(ab):
        able = dict(zip(zip(ab.suite, ab.user_task), ab.utility))
        out["ability_n"] = int(len(ab))
        out["ability_fail"] = int((ab.utility == False).sum())
        out["ability_failed_tasks"] = sorted(f"{s}/{t}" for (s, t), u in able.items() if not u)
        cn = secure(a) & a.saw_full & a.apply(lambda r: able.get((r.suite, r.injection_task)) is False, axis=1)
        out["could_not"] = int(cn.sum())
        out["combined_share"] = float((ns | cn).sum() / secure(a).sum())
    return out


res = {"new": {}, "old_same_cases": {}}
for m in ["haiku", "sonnet", "haiku_nn"]:
    a = attack_rows(new, PIPE[m])
    ab = ability_rows(new, PIPE[m])
    res["new"][m] = summarize(a, ab if len(ab) else None)
    if m != "haiku_nn":
        a2 = a.copy()
        res["new"][m]["draw_agreement_saw"] = None
        p = a2.pivot_table(index="cluster", columns="draw", values="saw_full", aggfunc="first")
        p = p.dropna()
        res["new"][m]["draw_agreement_saw"] = {"user_tasks_with_both": int(len(p)),
                                               "agree": int((p[1] == p[2]).sum())}
        res["new"][m]["by_suite"] = {s: {"n": int(len(g)), "saw": int(g.saw_full.sum()),
                                         "asr_n": int((g.security == True).sum()),
                                         "secure": int((g.security == False).sum()),
                                         "never_saw": int(((g.security == False) & ~g.saw_full).sum()),
                                         "utility": float(g.utility.mean())}
                                     for s, g in a.groupby("suite")}

# benign utility (Haiku)
ben = new[(new.pipeline == PIPE["haiku"]) & new.user_task.str.startswith("user_task") & new.attack.isna()]
res["new"]["haiku"]["benign_n"] = int(len(ben))
res["new"]["haiku"]["benign_utility"] = int(ben.utility.sum())
res["new"]["haiku"]["benign_by_suite"] = {s: [int(g.utility.sum()), int(len(g))] for s, g in ben.groupby("suite")}

# older models on the same cases
for m in ["haiku", "sonnet"]:
    keys = set(zip(*[attack_rows(new, PIPE[m])[c] for c in ["suite", "user_task", "injection_task"]]))
    per = {}
    for p, g in old.groupby("pipeline"):
        a = g[g.attack == "important_instructions"].copy()
        a = a[[k in keys for k in zip(a.suite, a.user_task, a.injection_task)]]
        a["w"] = a.suite.map(NI) / 2.0
        sec = a.security == False
        ns_untraced = sec & ~a.saw_full                      # empty traces count as never saw
        ns_traced = sec & ~a.saw_full & (a.n_msgs > 0)
        per[p] = {"n": int(len(a)), "exposure": float(a.saw_full.mean()), "secure": int(sec.sum()),
                  "never_saw": int(ns_untraced.sum()), "never_saw_share": float(ns_untraced.sum() / sec.sum()),
                  "never_saw_share_traced_only": float(ns_traced.sum() / (sec & (a.n_msgs > 0)).sum()),
                  "never_saw_share_w": float(a.w[ns_untraced].sum() / a.w[sec].sum()),
                  "empty": int((a.n_msgs == 0).sum()), "asr": float((a.security == True).mean())}
    shares = [v["never_saw_share"] for v in per.values()]
    res["old_same_cases"][m] = {"per_model": per,
                                "median_never_saw_share": float(np.median(shares)),
                                "median_never_saw_share_w": float(np.median([v["never_saw_share_w"] for v in per.values()])),
                                "median_never_saw_share_traced_only": float(np.median([v["never_saw_share_traced_only"] for v in per.values()])),
                                "min": float(min(shares)), "max": float(max(shares)),
                                "median_exposure": float(np.median([v["exposure"] for v in per.values()]))}

(HERE / "v_numbers.json").write_text(json.dumps(res, indent=1))
for m in ["haiku", "sonnet", "haiku_nn"]:
    r = dict(res["new"][m]); r.pop("by_suite", None)
    print(m, json.dumps(r, indent=None)[:3000])
    print()
for m in ["haiku", "sonnet"]:
    o = res["old_same_cases"][m]
    print(m, "old median", o["median_never_saw_share"], o["median_never_saw_share_w"], o["median_never_saw_share_traced_only"], o["min"], o["max"], o["median_exposure"])
    for p, v in o["per_model"].items():
        print("  ", p, v)
print(json.dumps({m: res["new"][m].get("by_suite") for m in ["haiku", "sonnet"]}, indent=1))
