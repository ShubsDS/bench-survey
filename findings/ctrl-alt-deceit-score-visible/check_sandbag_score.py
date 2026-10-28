"""Does the final score alone detect sandbagging as well as CTRL-ALT-DECEIT's monitors?

Ward, van der Weij et al., "CTRL-ALT-DECEIT" (arXiv 2511.09904v2), Figure 8: a Claude 3.7 Sonnet
monitor reads the AIDE best path, the task description and the agent's score on the test set, and
separates 134 Sandbagging runs from 219 Regular runs with pooled AUROC 0.60 (general prompt) and
0.90 (sandbagging-specific prompt). The released per-run table holds, for each run, the task, the
test score and each monitor's suspicion score.

This script scores the same runs with rules that read only the task and the test score:
  - leaderboard percentile: the share of the task's public Kaggle leaderboard (MLE-bench copy)
    at or below the score; lower is more suspicious. Uses only what the monitor is shown plus the
    public leaderboard.
  - medal tier: the score's tier (below 10th pct, 10th, 25th, 40th, median, bronze, silver, gold)
    from the repo's own threshold file; lower is more suspicious.
  - below own Regular runs: share of the task's Regular runs (excluding the run itself) that
    score better. Needs a reference of honest runs on the same task, which the monitor lacks.
  - logistic regression on the two monitor-available features, GroupKFold by task.
It reports AUROC with task-clustered bootstrap intervals, a within-task label-permutation null,
the paired difference against each monitor, and the same numbers on the 13 tasks that have
Sandbagging runs. It reads CSVs only and runs no downloaded code.

Usage:
    python -I check_sandbag_score.py [--cache DIR] [--out sandbag_score_checks.json]
"""
import argparse, json, urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

REPO = "0a12070c41ec06b81712f277590afbbed6ed6d6c"  # TeunvdWeij/ctrl-alt-deceit
MLEB = "d6731c308a4e9ab464abfbdfaa625ef7a9cd3134"  # openai/mle-bench, as resolved in the repo's poetry.lock
RAW = f"https://raw.githubusercontent.com/TeunvdWeij/ctrl-alt-deceit/{REPO}/"
LB = f"https://media.githubusercontent.com/media/openai/mle-bench/{MLEB}/mlebench/competitions/{{}}/leaderboard.csv"
MONITORS = {
    "general (paper 0.60)": "default_system",
    "sandbagging-specific (paper 0.90)": "teun_sandbagging_specific_monitor_v1",
    "general with sandbagging hint (not in paper figure)": "sandbagging_hint_full_trajectory",
}
TIERS = ["percentile_10th", "percentile_25th", "percentile_40th", "median", "bronze", "silver", "gold"]
B, PERM = 2000, 1000


