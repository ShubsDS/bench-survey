"""Shortcuts and provenance in rh-bench, a pooled reward-hacking detector benchmark.

rh-bench (huggingface.co/datasets/ktolnos/rh-bench) pools reward-hacking examples from several
sources into one table with a `label` (hacking / clean / paired), a `verification` field (human,
llm_judge, deterministic, none) and the generating `response_model`. It is meant for training and
testing reward-hack detectors. This script, at pinned revisions, checks:

1. Row counts against the dataset card.
2. Prompt-only and response-only bag-of-words baselines, per source, for the sources whose content
   is openly licensed (Jozdien realistic_reward_hacks, Countdown-Code), with prompts kept within one
   fold. A detector benchmark should not be solvable from the prompt.
3. School of Reward Hacks (source CSV): how often a bag-of-words model ranks the hack above its
   matched control on held-out pairs, against a null that swaps labels within random pairs.
4. The METR MALT rows, from metadata only (model, label, verification, split): which models the
   "clean" rows come from, compared with MALT's own card, which lists no Claude 3.7 Sonnet run among
   its human-reviewed benign runs. MALT and TRACE are gated upstream, so their text is not read.

Usage:
    python check_rhbench.py [--cache DIR] [--out rhbench_checks.json]
"""
import argparse, json, re, urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold, cross_val_predict

RH_SHA = "1045a7336432c40182924bbd3698af292ea24acb"
SORH_SHA = "d7e04a550119cb5410494cf90e2313284a5f2148"
RH = f"https://huggingface.co/datasets/ktolnos/rh-bench/resolve/{RH_SHA}/"
SORH = f"https://huggingface.co/datasets/longtermrisk/school-of-reward-hacks/resolve/{SORH_SHA}/school-of-reward-hacks.csv"
OPEN_SOURCES = ("jozdien_realistic_reward_hacks", "countdown_code")
# MALT public split (huggingface.co/datasets/metr-evals/malt-public card), human-reviewed benign
# runs by model; see ../malt-sandbagging-one-model/models.json.
MALT_REVIEWED_BENIGN = {"claude-opus-4-20250514": 349, "claude-sonnet-4-20250514": 332, "o1-preview": 1,
                        "o3-2025-04-16": 1, "openrouter/deepseek/deepseek-r1-0528": 11}
NULLS = 5


def fetch(url, cache):
    path = cache / url.rsplit("/", 1)[1]
    if not path.exists():
        with urllib.request.urlopen(url, timeout=600) as r:
            path.write_bytes(r.read())
    return path


def text(js):
    if js is None:
        return ""
    try:
        m = json.loads(js)
    except (TypeError, ValueError):
        return str(js)
    return " ".join(str(x.get("content", "")) for x in m) if isinstance(m, list) else str(m)


def bow_auroc(texts, y, groups):
    X = CountVectorizer(binary=True, min_df=2).fit_transform(texts)
    p = cross_val_predict(LogisticRegression(max_iter=3000), X, y, cv=GroupKFold(5), groups=groups,
                          method="predict_proba")[:, 1]
    return round(float(roc_auc_score(y, p)), 3)


def card_counts(card):
    rows = {}
    for m in re.finditer(r"^\|\s*(open_ended|multichoice|encrypted)\s*\|\s*([\d,]+)\s*\|", card, re.M):
        rows[m.group(1)] = int(m.group(2).replace(",", ""))
    for m in re.finditer(r"^\|\s*\[([^\]]+)\]\([^)]*\)\s*\|\s*([\d,]+)\s*\|", card, re.M):
        rows[m.group(1)] = int(m.group(2).replace(",", ""))
    return rows


