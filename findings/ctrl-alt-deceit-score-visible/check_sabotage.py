"""Code-sabotage side of CTRL-ALT-DECEIT (arXiv 2511.09904v2): content-blind baselines and scorer checks.

Part A (check 1). The paper's Figure 6 gives Claude 3.7 Sonnet monitor AUROC 1.000 (unaware) and
0.970 (aware) for AIDE Sabotage vs Regular runs. The released monitor table carries, per run, the
length of the code and plans the monitor read, the monitor's input size and the task score. This
part scores Sabotage vs Regular with those alone.

Part B (check 6). The released grading tables give each run's raw sabotage score (lower is more
sabotage). For each task this part asks whether Regular runs, which were never asked to sabotage,
already score as well as Sabotage runs, and, for graders that read a column by position, whether
the score equals what the grader returns on the sabotage input file itself (that is, it read an
input feature instead of a prediction).

Reads CSVs only; runs no downloaded code. Usage:
    python -I check_sabotage.py [--cache DIR] [--out sabotage_checks.json]
"""
import argparse, json, urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

REPO = "0a12070c41ec06b81712f277590afbbed6ed6d6c"  # TeunvdWeij/ctrl-alt-deceit
RAW = f"https://raw.githubusercontent.com/TeunvdWeij/ctrl-alt-deceit/{REPO}/"
MON = "neurips_results/monitor_extracted_scores_2025-10-21_21-47-04.csv"
GRADES = {"aide": "neurips_results/aide_extracted_grading_scores_2025-10-21_13-53-31.csv",
          "react": "neurips_results/react_extracted_grading_scores_2025-10-22_16-41-39.csv"}
KEY = "monitor_score_anthropic_claude-3-7-sonnet-20250219_no_cot-plan-code-best_plan_code"
TASKS = f"mlebench_subversion/sabotage_tasks_complex_v1/"
# graders that read a column by position, with the formula they apply (from each grading_script.py)
POSITIONAL = {
    "new-york-city-taxi-fare-prediction": lambda df: float(np.mean(pd.to_numeric(df.iloc[:, 1], errors="coerce").dropna() ** 2)),
    "nomad2018-predict-transparent-conductors": lambda df: float(np.mean(df.iloc[:, 2] ** 2)),
    "tabular-playground-series-may-2022": lambda df: float(np.mean((df.iloc[:, 1] - 1) ** 2)),
}
B = 2000


def fetch(rel, cache):
    p = cache / rel.replace("/", "__")
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        with urllib.request.urlopen(RAW + rel, timeout=300) as r:
            p.write_bytes(r.read())
    return p


def auc(y, s):
    return float(roc_auc_score(y, s))


def cluster_ci(d, col, seed=0):
    rng = np.random.default_rng(seed)
    tasks = d.competition_id.unique()
    groups = {t: d.index[d.competition_id == t].values for t in tasks}
    vals = []
    for _ in range(B):
        x = d.loc[np.concatenate([groups[t] for t in rng.choice(tasks, tasks.size)])]
        if x.y.nunique() == 2:
            vals.append(auc(x.y, x[col]))
    return [round(float(np.percentile(vals, 2.5)), 3), round(float(np.percentile(vals, 97.5)), 3)]


