"""Blind hand check of routes into "unfaithful" (post hoc, P5).

`build`: sample wrong answers to the lower-accuracy question of flagged pairs, up to 2 that the
authors' pattern autorater marks as answer flipping and 2 it does not, per model (6 + 6 for
Claude 3.7 Sonnet), seed 11. Writes results/route_sample.csv with the hidden labels and prints
the items shuffled, without model or autorater label, for labelling.
`score`: joins my labels (route_labels.csv) with the hidden ones.

    data/.venv/bin/python -I scripts/handcheck_routes.py build > data/route_items.txt
    data/.venv/bin/python -I scripts/handcheck_routes.py score
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).parent))
from posthoc_flip import MODELS  # noqa: E402

L = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def build():
    rng = np.random.default_rng(11)
    rows = []
    for short in MODELS:
        flips = {}
        for fp in sorted(Path("data/pat").glob(f"*__{short}.yaml")):
            d = yaml.load(fp.open(), Loader=L)
            for qid, it in d["pattern_analysis_by_qid"].items():
                for rid, r in ((it.get("q1_analysis") or {}).get("responses") or {}).items():
                    flips[(qid, rid)] = (r.get("answer_flipping_classification"),
                                         ",".join(it.get("categorization_for_pair") or []))
        flagged = set(json.loads(Path("results/flagged_low_qids.json").read_text())[short])
        cand = {"YES": [], "NO": []}
        for fp in sorted(Path("data/faith").glob(f"{short}__*.yaml")):
            d = yaml.load(fp.open(), Loader=L)
            for qid, it in d["questions_by_qid"].items():
                if qid not in flagged:
                    continue
                q = it["prompt"].split("\n\n")[1].strip()
                for rid, r in it["unfaithful_responses"].items():
                    lab = flips.get((qid, rid))
                    if lab and lab[0] in cand:
                        cand[lab[0]].append((qid, rid, q, r["response"], lab[1]))
        k = 6 if short == "claude-3.7-sonnet" else 2
        for lab, v in cand.items():
            for i in rng.permutation(len(v))[:k]:
                qid, rid, q, t, cats = v[i]
                rows.append({"model": short, "qid": qid, "response_id": rid, "autorater_flip": lab,
                             "pair_categories": cats, "question": q, "text": t})
    S = pd.DataFrame(rows).sample(frac=1, random_state=11).reset_index(drop=True)
    S.insert(0, "item", range(len(S)))
    S.drop(columns=["question", "text"]).to_csv("results/route_sample.csv", index=False)
    for _, r in S.iterrows():
        t = re.sub(r"\s+", " ", r.text)
        if len(t) > 1500:
            t = t[:900] + " [...] " + t[-550:]
        print(f"### item {r['item']}\nQ: {r.question}\n{t}\n")


def score():
    S = pd.read_csv("results/route_sample.csv")
    Lb = pd.read_csv("route_labels.csv")
    M = S.merge(Lb, on="item")
    M["me_flip"] = M.route == "FLIP"
    M["ar_flip"] = M.autorater_flip == "YES"
    tab = pd.crosstab(M.ar_flip, M.me_flip)
    agree = float((M.me_flip == M.ar_flip).mean())
    by_route = M.route.value_counts().to_dict()
    s37 = M[M.model == "claude-3.7-sonnet"]
    out = {"n": len(M), "agreement_flip": agree, "crosstab_autorater_rows_me_cols": tab.to_dict(),
           "my_routes": by_route,
           "autorater_flip_yes_precision": float(M[M.ar_flip].me_flip.mean()),
           "autorater_flip_no_my_flip_share": float(M[~M.ar_flip].me_flip.mean()),
           "claude37_my_flip_share_among_ar_yes": float(s37[s37.ar_flip].me_flip.mean()),
           "claude37_my_flip_share_among_ar_no": float(s37[~s37.ar_flip].me_flip.mean()),
           "routes_by_autorater_label": pd.crosstab(M.autorater_flip, M.route).to_dict()}
    Path("results/handcheck_routes.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"build": build, "score": score}[sys.argv[1]]()
