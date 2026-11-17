"""Step 4/5: the shortcut feature per item, computed without any model output.

For each affected task, an out-of-fold (OOF) prediction from a content-blind classifier:

  facts_human_defaults, influence, facts_llms (placebo task)
      choices-only classifier: logistic regression on TF-IDF (word 1-2 grams) of the answer-choice
      text alone, question hidden; each item's two choices are rows, label 1 on the keyed one;
      5-fold GroupKFold with near-duplicate questions (3-shingle Jaccard >= 0.5) and exact repeats
      in one group, so an item never sees itself or its copy in training. Same pipeline as
      findings/sad-content-blind-and-stale-keys/check_baselines.py:options_only.
      margin = p(keyed choice) - p(other choice); shortcut_right = margin > 0.
      Second, independent version: the hand-written denial rule from the same finding (pick the
      choice that reads as a denial; on yes/no items pick "no"); defined only where exactly one
      choice is a denial.
  stages_full (4-way), stages_oversight (2-way)
      surface classifier: multinomial logistic regression on seven surface features of the text
      (log length, newline rate, digit share, uppercase share, chat-turn marker, lettered-choice
      marker, ends with "?"), stratified 5-fold CV (seed 0). Same features as the earlier finding.
      shortcut_right = OOF argmax == label; conf = OOF probability of the argmax class;
      margin = p(label) - max p(other labels).
      Second, independent version: a random forest (300 trees, seed 0) on twelve surface features
      (the seven plus non-ASCII share, mean word length, share of lines starting with a bullet or
      number, punctuation share, log word count).

Items are keyed by a hash of (id, body, choices) because SAD's ids are not unique (influence) and
some items are scored twice (facts_human_defaults). No item text is written out.

Usage: python -I scripts/features.py --cache data --out results/features.csv
"""
import argparse, hashlib, json, math, re, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import MaxAbsScaler, StandardScaler

from common import clusters, ensure, mcq_task, norm

NEG = re.compile(r"^(no|not|nope|none|never)\b|\b(cannot|can't|can not|don't|do not|doesn't|does not|"
                 r"won't|wouldn't|isn't|aren't|haven't|n't|never|unable|not capable|not able|"
                 r"i'm not|i am not|i don't)\b", re.I)


def item_key(it):
    s = json.dumps([it["id"], it["q"], it["right"], it["wrong"]])
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def choices_only(items, groups, seed=0, folds=5):
    k = 2
    texts = [c for it in items for c in it["right"] + it["wrong"]]
    y = np.tile([1, 0], len(items))
    g = np.repeat(np.asarray(groups), k)
    p = np.zeros(len(texts))
    for tr, te in GroupKFold(n_splits=folds).split(texts, groups=g):
        pipe = make_pipeline(TfidfVectorizer(sublinear_tf=True, ngram_range=(1, 2), min_df=2),
                             MaxAbsScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
        pipe.fit([texts[i] for i in tr], y[tr])
        p[te] = pipe.predict_proba([texts[i] for i in te])[:, 1]
    return p[0::2] - p[1::2]


def denial_rule(it):
    ch = it["right"] + it["wrong"]
    neg = [bool(NEG.search(c.strip())) for c in ch]
    if sum(neg) != 1:
        return np.nan
    return 1.0 if neg[0] else 0.0


def surf7(t):
    n = max(1, len(t))
    return [math.log(n), t.count("\n") / n * 100, sum(c.isdigit() for c in t) / n,
            sum(c.isupper() for c in t) / n,
            float(bool(re.search(r"^(user|human|assistant|ai)\s*:", t, re.I | re.M))),
            float(bool(re.search(r"^\s*\(?[A-D][\).]\s", t, re.M))), float(t.rstrip().endswith("?"))]


def surf12(t):
    n = max(1, len(t))
    w = t.split()
    lines = [l for l in t.split("\n") if l.strip()] or [""]
    return surf7(t) + [sum(ord(c) > 127 for c in t) / n,
                       float(np.mean([len(x) for x in w])) if w else 0.0,
                       sum(bool(re.match(r"\s*([-*•]|\d+[.)])\s", l)) for l in lines) / len(lines),
                       sum(c in ".,;:!?()[]{}\"'" for c in t) / n, math.log(1 + len(w))]


def stages_oof(items, which, seed=0):
    labels = np.array([it["right"][0] for it in items])
    classes = sorted(set(labels))
    X = np.array([(surf7 if which == "lr7" else surf12)(it["q"]) for it in items])
    P = np.zeros((len(items), len(classes)))
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=seed).split(X, labels):
        if which == "lr7":
            m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
        else:
            m = RandomForestClassifier(n_estimators=300, random_state=seed, min_samples_leaf=2)
        m.fit(X[tr], labels[tr])
        P[te] = m.predict_proba(X[te])  # m.classes_ sorted == classes
    li = np.array([classes.index(l) for l in labels])
    pl = P[np.arange(len(items)), li]
    other = P.copy()
    other[np.arange(len(items)), li] = -1
    return pl - other.max(1), P.max(1), np.array(classes)[P.argmax(1)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="results/features.csv")
    a = ap.parse_args()
    unz, _ = ensure(a.cache)
    rows = []
    for t in ("facts_human_defaults", "influence", "facts_llms"):
        items = mcq_task(unz, t)
        grp = clusters([it["q"] for it in items])
        m = choices_only(items, grp)
        for it, g, mm in zip(items, grp, m):
            rows.append({"task": t, "key": item_key(it), "id": it["id"][:24], "group": f"{t}:{g}",
                         "subset": it["batch"] if t != "influence" else it["splits"].get("cat"),
                         "label": "keyed", "margin": round(float(mm), 5), "conf": round(abs(float(mm)), 5),
                         "shortcut_right": int(mm > 0) if mm != 0 else np.nan,
                         "alt_right": denial_rule(it),
                         "identical_choices": int(norm(it["right"][0]) == norm(it["wrong"][0]))})
    for t in ("stages_full", "stages_oversight"):
        items = mcq_task(unz, t)
        grp = clusters([it["q"] for it in items])
        m, conf, pred = stages_oof(items, "lr7")
        m2, _, _ = stages_oof(items, "rf12")
        for it, g, mm, cc, pp, mm2 in zip(items, grp, m, conf, pred, m2):
            rows.append({"task": t, "key": item_key(it), "id": it["id"][:24], "group": f"{t}:{g}",
                         "subset": it["splits"].get("source"), "label": it["right"][0],
                         "shortcut_pred": pp, "margin": round(float(mm), 5), "conf": round(float(cc), 5),
                         "shortcut_right": int(mm > 0), "alt_right": int(mm2 > 0), "identical_choices": 0})
    df = pd.DataFrame(rows)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.out, index=False)
    for t, d in df.groupby("task", sort=False):
        u = d.drop_duplicates("key")
        print(t, "rows", len(d), "distinct", len(u), "shortcut_right", Counter(d.shortcut_right.fillna(-1)),
              "acc", round(d.shortcut_right.mean(), 3), "alt defined", int(d.alt_right.notna().sum()),
              "alt acc", round(d.alt_right.mean(), 3),
              "agree", round(float((d.shortcut_right == d.alt_right)[d.alt_right.notna()].mean()), 3))


if __name__ == "__main__":
    main()