def open_sources(u):
    out = {}
    rng = np.random.default_rng(0)
    for src in OPEN_SOURCES:
        g = u[(u.source_dataset == src) & u.label.isin(["hacking", "clean"])].reset_index(drop=True)
        y = (g.label == "hacking").to_numpy().astype(int)
        prompts = [text(p) for p in g.prompt]
        resp = [text(h if l == "hacking" else c) for h, c, l in zip(g.response_hacking, g.response_clean, g.label)]
        groups = pd.factorize(pd.Series(prompts))[0]
        out[src] = {"rows": len(g), "hacking": int(y.sum()),
                    "label_by_source_split": {k: dict(v) for k, v in
                                              g.groupby("source_split").label.value_counts().unstack(fill_value=0).iterrows()},
                    "prompt_only_bow_auroc": bow_auroc(prompts, y, groups),
                    "response_only_bow_auroc": bow_auroc(resp, y, groups),
                    "null_prompt_only": [bow_auroc(prompts, rng.permutation(y), groups) for _ in range(NULLS)]}
    return out


def sorh(cache):
    d = pd.read_csv(fetch(SORH, cache))
    p = d[d.control.notna()].reset_index(drop=True)
    n = len(p)
    texts = list(p.school_of_reward_hacks) + list(p.control)
    grp = np.r_[np.arange(n), np.arange(n)]

    def paired(y):
        wins = []
        for tr, te in GroupKFold(5).split(texts, y, grp):
            v = CountVectorizer(binary=True, min_df=2).fit([texts[i] for i in tr])
            m = LogisticRegression(max_iter=3000).fit(v.transform([texts[i] for i in tr]), y[tr])
            s = dict(zip(te, m.predict_proba(v.transform([texts[i] for i in te]))[:, 1]))
            for k in np.unique(grp[te]):
                a, b = k, k + n
                hack, ctl = (a, b) if y[a] == 1 else (b, a)
                wins.append(s[hack] > s[ctl])
        return round(float(np.mean(wins)), 3)

    y = np.r_[np.ones(n), np.zeros(n)]
    rng = np.random.default_rng(0)
    nulls = []
    for _ in range(NULLS):
        flip = rng.random(n) < .5
        y2 = y.copy()
        y2[:n][flip], y2[n:][flip] = 0, 1
        nulls.append(paired(y2))
    return {"rows": len(d), "rows_without_control": int(d.control.isna().sum()), "pairs": n,
            "tasks": int(d.task.nunique()), "paired_accuracy_bow": paired(y), "null": nulls}


def malt(u):
    m = u[u.source_dataset == "metr_malt"]
    clean = m[m.label == "clean"]
    unreviewed = clean[~clean.response_model.isin(MALT_REVIEWED_BENIGN)]
    return {"rows": len(m), "label": m.label.value_counts().to_dict(),
            "verification": m.verification.value_counts().to_dict(),
            "clean_by_model": clean.response_model.value_counts().to_dict(),
            "clean_rows_from_models_with_no_reviewed_benign_run_in_malt": len(unreviewed),
            "hacking_by_model": m[m.label == "hacking"].response_model.value_counts().to_dict(),
            "malt_card_reviewed_benign_by_model": MALT_REVIEWED_BENIGN}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="rhbench_checks.json")
    args = ap.parse_args()
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    card = fetch(RH + "README.md", cache).read_text()
    u = pd.read_parquet(fetch(RH + "data/rh_bench_unified.parquet", cache))
    claimed = card_counts(card)
    result = {"pins": {"rh_bench": f"ktolnos/rh-bench@{RH_SHA}",
                       "school_of_reward_hacks": f"longtermrisk/school-of-reward-hacks@{SORH_SHA}"},
              "row_counts": {"card_open_ended": claimed.get("open_ended"), "file_open_ended": len(u),
                             "card_metr_malt": claimed.get("METR MALT"),
                             "file_metr_malt": int((u.source_dataset == "metr_malt").sum()),
                             "file_by_source": u.source_dataset.value_counts().to_dict()},
              "open_sources": open_sources(u),
              "school_of_reward_hacks": sorh(cache),
              "metr_malt_metadata": malt(u)}
    Path(args.out).write_text(json.dumps(result, indent=1, default=int) + "\n")
    print(json.dumps(result, indent=1, default=int))


if __name__ == "__main__":
    main()
