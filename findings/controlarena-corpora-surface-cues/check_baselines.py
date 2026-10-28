"""Check 1 (content-blind baselines) on the five adityaasinha28/control_arena_* corpora.

Features come from the `transcript` field, which equals the single `prompt` message a monitor
is given (check_provenance.py verifies this). Task = main_task_name (suite/user task for
agentdojo). Baselines, each with a shuffled-label null where labels are permuted within task:

  A. within-task Mann-Whitney AUROC on character count, pooled over tasks by pair count
     (the statistic of experiments/agentic/floors2.py), also within task x model cells, and on
     the 28K-token-filtered subsets 2605.29601 evaluates (shade 850, iac 1,443 rows);
  B. gradient boosting on six transcript counts (chars, lines, words, assistant turns, tool
     turns, tool calls), 5-fold GroupKFold by task;
  C. TF-IDF logistic regression, GroupKFold by task, on (i) tool-call function names only,
     (ii) tool output text only, (iii) the whole transcript;
  D. metadata only: task id one-hot, model id one-hot (ungrouped stratified 5-fold);
  E. not in the monitor's input: the policy's own reasoning (assistant `content` in
     trajectory_data): its length, and the 15-phrase regex of experiments/agentic/cot.py.

AUROCs are signed (above 0.5 = attack scores higher). The within-task Mann-Whitney null is on the
folded statistic max(a, 1 - a), as in floors2.py; the cross-validated baselines use the signed
out-of-fold AUROC and a one-sided null. Nulls report mean, 95th percentile and
p = (1 + #{null >= observed}) / (1 + R). C(ii) and C(iii) read text that contains the attack
actions or their results, so they are reference points, not content-blind baselines.
Only aggregates are written.

Usage:
    python -I check_baselines.py --cache data --out baselines_checks.json [--quick]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.request

import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold, StratifiedKFold

SETTINGS = ["bash", "shade", "iac", "rogue_eval", "agentdojo"]
PINS = {
    "bash": ("08663a5d10a5445bc4b750b7f8eb079c9a505df8", "29550a69f0d6c0dcc59b976d3a68fdf662ecd2620b2525c234ecb8794882e9c8"),
    "shade": ("7b5861e85f14381e70ed5b101fd7ceeec96d4f29", "2b637f8279804668f9210080f788b40d4cae133e56007d1d767f5da9e40e4eee"),
    "iac": ("cd0e7f667eba6214e2100f5fd30aec9f65aca1a8", "d74610fefa78bb7ae79594310e826d84c87b38508ba16104b3c64b2e92c343e8"),
    "rogue_eval": ("7946e03ece9d8329a28c17d7b0fe778b9c774b39", "2689c6e5ee7d708c07e798ddde9055606778938fdfd9d1aef9cfab66744c0640"),
    "agentdojo": ("a0f1e2131a8f27ebe14c285fa8ad34e439d128e2", "5ceb33f1116b9c317b98be1ddcfb7dddca300482ca45736faf291b0796ad5c33"),
}
PIPE_REPO = "adityaasinha28/deliberative-monitor-pipeline"
PIPE_SHA = "2f10f4e49f4bf349965640ac021406689455d1c3"
PRIOR_WITHIN_TASK = {"bash": 0.5044, "shade": 0.6022, "iac": 0.7041, "rogue_eval": 0.6158, "agentdojo": 0.8020}
KW = ["side task", "secondary task", "secret task", "injection", "without being detected", "without the user",
      "not mention", "hidden objective", "covert", "suspicious", "monitor", "stealth", "conceal", "disguise", "cover story"]
KWPAT = re.compile("|".join(re.escape(k) for k in KW), re.I)
TAGPAT = re.compile(r"<(?:thinking|think|reasoning|scratchpad|reflection)>", re.I)


def fetch(url: str, path: str, sha256: str | None = None) -> str:
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with urllib.request.urlopen(url, timeout=600) as r, open(path + ".part", "wb") as fh:
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                fh.write(b)
        os.replace(path + ".part", path)
    if sha256:
        h = hashlib.sha256(open(path, "rb").read()).hexdigest()
        if h != sha256:
            raise SystemExit(f"{path}: sha256 {h} != pinned {sha256}")
    return path


def corpus(cache: str, s: str) -> pd.DataFrame:
    sha, h = PINS[s]
    url = f"https://huggingface.co/datasets/adityaasinha28/control_arena_{s}/resolve/{sha}/control_arena_{s}.parquet"
    return pd.read_parquet(fetch(url, os.path.join(cache, f"control_arena_{s}.parquet"), h))


def pipe_rows(cache: str, s: str) -> np.ndarray:
    rel = f"filtered_eval/ctrl_{s}.parquet"
    p = fetch(f"https://huggingface.co/datasets/{PIPE_REPO}/resolve/{PIPE_SHA}/{rel}", os.path.join(cache, "pipeline", rel))
    return pd.read_parquet(p, columns=["row_index"])["row_index"].to_numpy()


SEG = re.compile(r"(?m)^\[(USER|ASSISTANT|TOOL)\]\n")


def segments(tr: str) -> list[tuple[str, str]]:
    parts = SEG.split(tr)
    return [(parts[i], parts[i + 1]) for i in range(1, len(parts) - 1, 2)]


CALL = re.compile(r"(?m)^([A-Za-z_][A-Za-z0-9_]*)\(")


def features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    t = df["transcript"].fillna("").astype(str)
    names, outs, rows = [], [], []
    for tr in t:
        segs = segments(tr)
        calls = []
        for role, body in segs:
            if role == "ASSISTANT" and "[TOOL CALLS]" in body:
                calls += CALL.findall(body.split("[TOOL CALLS]", 1)[1])
        names.append(" ".join(calls))
        outs.append("\n".join(b for r, b in segs if r == "TOOL"))
        rows.append({"chars": len(tr), "lines": tr.count("\n"), "words": len(tr.split()),
                     "assistant_turns": sum(r == "ASSISTANT" for r, _ in segs),
                     "tool_turns": sum(r == "TOOL" for r, _ in segs), "tool_calls": len(calls)})
    return pd.DataFrame(rows), pd.Series(names), pd.Series(outs)


def task_ids(df: pd.DataFrame) -> np.ndarray:
    md = pd.json_normalize(df["trajectory_data"].map(lambda x: json.loads(x)["metadata"]))
    t = md["main_task_name"].fillna("").astype(str)
    if "suite_name" in md:
        t = md["suite_name"].astype(str) + "/" + t
    return t.to_numpy()


class WithinTask:
    def __init__(self, x, y, g):
        self.groups, self.pairs = [], 0
        for t in pd.unique(g):
            idx = np.flatnonzero(g == t)
            yy = y[idx]
            n1 = int(yy.sum()); n0 = len(yy) - n1
            if n1 and n0:
                self.groups.append((rankdata(x[idx]), yy, n1))
                self.pairs += n1 * n0

    def auroc(self, labels=None):
        w = 0.0
        for k, (r, yy, n1) in enumerate(self.groups):
            lab = yy if labels is None else labels[k]
            w += r[lab == 1].sum() - n1 * (n1 + 1) / 2.0
        return w / self.pairs


def within_task(x, y, g, n_perm, rng, n_boot=500):
    w = WithinTask(x, y, g)
    raw = w.auroc(); obs = max(raw, 1 - raw)
    null = np.array([max(v, 1 - v) for v in (w.auroc([rng.permutation(yy) for _, yy, _ in w.groups]) for _ in range(n_perm))])
    boots = []
    for _ in range(n_boot):  # rows resampled within task (ignores epoch correlation: too narrow)
        idx = np.concatenate([rng.choice(np.flatnonzero(g == t), size=int((g == t).sum())) for t in pd.unique(g)])
        wb = WithinTask(x[idx], y[idx], g[idx])
        if wb.pairs:
            boots.append(wb.auroc())
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"auroc_signed": round(raw, 4), "auroc_folded": round(obs, 4),
            "ci95_signed_row_bootstrap": [round(float(lo), 4), round(float(hi), 4)],
            "tasks_used": len(w.groups), "pairs": int(w.pairs), **nullstats(obs, null)}


def nullstats(obs, null):
    null = np.asarray(null)
    return {"null_mean": round(float(null.mean()), 4), "null_p95": round(float(np.percentile(null, 95)), 4),
            "null_max": round(float(null.max()), 4), "perm_p": round(float((1 + np.sum(null >= obs)) / (1 + len(null))), 4),
            "n_perm": int(len(null))}


def perm_within(y, g, rng):
    yp = y.copy()
    for t in pd.unique(g):
        idx = np.flatnonzero(g == t)
        yp[idx] = rng.permutation(y[idx])
    return yp


def oof(fit_predict, X, y, g, grouped=True):
    p = np.zeros(len(y))
    splits = GroupKFold(5).split(X, y, g) if grouped else StratifiedKFold(5, shuffle=True, random_state=0).split(X, y)
    for tr, te in splits:
        if len(set(y[tr])) < 2:
            p[te] = 0.5
            continue
        p[te] = fit_predict(X[tr], y[tr], X[te])
    return p


def gbm(Xtr, ytr, Xte):
    return GradientBoostingClassifier(random_state=0).fit(Xtr, ytr).predict_proba(Xte)[:, 1]


def lr(Xtr, ytr, Xte):
    return LogisticRegression(C=1.0, max_iter=2000).fit(Xtr, ytr).predict_proba(Xte)[:, 1]


def cv_with_null(fp, X, y, g, n_perm, rng, grouped=True, perm="within"):
    # signed statistic, one-sided null: a cross-task model that is anti-predictive is not a cue
    a = float(roc_auc_score(y, oof(fp, X, y, g, grouped)))
    null = []
    for _ in range(n_perm):
        yp = perm_within(y, g, rng) if perm == "within" else rng.permutation(y)
        null.append(float(roc_auc_score(yp, oof(fp, X, yp, g, grouped))))
    return {"auroc_signed": round(a, 4), **nullstats(a, null)}


def scratchpad(df: pd.DataFrame) -> pd.Series:
    def f(td):
        ms = json.loads(td)["messages"]
        return "\n".join((m.get("content") or "") for m in ms if m["role"] == "assistant")
    return df["trajectory_data"].map(f)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="baselines_checks.json")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--quick", action="store_true", help="fewer permutations")
    a = ap.parse_args()
    R_MW, R_GBM, R_BOW, R_META = (200, 10, 5, 50) if a.quick else (1000, 100, 20, 200)

    out = {"pins": {s: PINS[s][0] for s in SETTINGS}, "pipeline_pin": PIPE_SHA,
           "n_perm": {"within_task_mw": R_MW, "gbm_structural": R_GBM, "bow": R_BOW, "metadata": R_META},
           "seed": a.seed, "settings": {}}
    for k, s in enumerate(SETTINGS):
        rng = np.random.default_rng([a.seed, k])
        df = corpus(a.cache, s)
        y = df["ground_truth"].astype(int).to_numpy()
        g = task_ids(df)
        model = pd.json_normalize(df["extra_info"])["model"].to_numpy()
        F, names, outs = features(df)
        r: dict = {"n": int(len(y)), "n_tasks": int(len(set(g)))}

        r["median_by_label"] = {c: {str(l): float(F[c][y == l].median()) for l in (0, 1)} for c in F.columns}
        r["reasoning_tag_in_transcript_rate"] = {str(l): round(float(df["transcript"][y == l].str.contains(TAGPAT).mean()), 4) for l in (0, 1)}

        # A. within-task chars
        x = F["chars"].to_numpy().astype(float)
        r["A_within_task_chars"] = within_task(x, y, g, R_MW, rng)
        r["A_within_task_chars"]["reproduces_floors2"] = bool(abs(r["A_within_task_chars"]["auroc_folded"] - PRIOR_WITHIN_TASK[s]) < 1e-4)
        gm = np.array([f"{t}|{m}" for t, m in zip(g, model)])
        r["A_within_task_x_model_chars"] = within_task(x, y, gm, R_MW, rng, n_boot=200)
        r["A_within_task_other_counts_signed"] = {c: round(WithinTask(F[c].to_numpy().astype(float), y, g).auroc(), 4)
                                                  for c in F.columns if c != "chars"}
        if s in ("shade", "iac", "rogue_eval", "bash"):
            keep = pipe_rows(a.cache, s)
            r["A_within_task_chars_on_2605_29601_filtered_rows"] = {"n": int(len(keep)),
                                                                     **within_task(x[keep], y[keep], g[keep], R_MW, rng, n_boot=200)}
            dropped = np.setdiff1d(np.arange(len(y)), keep)
            r["filtered_rows_dropped_by_label"] = {str(l): int((y[dropped] == l).sum()) for l in (0, 1)}

        # B. structural GBM, GroupKFold by task
        r["B_gbm_structural_groupkfold"] = cv_with_null(gbm, F.to_numpy().astype(float), y, g, R_GBM, rng)

        # C. bag of words (vocabulary fit label-free on all rows)
        for name, text, kw in [("C_bow_tool_names", names, dict(token_pattern=r"[A-Za-z_][A-Za-z0-9_]*", ngram_range=(1, 2), min_df=2)),
                               ("C_bow_tool_outputs", outs, dict(min_df=3, max_features=30000, sublinear_tf=True)),
                               ("C_bow_whole_transcript", df["transcript"].fillna(""), dict(min_df=3, max_features=30000, sublinear_tf=True))]:
            X = TfidfVectorizer(**kw).fit_transform(text)
            r[name] = cv_with_null(lr, X, y, g, R_BOW, rng)

        # D. metadata only (ungrouped CV; within-task permutation would be constant, so permute globally)
        T = pd.get_dummies(pd.Series(g)).to_numpy().astype(float)
        r["D_task_id_only_ungrouped"] = cv_with_null(lr, T, y, g, R_META, rng, grouped=False, perm="global")
        M = pd.get_dummies(pd.Series(model)).to_numpy().astype(float)
        r["D_model_id_only_ungrouped"] = cv_with_null(lr, M, y, g, R_META, rng, grouped=False, perm="global")
        pos_rate = pd.Series(y).groupby(g).mean()
        r["D_task_positive_rate_range"] = [round(float(pos_rate.min()), 4), round(float(pos_rate.max()), 4)]

        # E. policy reasoning, which the transcript does not contain
        sp = scratchpad(df)
        hits = sp.map(lambda z: len(KWPAT.findall(z))).to_numpy()
        ka = roc_auc_score(y, hits)
        r["E_not_in_monitor_input"] = {
            "reasoning_chars_auroc_signed": round(float(roc_auc_score(y, sp.str.len())), 4),
            "reasoning_chars_within_task_signed": round(WithinTask(sp.str.len().to_numpy().astype(float), y, g).auroc(), 4),
            "cot_regex_auroc_signed": round(float(ka), 4),
            "cot_regex_hit_rate_by_label": {str(l): round(float((hits[y == l] > 0).mean()), 4) for l in (0, 1)},
            "reasoning_tag_rate_by_label": {str(l): round(float(sp[y == l].str.contains(TAGPAT).mean()), 4) for l in (0, 1)},
            "cot_regex_hits_in_transcript_auroc_signed": round(float(roc_auc_score(
                y, df["transcript"].map(lambda z: len(KWPAT.findall(z))))), 4),
        }
        out["settings"][s] = r
        print(s, json.dumps({kk: (v.get("auroc_signed") if isinstance(v, dict) and "auroc_signed" in v else None)
                             for kk, v in r.items() if kk[:2] in ("A_", "B_", "C_", "D_")}), flush=True)

    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
