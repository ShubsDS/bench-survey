"""Content-blind baselines on SAD (check 1): can the key be picked without the model knowing
anything about itself?

SAD at LRudL/sad commit dfc5c983 (2024-12-14). Chance per task is the `random_chance` SAD's code
passes to each Task (0.5 for the two-choice tasks, 0.25 for stages_full).

Two-choice question tasks (facts_human_defaults, facts_llms, influence, and facts_which_llm per
model), each scored with a Wilson 95% interval, ties sharing credit:
  longest / shortest      the choice with more / fewer characters
  overlap                 the choice with the higher word Jaccard against the question
  negative                the choice that reads as a denial (starts with no / not, or contains
                          cannot, can't, don't, do not, n't, never, unable, not capable)
  always_no               among items whose two choices are exactly yes and no, answer no
  options_only            logistic regression over TF-IDF of the choice text alone (question
                          hidden), argmax per item, GroupKFold with near-duplicate questions (and,
                          for facts_which_llm, the same csv row across models) in one group; null
                          = same pipeline with the key swapped at random within each item
facts_which_llm also gets `generic_llm`: answer as the other 20 models' majority key (leave one
model out), i.e. as a typical 2024 LLM with no idea which one it is.

Stages tasks (the question is fixed; the text is the item): class balance, and a classifier on
seven surface features of the text (log length, newline rate, digit share, uppercase share, a
chat-turn marker, a lettered-choice marker, ends with "?") under stratified 5-fold CV with a
label-permutation null.

Self-recognition (model-specific items, from the released eval results of the plain variant):
  who: pick the entity whose text is longer / shorter / has more line breaks
  groups: match X and Y to the entities by nearest surface style (log length, newline rate,
          mean word length), no content

Answer position: share of each answer letter in the released results.

Usage: python -I check_baselines.py --cache data --out baseline_checks.json --perms 200
"""
import argparse, json, math, re, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import MaxAbsScaler, StandardScaler

from common import (CHANCE, PILES, SHA, acc, clusters, ensure, evalresults, load_evalresult, mcq_task,
                    norm, which_llm, wilson)

NEG = re.compile(r"^(no|not|nope|none|never)\b|\b(cannot|can't|can not|don't|do not|doesn't|does not|"
                 r"won't|wouldn't|isn't|aren't|haven't|n't|never|unable|not capable|not able|"
                 r"i'm not|i am not|i don't)\b", re.I)


def words(t):
    return set(norm(t).split())


def pick_rules(it):
    """Map rule name -> set of chosen choice indices (0 = right, 1.. = wrong) or None."""
    ch = it["right"] + it["wrong"]
    L = [len(c) for c in ch]
    q = words(it["q"])
    ov = [(len(q & words(c)) / len(q | words(c))) if q | words(c) else 0 for c in ch]
    neg = {i for i, c in enumerate(ch) if NEG.search(c.strip())}
    yn = sorted(norm(c) for c in ch) == ["no", "yes"]
    return {"longest": {i for i, x in enumerate(L) if x == max(L)},
            "shortest": {i for i, x in enumerate(L) if x == min(L)},
            "overlap": {i for i, x in enumerate(ov) if x == max(ov)},
            "negative": neg if 0 < len(neg) < len(ch) else None,
            "always_no": {i for i, c in enumerate(ch) if norm(c) == "no"} if yn else None}


def score_rules(items):
    out = {}
    for name in ("longest", "shortest", "overlap", "negative", "always_no"):
        hit, n = 0.0, 0
        for it in items:
            w = pick_rules(it)[name]
            if not w:
                continue
            n += 1
            hit += (0 in w) / len(w)
        out[name] = acc(hit, n) | {"share_of_items": round(n / len(items), 3)}
    return out


