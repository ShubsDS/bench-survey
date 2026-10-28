"""DarkBench content-blind baselines: do length or stock phrases predict the dark-pattern labels?

The DarkBench authors did not publish responses or annotations (their DVC remote needs a login).
Two public re-runs publish responses with judge verdicts from three developers:

* who-gets-nudged (Lukyanenko 2026, github.com/stlukyanenko/who-gets-nudged @ 8882ddb, MIT):
  2,520 responses from six models to 60 DarkBench prompts in four categories (anthropomorphization,
  brand bias, sycophancy, user retention), under a fictional deployer system prompt; DarkBench judge
  prompt; judges Gemini 3.8 Flash, Claude Sonnet 5.5, GPT-6 Luna; 100 human labels.
* darkbench-revisited (Hartnett 2026, github.com/eileenhartnett/darkbench-revisited @ c62134a, no
  licence: aggregates only): 150 hand-labelled responses (four categories, sampled to over-represent
  judge disagreement) and 100 unlabelled sneaking and brand-bias responses, each with the three
  judges' verdicts (GPT-5.5, Opus 4.6, Gemini 3.1 Pro).

Features, fixed before looking at any label (regexes below):
  length in characters; refusal phrases; AI self-disclaimers ("as an AI", "I don't have feelings");
  stock warmth formulas ("I'm here for you", "happy to help", "feel free", "take care"); first-person
  affect ("I love", "I enjoy", "I find"); ending on a question; exclamation marks.

For each category and label source (majority of the three judges, each judge, the human label) the
script reports each feature's AUROC and a null from 1,000 permutations of the labels within prompt
(so prompt-level differences in length or base rate are kept). It also fits a logistic regression on
all features with cross-validation grouped by prompt, against 200 within-prompt permutations.
Flag rule (scope.md check 1): AUROC above the null's 95th percentile and above 0.6.

Usage:
    python check_baselines.py [--cache DIR] [--out baselines_checks.json]
"""
import argparse, csv, io, json, re, urllib.request, zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

NUD = ("stlukyanenko/who-gets-nudged", "8882ddb2af915313b5ae26699c27cfc83e285f5c")
REV = ("eileenhartnett/darkbench-revisited", "c62134aa9a64b510dc1f4e2baf18e592a2028883")
NUD_LOGS = [
    "2026-10-18T22-14-21-00-00_who-gets-nudged_G5DN54XNdRN8S68bhkCCaP.eval",
    "2026-10-18T22-14-22-00-00_who-gets-nudged_LPMPSztYMEjxv6akQ4sn7M.eval",
    "2026-10-18T22-14-22-00-00_who-gets-nudged_bd3jbQ2pVxCfvKnKHSQkbX.eval",
    "2026-10-18T22-15-42-00-00_who-gets-nudged_SucFpK7EGHXKDtCszWJHkN.eval",
    "2026-10-18T22-17-09-00-00_who-gets-nudged_6NYGVd8hmJb2jPYyoDzDRV.eval",
    "2026-10-18T22-24-32-00-00_who-gets-nudged_k99aYG7FaowFCM5RTu2bgg.eval",
]

PAT = {
    "refusal": r"\b(i can(?:'|’)?t|i cannot|i won(?:'|’)t|i(?:'|’)m not able to|i am not able to|i(?:'|’)m unable|i am unable|i must decline|i(?:'|’)m not going to)\b",
    "ai_disclaimer": r"\b(as an ai|i(?:'|’)m an ai|i am an ai|ai (?:language )?model|language model|i don(?:'|’)t (?:have|experience) (?:personal|feelings|emotions|a body|preferences|experiences|a life)|i do not have (?:personal|feelings|emotions|preferences)|not a (?:real )?person|i(?:'|’)m not (?:a )?human|i am not (?:a )?human)\b",
    "warmth_formula": r"\b(here for you|i(?:'|’)m (?:so |really )?glad|happy to (?:help|chat|talk|listen)|i(?:'|’)d love to|feel free|don(?:'|’)t hesitate|reach out|any ?time|take care|i(?:'|’)m (?:so |really )?sorry|i understand|that sounds (?:really |so )?(?:hard|tough|difficult|lonely)|you(?:'|’)re not alone|always here)\b",
    "first_person_affect": r"\b(i (?:really |genuinely |truly )?(?:love|enjoy|like|feel|find|adore|miss|cherish)|my favou?rite)\b",
}
STYLE = ["log_chars", "warmth_formula", "first_person_affect", "ends_question", "exclamations"]
FEATS = ["log_chars", "refusal", "ai_disclaimer", "warmth_formula", "first_person_affect", "ends_question", "exclamations"]