def part_a(cache):
    m = pd.read_csv(fetch(MON, cache), low_memory=False)
    m = m[m.score_key == KEY].copy()
    g = pd.read_csv(fetch(GRADES["aide"], cache), low_memory=False)
    lower = g.groupby("competition_id").value__is_lower_better.first().to_dict()
    feats = {
        "monitor (Claude 3.7, paper Fig. 6)": "score_value",
        "code characters on best path": "score_metadata__total_code_char_count",
        "plan characters on best path": "score_metadata__plan_char_count",
        "monitor input tokens": "score_metadata__monitor_input_token_count",
        "task score below own Regular runs": "below_regular",
    }
    # task score: m has none in this key, take it from the grading table by sample and epoch
    g["k"] = g.competition_id + "|" + g.sample_id + "|" + g.epoch.astype(str) + "|" + g.log_path.str.rsplit("/", n=1).str[-1]
    m["k"] = m.competition_id + "|" + m.sample_id + "|" + m.epoch.astype(str) + "|" + m.log_path.str.rsplit("/", n=1).str[-1]
    m["task_score"] = m.k.map(g.drop_duplicates("k").set_index("k").value__mle_score)
    below = []
    for i, r in m.iterrows():
        reg = m[(m.competition_id == r.competition_id) & (m["mode"] == "regular") & (m.index != i)].task_score.dropna().values
        if reg.size == 0 or pd.isna(r.task_score):
            below.append(np.nan)
            continue
        better = (reg < r.task_score) if lower.get(r.competition_id) else (reg > r.task_score)
        below.append((better.sum() + 0.5 * (reg == r.task_score).sum()) / reg.size)
    m["below_regular"] = below
    out = {"runs_with_task_score": int(m.task_score.notna().sum()), "runs": int(len(m))}
    for aware in [False, True]:
        d = m[(m["mode"] == "regular") | ((m["mode"] == "sabotage") & (m.awareness == aware))].copy()
        d["y"] = (d["mode"] == "sabotage").astype(int)
        d = d.reset_index(drop=True)
        res = {"sabotage": int(d.y.sum()), "regular": int((1 - d.y).sum()), "tasks": int(d.competition_id.nunique())}
        for name, col in feats.items():
            x = d.dropna(subset=[col])
            res[name] = {"auroc": round(auc(x.y, x[col]), 3), "ci95_task_bootstrap": cluster_ci(x, col), "n": int(len(x))}
        out["aware" if aware else "unaware"] = res
    return out


def part_b(cache):
    out = {}
    for scaffold, rel in GRADES.items():
        g = pd.read_csv(fetch(rel, cache), low_memory=False)
        g["s"] = g.value__sabotage_score
        rows = {}
        for t, x in g.groupby("competition_id"):
            r = x[x.task_args__mode == "regular"].s.dropna()
            s = x[x.task_args__mode == "sabotage"].s.dropna()
            e = {"regular_runs": int(len(r)), "sabotage_runs": int(len(s))}
            if len(r) and len(s):
                med = float(s.median())
                e.update({
                    "regular_median": round(float(r.median()), 4),
                    "sabotage_median": round(med, 4),
                    "regular_at_or_below_sabotage_median": int((r <= med).sum()),
                    "auroc_raw_score_sabotage_vs_regular": round(auc(np.r_[np.zeros(len(r)), np.ones(len(s))], -np.r_[r, s]), 3),
                })
            if t in POSITIONAL:
                inp = pd.read_csv(fetch(TASKS + t + "/sabotage_inputs/test.csv", cache))
                v = POSITIONAL[t](inp)
                e["score_if_grader_reads_input_file"] = round(v, 4)
                e["runs_equal_to_input_file_score"] = {
                    mode: int(np.isclose(x[x.task_args__mode == mode].s, v, rtol=1e-9).sum())
                    for mode in ["regular", "sabotage"]}
            rows[t] = e
        flagged = [t for t, e in rows.items() if e.get("auroc_raw_score_sabotage_vs_regular", 1) <= 0.65]
        out[scaffold] = {"tasks": rows, "tasks_where_raw_score_barely_separates_modes_auroc_le_0.65": flagged}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="sabotage_checks.json")
    a = ap.parse_args()
    cache = Path(a.cache)
    out = {"pins": {"ctrl-alt-deceit": REPO, "paper": "arXiv 2511.09904v2, Figure 6 and Appendix C"},
           "content_blind_vs_monitor_aide": part_a(cache), "scorer_checks": part_b(cache)}
    Path(a.out).write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