def options_only(items, groups, perms, seed=0, folds=5):
    """Two-choice options-only classifier. Each item contributes its choices as rows; label 1 on
    the keyed one. Scored per item by argmax. Null: key swapped at random within each item."""
    k = len(items[0]["right"]) + len(items[0]["wrong"])
    texts = [c for it in items for c in it["right"] + it["wrong"]]
    g = np.repeat(np.asarray(groups), k)
    nf = min(folds, len(set(groups)))
    splits = list(GroupKFold(n_splits=nf).split(texts, groups=g))

    def run(keys):
        y = np.zeros(len(texts), dtype=int)
        for i, kk in enumerate(keys):
            y[k * i + kk] = 1
        p = np.zeros(len(texts))
        for tr, te in splits:
            pipe = make_pipeline(TfidfVectorizer(sublinear_tf=True, ngram_range=(1, 2), min_df=2),
                                 MaxAbsScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
            pipe.fit([texts[i] for i in tr], y[tr])
            p[te] = pipe.predict_proba([texts[i] for i in te])[:, 1]
        hit = 0.0
        for i, kk in enumerate(keys):
            sc = p[k * i:k * i + k]
            top = np.flatnonzero(sc == sc.max())
            hit += (kk in set(top.tolist())) / len(top)
        return hit / len(items)

    a = run(np.zeros(len(items), dtype=int))  # choices are stored right-first; position never seen
    rng = np.random.default_rng(seed)
    null = [run(rng.integers(0, k, size=len(items))) for _ in range(perms)]
    return {"n": len(items), "groups": len(set(groups)), "accuracy": round(a, 3),
            "wilson_95": wilson(round(a * len(items)), len(items)), "null_permutations": perms,
            "null_mean": round(float(np.mean(null)), 3), "null_p95": round(float(np.quantile(null, .95)), 3),
            "p_value": round((1 + sum(x >= a for x in null)) / (1 + perms), 4)}


def stages_surface(items, labels, perms, seed=0):
    def feats(t):
        n = max(1, len(t))
        return [math.log(n), t.count("\n") / n * 100, sum(c.isdigit() for c in t) / n,
                sum(c.isupper() for c in t) / n,
                float(bool(re.search(r"^(user|human|assistant|ai)\s*:", t, re.I | re.M))),
                float(bool(re.search(r"^\s*\(?[A-D][\).]\s", t, re.M))), float(t.rstrip().endswith("?"))]
    X = np.array([feats(it["q"]) for it in items])
    y = np.array(labels)
    cv = StratifiedKFold(5, shuffle=True, random_state=seed)

    def run(yy):
        pred = np.empty(len(yy), dtype=object)
        for tr, te in cv.split(X, yy):
            m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(X[tr], yy[tr])
            pred[te] = m.predict(X[te])
        return float(np.mean(pred == yy))
    a = run(y)
    rng = np.random.default_rng(seed)
    null = [run(rng.permutation(y)) for _ in range(perms)]
    lens = defaultdict(list)
    for it, l in zip(items, labels):
        lens[l].append(len(it["q"]))
    return {"n": len(items), "accuracy": round(a, 3), "wilson_95": wilson(round(a * len(y)), len(y)),
            "null_mean": round(float(np.mean(null)), 3), "null_p95": round(float(np.quantile(null, .95)), 3),
            "p_value": round((1 + sum(x >= a for x in null)) / (1 + perms), 4),
            "median_chars_by_label": {k: int(np.median(v)) for k, v in sorted(lens.items())},
            "length_only": length_only(X[:, :1], y, cv)}


def length_only(X, y, cv):
    pred = np.empty(len(y), dtype=object)
    for tr, te in cv.split(X, y):
        m = LogisticRegression(max_iter=2000).fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
    a = float(np.mean(pred == y))
    return {"accuracy": round(a, 3), "wilson_95": wilson(round(a * len(y)), len(y))}


def generic_llm(per_model):
    """Leave-one-model-out majority key per csv row, as a policy for the held-out model."""
    keys = defaultdict(dict)
    for m, items in per_model.items():
        for it in items:
            keys[it["row"]][m] = norm(it["right"][0])
    out = {}
    tot_hit = tot_n = 0
    for m, items in per_model.items():
        hit = 0.0
        for it in items:
            others = Counter(v for mm, v in keys[it["row"]].items() if mm != m)
            ch = [norm(c) for c in it["right"] + it["wrong"]]
            best = max(others.values())
            tops = {v for v, c in others.items() if c == best}
            w = {i for i, c in enumerate(ch) if c in tops}
            if not w or len(w) == len(ch):
                hit += 1 / len(ch)
            else:
                hit += (0 in w) / len(w)
        out[m] = acc(hit, len(items))
        tot_hit += hit
        tot_n += len(items)
    vals = [v["accuracy"] for v in out.values()]
    return {"per_model": out, "pooled": acc(tot_hit, tot_n), "min": min(vals), "max": max(vals)}


def self_recognition(unz, variant="plain"):
    res = {}
    for q in ("who", "groups"):
        per = {}
        for p in evalresults(unz, "sad/self_recognition", f"self_recognition_{q}--{variant}--"):
            if " " in p.name.split("--")[2]:  # skip COT wrappers; same items as the plain model
                continue
            er = load_evalresult(p)
            model = p.name.split("--")[2]
            hits = defaultdict(float)
            n = 0
            for sr in er["sample_results"]:
                s = sr["sample"]
                v = s["extra_template_vars"]
                right = s["choices_right"][0]
                n += 1
                if q == "who":
                    me = 1 if "You are ENTITY 1" in right else 2
                    t = {1: v["train_text_1"], 2: v["train_text_2"]}
                    for name, f in (("longer", len), ("shorter", lambda x: -len(x)),
                                    ("more_newlines", lambda x: x.count("\n"))):
                        a, b = f(t[1]), f(t[2])
                        hits[name] += 0.5 if a == b else float((1 if a > b else 2) == me)
                else:
                    x_is_1 = right.startswith("TEXT X was created by ENTITY 1")
                    def sty(x):
                        w = x.split()
                        return np.array([math.log(1 + len(x)), x.count("\n") / max(1, len(x)) * 100,
                                         np.mean([len(z) for z in w]) if w else 0.0])
                    f1, f2, fx, fy = (sty(v[k]) for k in ("train_text_1", "train_text_2", "text_x", "text_y"))
                    d_same = np.linalg.norm(fx - f1) + np.linalg.norm(fy - f2)
                    d_swap = np.linalg.norm(fx - f2) + np.linalg.norm(fy - f1)
                    hits["nearest_style"] += 0.5 if d_same == d_swap else float((d_same < d_swap) == x_is_1)
            per[model] = {k: acc(h, n) for k, h in hits.items()} | {
                "released_accuracy": round(float(er["accuracy"]), 3)}
        res[f"self_recognition_{q}"] = per
    return res


def positions(unz):
    """Share of the most common correct answer in each released plain-variant result file with
    the full item count (a few files are one-item test runs and are skipped)."""
    from scipy.stats import binomtest
    out = {}
    for task, d in (("facts_human_defaults", "sad/facts/human_defaults"), ("facts_llms", "sad/facts/llms"),
                    ("facts_which_llm", "sad/facts/which_llm"), ("influence", "sad/influence"),
                    ("stages_full", "sad/stages/full"), ("stages_oversight", "sad/stages/oversight")):
        files = [p for p in evalresults(unz, d, f"{task}--plain--") if " " not in p.name.split("--")[2]]
        cs = [Counter(re.findall(r"^  output_correct: (.*)$", p.read_text(), re.M)) for p in files]
        full = max(sum(c.values()) for c in cs)
        cs = [c for c in cs if sum(c.values()) == full]
        tops = [c.most_common(1)[0][1] / full for c in cs]
        worst = max(cs, key=lambda c: c.most_common(1)[0][1])
        k = worst.most_common(1)[0][1]
        out[task] = {"full_result_files": len(cs), "items": full, "answer_options_seen": len(worst),
                     "max_share_of_one_answer": round(max(tops), 3), "min_share": round(min(tops), 3),
                     "binomial_p_of_max_vs_uniform": round(binomtest(k, full, 1 / len(worst)).pvalue, 4)}
    return out


def released(repo):
    """Released plain-variant scores per task from the repo's results csvs (COT wrappers dropped)."""
    import csv
    files = {"facts_human_defaults": "sad/facts/human_defaults/results.csv", "facts_llms": "sad/facts/llms/results.csv",
             "facts_which_llm": "sad/facts/which_llm/results.csv", "influence": "sad/influence/results.csv",
             "stages_full": "sad/stages/full/results.csv", "stages_oversight": "sad/stages/oversight/results.csv",
             "self_recognition_who": "sad/self_recognition/results_who.csv",
             "self_recognition_groups": "sad/self_recognition/results_groups.csv"}
    out = {}
    for t, f in files.items():
        with open(Path(repo) / f, newline="") as fh:
            rows = [r for r in csv.DictReader(fh) if r["variant"] == "plain" and not r["model"].startswith("COT")
                    and r["score"]]
        sc = {r["model"]: round(float(r["score"]), 3) for r in rows}
        out[t] = {"models": len(sc), "min": min(sc.values()), "max": max(sc.values()),
                  "median": round(float(np.median(list(sc.values()))), 3), "scores": sc,
                  "human_baseline": next((r["human_baseline"] for r in rows if r.get("human_baseline")), None)}
    return out


def mname(m):
    for pre in ("replicate_", "together_api_"):
        m = m.removeprefix(pre)
    return m.replace(".", "_")


def compare(res):
    """Released plain-variant scores against the content-blind numbers above."""
    rel = {t: {mname(m): v for m, v in x["scores"].items()} for t, x in res["released_plain_scores"].items()}
    t = res["tasks"]
    single = {"facts_human_defaults": ("options_only", t["facts_human_defaults"]["options_only"]["accuracy"]),
              "influence": ("options_only", t["influence"]["options_only"]["accuracy"]),
              "facts_llms": ("options_only", t["facts_llms"]["options_only"]["accuracy"]),
              "stages_full": ("surface_features", t["stages_full"]["surface_features"]["accuracy"]),
              "stages_oversight": ("surface_features", t["stages_oversight"]["surface_features"]["accuracy"])}
    out = {}
    for task, (name, v) in single.items():
        sc = rel[task]
        out[task] = {"baseline": name, "baseline_accuracy": v, "models": len(sc),
                     "models_scoring_below_baseline": sum(x < v for x in sc.values())}
    gl = {mname(m): x["accuracy"] for m, x in t["facts_which_llm"]["generic_llm"]["per_model"].items()}
    sc = rel["facts_which_llm"]
    out["facts_which_llm"] = {"baseline": "generic_llm (own model's items)", "models": len(sc),
                              "models_scoring_below_baseline": sum(sc[m] < gl[m] for m in sc if m in gl),
                              "per_model": {m: {"released": sc[m], "generic_llm": gl.get(m)} for m in sc}}
    for q, rule in (("self_recognition_who", "more_newlines"), ("self_recognition_groups", "nearest_style")):
        per = {mname(m): x[rule]["accuracy"] for m, x in t[q].items()}
        sc = rel[q]
        out[q] = {"baseline": rule, "range": [min(per.values()), max(per.values())], "models": len(sc),
                  "models_scoring_below_baseline": sum(sc[m] < per[m] for m in sc if m in per)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="baseline_checks.json")
    ap.add_argument("--perms", type=int, default=200)
    a = ap.parse_args()
    unz, hashes = ensure(a.cache)
    res = {"repo": "LRudL/sad", "commit": SHA, "chance": CHANCE, "zip_sha256": hashes, "tasks": {}}
    for t in ("facts_human_defaults", "facts_llms", "influence"):
        items = mcq_task(unz, t)
        if t == "influence":  # one item has identical right and wrong text; it carries no signal
            items = [it for it in items if norm(it["right"][0]) != norm(it["wrong"][0])]
        r = {"items": len(items), "rules": score_rules(items),
             "options_only": options_only(items, clusters([it["q"] for it in items]), a.perms)}
        groups_key = (lambda it: it["batch"]) if t == "facts_human_defaults" else (lambda it: it["splits"].get("cat"))
        if t != "facts_llms":
            by = defaultdict(list)
            for it in items:
                by[groups_key(it)].append(it)
            r["by_group"] = {str(k): {"items": len(v)} | score_rules(v) for k, v in sorted(by.items(), key=lambda kv: str(kv[0]))}
        res["tasks"][t] = r
        print(t, json.dumps(r["rules"]), r["options_only"]["accuracy"], r["options_only"]["null_p95"], flush=True)

    per_model, _ = which_llm(unz)
    pooled = [it for v in per_model.values() for it in v if norm(it["right"][0]) != norm(it["wrong"][0])
              and it["right"][0].strip()]
    wl = {"models": len(per_model), "items_per_model": len(next(iter(per_model.values()))),
          "pooled_items": len(pooled), "rules_pooled": score_rules(pooled),
          "rules_per_model_range": {}, "generic_llm": generic_llm(per_model),
          "options_only_pooled": options_only(pooled, [it["row"] for it in pooled], max(20, a.perms // 4))}
    for name in ("longest", "shortest", "overlap", "negative", "always_no"):
        vals = [score_rules(v)[name]["accuracy"] for v in per_model.values()]
        wl["rules_per_model_range"][name] = [min(vals), max(vals)]
    res["tasks"]["facts_which_llm"] = wl
    print("which_llm", wl["generic_llm"]["pooled"], wl["options_only_pooled"]["accuracy"], flush=True)

    for t in ("stages_full", "stages_oversight"):
        items = mcq_task(unz, t)
        labels = [it["right"][0] for it in items]
        src = defaultdict(Counter)
        for it in items:
            src[it["right"][0]][it["splits"].get("source")] += 1
        r = {"items": len(items), "label_counts": dict(Counter(labels)),
             "best_fixed_label": round(max(Counter(labels).values()) / len(items), 3),
             "sources_per_label": {k: len(v) for k, v in src.items()},
             "surface_features": stages_surface(items, labels, a.perms)}
        res["tasks"][t] = r
        print(t, r["surface_features"]["accuracy"], r["surface_features"]["null_p95"], flush=True)

    res["tasks"] |= self_recognition(unz)
    res["answer_position_released_results"] = positions(unz)
    res["released_plain_scores"] = released(Path(a.cache) / "repo")
    res["released_vs_baselines"] = compare(res)
    Path(a.out).write_text(json.dumps(res, indent=2) + "\n")


if __name__ == "__main__":
    main()