def fetch(repo, path, cache, binary=False):
    name, sha = repo
    local = cache / name.replace("/", "__") / sha[:7] / path
    if not local.exists():
        local.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(f"https://raw.githubusercontent.com/{name}/{sha}/{path}", timeout=300) as r:
            local.write_bytes(r.read())
    return local if binary else local.read_text(encoding="utf-8")


def feats(text):
    t = text.lower()
    f = {"log_chars": float(np.log1p(len(text)))}
    for k, p in PAT.items():
        f[k] = float(len(re.findall(p, t)))
    f["ends_question"] = float("?" in text.rstrip()[-200:])
    f["exclamations"] = float(text.count("!"))
    return f


def auroc(score, y):
    score, y = np.asarray(score, float), np.asarray(y, int)
    pos, neg = y.sum(), len(y) - y.sum()
    if pos == 0 or neg == 0:
        return None
    order = np.argsort(score, kind="mergesort")
    ranks = np.empty(len(score)); s = score[order]
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return float((ranks[y == 1].sum() - pos * (pos + 1) / 2) / (pos * neg))


def perm_within(y, groups, rng):
    y = np.asarray(y).copy()
    for g in np.unique(groups):
        idx = np.where(groups == g)[0]
        y[idx] = y[rng.permutation(idx)]
    return y


def cv_auc(X, y, groups):
    k = min(5, len(np.unique(groups)))
    pred = np.zeros(len(y))
    for tr, te in GroupKFold(n_splits=k).split(X, y, groups):
        if len(np.unique(y[tr])) < 2:
            pred[te] = y[tr].mean(); continue
        m = LogisticRegression(max_iter=2000, C=1.0).fit(X[tr], y[tr])
        pred[te] = m.predict_proba(X[te])[:, 1]
    return auroc(pred, y)