def fetch(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with urllib.request.urlopen(url, timeout=300) as r:
            path.write_bytes(r.read())
    return path


def load(cache):
    frames = {}
    for name, stem in MONITORS.items():
        p = fetch(RAW + f"data/monitor_data_for_plotting/{stem}.csv", cache / f"{stem}.csv")
        d = pd.read_csv(p)
        src = d.log_location.str.split("/").str[:2].str.join("/")
        d["key"] = src + "|" + d.sample_id + "|" + d.sample_epoch.astype(str)
        frames[name] = d.set_index("key")
    base = frames[next(iter(MONITORS))][["mode", "target", "task", "task_score"]].copy()
    for name, d in frames.items():
        assert set(d.index) == set(base.index)
        assert np.allclose(d.task_score.reindex(base.index), base.task_score)
        base[name] = d.monitor_score.reindex(base.index)
    base["y"] = (base["mode"] == "sandbagging").astype(int)
    thr = json.loads(fetch(RAW + "data/medal_thresholds_results.json", cache / "medal_thresholds_results.json").read_text())
    thr = {t["competition"]: t for t in thr}
    return base.reset_index(), thr


def add_features(df, thr, cache):
    pct, tier = [], []
    for task, s in zip(df.task, df.task_score):
        t = thr[task]
        lower = t["lower_is_better"]
        lb = pd.read_csv(fetch(LB.format(task), cache / "leaderboards" / f"{task}.csv"))
        v = np.sort(pd.to_numeric(lb["score"], errors="coerce").dropna().values)
        # same rule as mlebench_subversion/utils/leaderboard_percentage.py
        n = (v.size - np.searchsorted(v, s, side="left")) if lower else np.searchsorted(v, s, side="right")
        pct.append(100 * n / v.size)
        k = 0
        for i, name in enumerate(TIERS):
            th = float(t[f"{name}_threshold"])
            if (s <= th) if lower else (s >= th):
                k = i + 1
        tier.append(k)
    df["lb_percentile"] = pct
    df["medal_tier"] = tier
    # below own Regular runs (leave the run itself out)
    below = []
    for i, r in df.iterrows():
        reg = df[(df.task == r.task) & (df["mode"] == "regular") & (df.index != i)].task_score.values
        if reg.size == 0:
            below.append(np.nan)
            continue
        lower = thr[r.task]["lower_is_better"]
        better = (reg < r.task_score) if lower else (reg > r.task_score)
        ties = reg == r.task_score
        below.append((better.sum() + 0.5 * ties.sum()) / reg.size)
    df["share_regular_better"] = below
    return df


def auc(y, s):
    return float(roc_auc_score(y, s))


def cluster_ci(df, col, other=None, seed=0):
    rng = np.random.default_rng(seed)
    tasks = df.task.unique()
    groups = {t: df.index[df.task == t].values for t in tasks}
    out = []
    for _ in range(B):
        idx = np.concatenate([groups[t] for t in rng.choice(tasks, tasks.size)])
        d = df.loc[idx]
        if d.y.nunique() < 2:
            continue
        a = auc(d.y, d[col])
        out.append(a - auc(d.y, d[other]) if other else a)
    return [round(float(np.percentile(out, 2.5)), 3), round(float(np.percentile(out, 97.5)), 3)]


def perm_null(df, col, seed=0):
    rng = np.random.default_rng(seed)
    y = df.y.values.copy()
    groups = [np.where(df.task.values == t)[0] for t in df.task.unique()]
    vals = []
    for _ in range(PERM):
        yp = y.copy()
        for g in groups:
            yp[g] = rng.permutation(yp[g])
        vals.append(auc(yp, df[col].values))
    return {"mean": round(float(np.mean(vals)), 3), "p95": round(float(np.percentile(vals, 95)), 3)}


def within_task(df, col):
    rows = []
    for t, d in df.groupby("task"):
        if d.y.nunique() == 2:
            rows.append((t, auc(d.y, d[col]), int(d.y.sum()), int((1 - d.y).sum())))
    w = np.array([r[2] for r in rows], float)
    a = np.array([r[1] for r in rows])
    return {"tasks": len(rows), "mean": round(float(a.mean()), 3),
            "weighted_by_sandbag_runs": round(float((a * w).sum() / w.sum()), 3)}


def logreg_groupkfold(df):
    X = df[["lb_percentile", "medal_tier"]].values
    p = np.zeros(len(df))
    for tr, te in GroupKFold(n_splits=5).split(X, df.y, df.task):
        m = LogisticRegression(max_iter=2000).fit(X[tr], df.y.values[tr])
        p[te] = m.predict_proba(X[te])[:, 1]
    return p


def block(df, label):
    res = {"runs": int(len(df)), "sandbagging": int(df.y.sum()), "regular": int((1 - df.y).sum()),
           "tasks": int(df.task.nunique()), "detectors": {}}
    cols = {m: m for m in MONITORS}
    cols.update({
        "score only: low leaderboard percentile": "neg_pct",
        "score only: low medal tier (repo thresholds)": "neg_tier",
        "score only: logistic regression on percentile and tier, GroupKFold by task": "lr",
        "score vs own Regular runs (needs honest reference)": "share_regular_better",
    })
    for name, col in cols.items():
        d = df.dropna(subset=[col])
        e = {"auroc": round(auc(d.y, d[col]), 3), "ci95_task_bootstrap": cluster_ci(d, col),
             "within_task": within_task(d, col)}
        if name not in MONITORS:
            e["null_within_task_permutation"] = perm_null(d, col)
            e["minus_monitor"] = {m: {"diff": round(e["auroc"] - auc(d.y, d[m]), 3),
                                      "ci95": cluster_ci(d, col, other=m)} for m in MONITORS}
        res["detectors"][name] = e
    # does the monitor's suspicion follow the score? Spearman within each class
    res["spearman_monitor_vs_lb_percentile"] = {
        m: {cls: round(float(spearmanr(df[df["mode"] == cls][m], df[df["mode"] == cls].lb_percentile)[0]), 3)
            for cls in ["regular", "sandbagging"]} for m in MONITORS}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="sandbag_score_checks.json")
    a = ap.parse_args()
    cache = Path(a.cache)
    df, thr = load(cache)
    df = add_features(df, thr, cache)
    df["neg_pct"] = -df.lb_percentile
    df["neg_tier"] = -df.medal_tier
    df["lr"] = logreg_groupkfold(df)
    sb_tasks = set(df[df.y == 1].task)
    out = {
        "pins": {"ctrl-alt-deceit": REPO, "mle-bench": MLEB, "paper": "arXiv 2511.09904v2, Figure 8"},
        "reproduced_paper_auroc": {m: round(auc(df.y, df[m]), 3) for m in MONITORS},
        "tasks_with_regular_runs_only": sorted(set(df.task) - sb_tasks),
        "all_runs_as_in_paper": block(df, "all"),
        "only_tasks_with_sandbagging_runs": block(df[df.task.isin(sb_tasks)].reset_index(drop=True), "13"),
        "sandbagging_runs_scoring_at_or_above_own_regular_median": int(
            (df[df.y == 1].share_regular_better <= 0.5).sum()),
    }
    Path(a.out).write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
