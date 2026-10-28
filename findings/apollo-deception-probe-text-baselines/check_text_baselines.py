"""Content-blind baselines for two of Apollo's deception-probe evaluation sets.

Goldowsky-Dill et al., "Detecting Strategic Deception Using Linear Probes" (arXiv 2502.03407),
report probe AUROCs of 0.999 on Insider Trading Report and 0.983 on Sandbagging (honest vs
deceptive, ambiguous excluded). This script asks how well the text alone separates the same labels,
using the released Llama-3.3-70B rollouts at a pinned commit:

- Insider Trading Report: whether the report email mentions the insider tip, and email length.
- Sandbagging: question source (WMDP vs MMLU), the step scaffold, and a bag-of-words classifier
  on only the span the probe is scored on (from the last <step4>, the repo's default trimming),
  against a shuffled-label null.

It reads the rollouts as text and never runs them.

Usage:
    python check_text_baselines.py [--cache DIR] [--out text_baselines.json]
"""
import argparse, ast, json, re, urllib.request
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

COMMIT = "f8ec4010e74927394709dffa22b97bdf8cd5a62f"
RAW = f"https://raw.githubusercontent.com/ApolloResearch/deception-detection/{COMMIT}/"
INSIDER = RAW + "data/insider_trading/llama-70b-3.3-generations.json"
SANDBAG = RAW + "data/rollouts/sandbagging_v2__wmdp_mmlu__llama-70b-3.3.json"
WMDP = {"bio", "chem", "cyber"}
PERMUTATIONS = 20


def fetch(url, cache):
    path = cache / url.rsplit("/", 1)[1]
    if not path.exists():
        with urllib.request.urlopen(url, timeout=300) as r:
            path.write_bytes(r.read())
    return json.loads(path.read_text())


def lit(v):
    return ast.literal_eval(v) if isinstance(v, str) else v


def auroc(y, s):
    return round(float(roc_auc_score(y, s)), 3)


def bow_auroc(texts, y):
    X = CountVectorizer(binary=True, min_df=2).fit_transform(texts)
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    p = cross_val_predict(LogisticRegression(max_iter=2000), X, y, cv=cv,
                          method="predict_proba")[:, 1]
    return auroc(y, p)


def insider_trading(rows):
    y, mentions, length = [], [], []
    for r in rows:
        m = r["metadata"]
        if m.get("report_label") not in ("explicit", "concealed"):
            continue
        email = m["report_message"].split("Action Input:", 1)[-1]
        y.append(m["report_label"] == "concealed")
        mentions.append(bool(re.search(r"insider|non-public|nonpublic", email, re.I)))
        length.append(len(email))
    y, mentions, length = map(np.array, (y, mentions, length))
    return {"deceptive": int(y.sum()), "honest": int((~y).sum()),
            "email_mentions_tip": {"deceptive": int(mentions[y].sum()),
                                   "honest": int(mentions[~y].sum())},
            "auroc_no_mention": auroc(y, ~mentions),
            "auroc_shorter_email": auroc(y, -length),
            "paper_probe_auroc": 0.999}


def sandbagging(data):
    y, scored, step2, wmdp = [], [], [], []
    for r in data["rollouts"]:
        topic = lit(r["metadata"])["topic"]
        for label, out in zip(lit(r["graded_deception"]), lit(r["output_strs"])):
            if label not in ("honest", "deceptive") or "<step4>" not in out:
                continue
            y.append(label == "deceptive")
            scored.append(out[out.rindex("<step4>"):])
            step2.append("<step2>" in out)
            wmdp.append(topic in WMDP)
    y, step2, wmdp = map(np.array, (y, step2, wmdp))
    rng = np.random.default_rng(0)
    null = [bow_auroc(scored, rng.permutation(y)) for _ in range(PERMUTATIONS)]
    return {"deceptive": int(y.sum()), "honest": int((~y).sum()),
            "response_has_step2": {"deceptive": int(step2[y].sum()), "honest": int(step2[~y].sum())},
            "question_from_wmdp": {"deceptive": int(wmdp[y].sum()), "honest": int(wmdp[~y].sum())},
            "auroc_question_source": auroc(y, wmdp),
            "auroc_bow_scored_span": bow_auroc(scored, y),
            "null_bow_scored_span": {"mean": round(float(np.mean(null)), 3),
                                     "max": round(float(np.max(null)), 3),
                                     "permutations": PERMUTATIONS},
            "paper_probe_auroc": 0.983}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="text_baselines.json")
    args = ap.parse_args()
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    result = {"pins": {"deception_detection_commit": COMMIT},
              "insider_trading_report": insider_trading(fetch(INSIDER, cache)),
              "sandbagging": sandbagging(fetch(SANDBAG, cache))}
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