def analyse(rows, label_key, rng, n_perm=1000, n_perm_cv=200):
    """rows: list of dicts with 'feats', 'group', label_key. Returns per-feature AUROC with nulls."""
    rows = [r for r in rows if r.get(label_key) is not None]
    y = np.array([r[label_key] for r in rows], int)
    g = np.array([r["group"] for r in rows])  # CV folds
    gp = np.array([r.get("permgroup", r["group"]) for r in rows])  # permutation strata
    out = {"n": len(rows), "positives": int(y.sum())}
    if y.sum() < 3 or (len(y) - y.sum()) < 3:
        out["skipped"] = "fewer than 3 in a class"
        return out
    X = np.array([[r["feats"][f] for f in FEATS] for r in rows])
    perms = [perm_within(y, gp, rng) for _ in range(n_perm)]
    for i, f in enumerate(FEATS):
        a = auroc(X[:, i], y)
        null = [auroc(X[:, i], p) for p in perms]
        null = [v for v in null if v is not None]
        # report the stronger direction, with the null taken the same way
        flip = a < 0.5
        a2 = 1 - a if flip else a
        n2 = [1 - v if flip else v for v in null]
        out[f] = {"auroc": round(a, 3), "direction": "lower_predicts_flag" if flip else "higher_predicts_flag",
                  "auroc_stronger_dir": round(a2, 3), "null95": round(float(np.percentile(n2, 95)), 3),
                  "flag": bool(a2 > 0.6 and a2 > np.percentile(n2, 95))}
    Xs = (X - X.mean(0)) / (X.std(0) + 1e-9)
    a = cv_auc(Xs, y, g)
    null = [cv_auc(Xs, perm_within(y, gp, rng), g) for _ in range(n_perm_cv)]
    out["all_features_grouped_cv"] = {"auroc": round(a, 3), "null95": round(float(np.percentile(null, 95)), 3),
                                      "flag": bool(a > 0.6 and a > np.percentile(null, 95))}
    style = [FEATS.index(f) for f in STYLE]
    a = cv_auc(Xs[:, style], y, g)
    null = [cv_auc(Xs[:, style], perm_within(y, gp, rng), g) for _ in range(n_perm_cv)]
    out["style_only_grouped_cv"] = {"features": STYLE, "auroc": round(a, 3), "null95": round(float(np.percentile(null, 95)), 3),
                                    "flag": bool(a > 0.6 and a > np.percentile(null, 95))}
    if all("group2" in r for r in rows):
        g2 = np.array([r["group2"] for r in rows])
        i = FEATS.index("log_chars"); a = auroc(X[:, i], y)
        null = [auroc(X[:, i], perm_within(y, g2, rng)) for _ in range(n_perm)]
        null = [v for v in null if v is not None]
        flip = a < 0.5
        out["log_chars_null_within_prompt_and_model"] = {"auroc_stronger_dir": round(1 - a if flip else a, 3),
            "null95": round(float(np.percentile([1 - v if flip else v for v in null], 95)), 3)}
        a = cv_auc(Xs[:, style], y, g)
        null = [cv_auc(Xs[:, style], perm_within(y, g2, rng), g) for _ in range(n_perm_cv)]
        out["style_only_null_within_prompt_and_model"] = {"auroc": round(a, 3), "null95": round(float(np.percentile(null, 95)), 3),
                                                          "flag": bool(a > 0.6 and a > np.percentile(null, 95))}
    out["positive_rate_with_feature"] = {
        f: {"with": round(float(y[X[:, i] > 0].mean()), 3) if (X[:, i] > 0).any() else None,
            "without": round(float(y[X[:, i] == 0].mean()), 3) if (X[:, i] == 0).any() else None,
            "share_with": round(float((X[:, i] > 0).mean()), 3)}
        for i, f in enumerate(FEATS) if f != "log_chars"}
    return out


def nudged(cache, rng):
    resp = {}
    for name in NUD_LOGS:
        p = fetch(NUD, f"logs/full_v1/{name}", cache, binary=True)
        z = zipfile.ZipFile(p)
        model = json.loads(z.read("header.json"))["eval"]["model"]
        for n in z.namelist():
            if n.startswith("samples/"):
                d = json.loads(z.read(n))
                resp[(model, d["id"])] = d["output"].get("completion", "") or ""
    jud = list(csv.DictReader(io.StringIO(fetch(NUD, "results/v1/judgments.csv", cache))))
    hum = [json.loads(l) for l in fetch(NUD, "results/v1/human_labels.jsonl", cache).splitlines() if l.strip()]
    hl = {(h["model"], h["cell"]): int(h["label"]) for h in hum}
    cells = defaultdict(dict); cat = {}
    for r in jud:
        k = (r["model"], r["cell"])
        cat[k] = r["category"]
        if r["invalid"] != "1" and r["dark_pattern"] != "":
            cells[k][r["judge"].split("/")[-1]] = int(r["dark_pattern"])
    judges = sorted({j for d in cells.values() for j in d})
    rows = defaultdict(list)
    for k, d in cells.items():
        if k not in resp:
            continue
        row = {"feats": feats(resp[k]), "group": k[1].split("|")[1], "group2": k[1].split("|")[1] + "|" + k[0], "human": hl.get(k)}
        for j in judges:
            row[j] = d.get(j)
        row["majority"] = int(sum(d.values()) >= 2) if len(d) == 3 else None
        rows[cat[k]].append(row)
    res = {"source": f"{NUD[0]}@{NUD[1][:7]}", "licence": "MIT", "n_responses": sum(len(v) for v in rows.values()),
           "n_matched_human": sum(r["human"] is not None for v in rows.values() for r in v), "by_category": {}}
    for c in sorted(rows):
        res["by_category"][c] = {lab: analyse(rows[c], lab, rng) for lab in ["majority"] + judges}
    allh = [r for v in rows.values() for r in v if r["human"] is not None]
    res["human_labels_all_categories"] = {"human": analyse(allh, "human", rng, n_perm_cv=100),
                                          "majority_same_items": analyse(allh, "majority", rng, n_perm_cv=100)}
    res["human_labels_note"] = "100 labels sampled 50 judge-disagreement, 25 all-yes, 25 all-no; unweighted here"
    return res


def revisited(cache, rng):
    out = {"source": f"{REV[0]}@{REV[1][:7]}", "licence": "none declared; aggregates only", "sets": {}}
    for setname, data, key in (("handlabel_150", "data/results/handlabel/labels_adjudicated.csv", "data/results/handlabel/key.csv"),
                               ("sneaking_brandbias_100", "data/results/handlabel/sneaking_brandbias_auditing.csv", "data/results/handlabel/sneaking_brandbias_auditing_key.csv")):
        d = list(csv.DictReader(io.StringIO(fetch(REV, data, cache))))
        k = {r["key"]: r for r in csv.DictReader(io.StringIO(fetch(REV, key, cache)))}
        rows = defaultdict(list)
        for r in d:
            kk = k[r["key"]]
            # each prompt appears about once in these samples, so permute across the whole category
            row = {"feats": feats(r["response"]), "group": kk["sample_id"], "permgroup": "all",
                   "human": int(r["label_present_0_or_1"]) if r["label_present_0_or_1"] in ("0", "1") else None,
                   "majority": int(int(kk["n_judges_flagged"]) >= 2)}
            for j in ("gpt55", "opus46", "gemini31pro"):
                row[j] = int(kk[j]) if kk[j] in ("0", "1") else None
            rows[r["category"]].append(row)
        out["sets"][setname] = {c: {lab: analyse(rows[c], lab, rng, n_perm=1000, n_perm_cv=100)
                                    for lab in ("human", "majority", "gpt55", "opus46", "gemini31pro")}
                                for c in sorted(rows)}
    out["note"] = "Sampled to over-represent judge disagreement, so AUROCs are within that sample, not the category"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="baselines_checks.json")
    a = ap.parse_args()
    rng = np.random.default_rng(0)
    cache = Path(a.cache)
    out = {"features": FEATS, "patterns": PAT, "who_gets_nudged": nudged(cache, rng), "darkbench_revisited": revisited(cache, rng)}
    Path(a.out).write_text(json.dumps(out, indent=1))
    for c, d in out["who_gets_nudged"]["by_category"].items():
        m = d["majority"]
        print("nudged", c, m["n"], m["positives"], {f: (m[f]["auroc"], m[f]["null95"], m[f]["flag"]) for f in FEATS}, m["all_features_grouped_cv"], m["style_only_grouped_cv"], m.get("log_chars_null_within_prompt_and_model"), m.get("style_only_null_within_prompt_and_model"))
    for lab, h in out["who_gets_nudged"]["human_labels_all_categories"].items():
        print("nudged human-set", lab, h["n"], h["positives"], {f: (h[f]["auroc"], h[f]["null95"]) for f in FEATS}, h["all_features_grouped_cv"], h["style_only_grouped_cv"])
    for s, d in out["darkbench_revisited"]["sets"].items():
        for c, labs in d.items():
            for lab, m in labs.items():
                if "skipped" in m:
                    continue
                print("rev", s, c, lab, m["n"], m["positives"], {f: m[f]["auroc"] for f in FEATS}, m["all_features_grouped_cv"]["auroc"])


if __name__ == "__main__":
    main()
