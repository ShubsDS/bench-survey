"""StrongREJECT judges against StrongREJECT's released human labels.

Data (OSF, linked from the Makefile of dsbowen/strong_reject at a pinned commit):
  labelbox.csv        1,361 (forbidden prompt, jailbreak, model, response) rows with up to five
                      human Likert labels scaled to 0-1 and their median (`label_median`).
  labelbox_evals.csv  the same rows scored by ten evaluators (StrongREJECT rubric and fine-tuned,
                      HarmBench classifier, string matching, PAIR, GPT-4 judge, ...), no responses.
  strongreject_dataset.csv (current and 2024_02) from alexandrasouly/strongreject, for categories.
No model is run. Nothing downloaded is imported or executed. Outputs hold ids, categories and
aggregates only.

Checks:
  6  error (judge minus human median) per judge, overall and by category, jailbreak, target model
     and response property; leave-one-labeller-out human error as the reference; what the rubric's
     refusal flag does to responses humans gave credit.
  1  content-blind features (length, refusal phrases, code, lists) as predictors of the human median
     and of each judge; whether length moves a judge's score among responses humans scored 0.

Usage:
    python -I check_strongreject.py [--cache ../data] [--out strongreject_checks.json]
"""
import argparse, hashlib, json, math, re, urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold

SR_PKG_COMMIT = "7a551d5b440ec7b75d4f6f5bb7c1719965b76b47"  # dsbowen/strong_reject main, 2025-07-07 (Makefile names the OSF ids)
SR_DATA_COMMIT = "f7cad6c17e624e21d8df2278e918ae1dddb4cb56"  # alexandrasouly/strongreject main, 2024-11-03
RAW = f"https://raw.githubusercontent.com/alexandrasouly/strongreject/{SR_DATA_COMMIT}/"
FILES = {  # name: (url, sha256)
    "labelbox.csv": ("https://osf.io/download/jwmqe/?revision=1",
                     "7a5928a4f09b4cbfce274001873ccf095510d5a990f8be52e4323d4c069fbad2"),
    "labelbox_evals.csv": ("https://osf.io/download/92s8k/?revision=1",
                           "8b77df36bba0853c0763c5b651db87cc3a760d75a552df5f5cd8541bbffd413d"),
    "strongreject_dataset.csv": (RAW + "strongreject_dataset/strongreject_dataset.csv",
                                 "4dd70357e4ff8b5d0ba5ebafecab5d6dd5633ce8046e3dd1c8bd93e64de44381"),
    "strongreject_dataset_2024_02.csv": (RAW + "strongreject_dataset/previous_versions/2024_02/strongreject_dataset.csv", "6280fa699a0d8e7b55b55ebaed991e840d45a7595fd902403af1b25557c59d0b"),
}
MAIN = ["strongreject_rubric", "strongreject_finetuned", "harmbench", "string_matching"]
SEED = 0


def fetch(cache, name):
    url, sha = FILES[name]
    p = Path(cache) / "sr" / name
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=180) as r:
            p.write_bytes(r.read())
    got = hashlib.sha256(p.read_bytes()).hexdigest()
    if sha:
        assert got == sha, f"{p}: sha256 {got} != pinned {sha}"
    return p, got


# ------------------------------------------------------------------ features (same as check_harmbench.py)
REFUSAL = [
    "i'm sorry", "i am sorry", "i apologize", "my apologies", "as an ai", "as a language model",
    "as an assistant", "i cannot", "i can't", "i can not", "i'm not able to", "i am not able to",
    "i'm unable to", "i am unable to", "i will not", "i won't", "i must decline", "i must refuse",
    "i do not feel comfortable", "i'm not comfortable", "not appropriate", "not ethical",
    "unethical", "against my", "i'm really sorry", "i'm truly sorry", "cannot fulfill",
    "can't fulfill", "cannot assist", "can't assist", "cannot provide", "can't provide",
    "cannot help", "can't help", "i'd prefer not", "i refuse",
]
REFUSAL_RE = re.compile("|".join(re.escape(s) for s in REFUSAL))
CODE_LINE = re.compile(r"^\s*(def |class |import |from \S+ import |#include|function\s*\w*\s*\(|var |const |let |"
                       r"public |private |static |SELECT |INSERT |UPDATE |DROP |<\?php|\$\w+\s*=|for\s*\(|"
                       r"while\s*\(|if\s*\(|return\b|print\(|echo |sudo |curl |wget |chmod |nc |#!/)")
LIST_LINE = re.compile(r"^\s*(\d+[.)]|[-*•]|step \d+[:.]?)\s", re.I)
WORD = re.compile(r"[a-z][a-z']+")
STOP = set("""a an the and or of to in on for with by from at as is are be this that these those it its
your you their them they he she his her our we i me my write give generate create describe explain list
detailed instructions step steps how what which who make making use using about into some any more most
such than then there here also would could should will can just very well article post persuasive
message text code way ways""".split())


def norm(s):
    return str(s).replace("’", "'").replace("‘", "'").lower()


def features(text, prompt):
    text = "" if pd.isna(text) else str(text)
    t = norm(text).strip()
    words = t.split()
    n = len(words)
    m = [x.start() for x in REFUSAL_RE.finditer(t)]
    open_ref = bool(m) and m[0] < 150
    lines = text.splitlines()
    code = ("```" in text) or sum(bool(CODE_LINE.match(l)) for l in lines) >= 2
    lst = sum(bool(LIST_LINE.match(l)) for l in lines) >= 3
    pw = {w for w in WORD.findall(norm(prompt)) if len(w) >= 4 and w not in STOP}
    gw = {w[:5] for w in WORD.findall(t)}
    overlap = (sum(w[:5] in gw for w in pw) / len(pw)) if pw else np.nan
    uniq = len(set(words)) / n if n else 0.0
    nonascii = sum(ord(c) > 127 for c in text) / max(len(text), 1)
    return dict(n_words=n, log_words=math.log1p(n), refusal_any=bool(m), refusal_open=open_ref,
                refusal_late=bool(m) and not open_ref, refusal_count=len(m), code=code, list=lst,
                overlap=overlap, uniq_ratio=uniq, nonascii=nonascii,
                refuse_then_comply=open_ref and n >= 150,
                degenerate=(n >= 50 and uniq < 0.3) or nonascii > 0.3)


def r4(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 4)


def auroc(score, y):
    score, y = np.asarray(score, float), np.asarray(y, int)
    pos, neg = score[y == 1], score[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    r = pd.Series(np.concatenate([pos, neg])).rank().to_numpy()
    return (r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def sp(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if np.std(a) == 0 or np.std(b) == 0:
        return np.nan
    return spearmanr(a, b).statistic


def cluster_boot(df, group, fn, B=1000, seed=SEED):
    rng = np.random.default_rng(seed)
    g = df[group].to_numpy()
    ug = np.unique(g)
    idx = {k: np.flatnonzero(g == k) for k in ug}
    vals = []
    for _ in range(B):
        ii = np.concatenate([idx[k] for k in rng.choice(ug, len(ug), replace=True)])
        v = fn(df.iloc[ii])
        if v is not None and not np.isnan(v):
            vals.append(v)
    return [r4(np.percentile(vals, 2.5)), r4(np.percentile(vals, 97.5))] if vals else None


def jacc(a, b):
    a, b = set(norm(a).split()), set(norm(b).split())
    return len(a & b) / max(len(a | b), 1)


def err_block(sub, judges):
    o = {"n": len(sub), "human_mean": r4(sub.human.mean()), "human_zero_share": r4((sub.human == 0).mean())}
    for j in judges:
        e = sub[j] - sub.human
        z = sub[sub.human == 0]
        f = sub[sub.human == 1]
        o[j] = {"mean": r4(sub[j].mean()), "bias": r4(e.mean()), "mae": r4(e.abs().mean()),
                "mean_when_human_0": r4(z[j].mean()) if len(z) else None,
                "share_gt0_when_human_0": r4((z[j] > 0).mean()) if len(z) else None,
                "mean_when_human_1": r4(f[j].mean()) if len(f) else None}
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="../data")
    ap.add_argument("--out", default="strongreject_checks.json")
    args = ap.parse_args()
    shas = {}
    paths = {}
    for k in FILES:
        paths[k], shas[k] = fetch(args.cache, k)
    lab = pd.read_csv(paths["labelbox.csv"])
    ev = pd.read_csv(paths["labelbox_evals.csv"])
    cur = pd.read_csv(paths["strongreject_dataset.csv"])
    old = pd.read_csv(paths["strongreject_dataset_2024_02.csv"])

    key = ["forbidden_prompt", "jailbreak", "model"]
    lab = lab.reset_index().rename(columns={"index": "row"})
    wide = ev.pivot_table(index=key, columns="evaluator", values="score", aggfunc="first").reset_index()
    rub = ev[ev.evaluator == "strongreject_rubric"][key + ["refusal", "convincingness", "specificity", "judge_model"]]
    df = lab.merge(wide, on=key, how="left").merge(rub, on=key, how="left")
    judges = [c for c in wide.columns if c not in key]
    assert len(df) == len(lab) and df[judges].notna().all().all()
    df["human"] = df.label_median
    labs = [f"label_{i}" for i in range(5)]
    df["n_labels"] = df[labs].notna().sum(axis=1)

    # prompt id and category: exact (whitespace-normalised) match, else best word-Jaccard match
    pool = pd.concat([cur.assign(version="current", sr_row=cur.index), old.assign(version="2024_02", sr_row=old.index)])
    prompts = sorted(df.forbidden_prompt.unique())
    pmap = {}
    for i, p in enumerate(prompts):
        sc = pool.forbidden_prompt.map(lambda q: jacc(p, q))
        j = int(sc.to_numpy().argmax())
        best = pool.iloc[j]
        pmap[p] = dict(prompt_id=f"P{i:02d}", category=best.category if sc.iloc[j] >= 0.5 else "unmatched",
                       match_jaccard=r4(sc.iloc[j]), sr_version=best.version, sr_row=int(best.sr_row), source=best.source)
    for c in ["prompt_id", "category", "source"]:
        df[c] = df.forbidden_prompt.map(lambda p: pmap[p][c])
    feats = pd.DataFrame([features(r.response, r.forbidden_prompt) for r in df.itertuples()])
    df = pd.concat([df, feats], axis=1)

    out = {"pins": {"strong_reject_package_commit": SR_PKG_COMMIT, "strongreject_data_commit": SR_DATA_COMMIT,
                    "files": {k: v[0] for k, v in FILES.items()}, "sha256": shas,
                    "finetuned_model": "qylu4156/strongreject-15k-v1 @ 4bd893d32390d2cace4f067dc2e3ef5294fd78a2 (not run)",
                    "harmbench_model": "cais/HarmBench-Llama-2-13b-cls @ bda705349d1144fa618770bea64d99ce54e3835b (not run)"},
           "n_rows": len(df), "n_prompts": len(prompts),
           "judge_models_in_file": {e: g.judge_model.fillna("none").value_counts().to_dict() for e, g in ev.groupby("evaluator")},
           "prompt_match": {v["prompt_id"]: {k: v[k] for k in ["category", "match_jaccard", "sr_version", "sr_row", "source"]} for v in pmap.values()},
           "rows_by_model": df.model.value_counts().to_dict(), "rows_by_jailbreak": df.jailbreak.value_counts().to_dict(),
           "human_median_values": {str(k): int(v) for k, v in df.human.value_counts().sort_index().items()},
           "labels_per_row": {str(k): int(v) for k, v in df.n_labels.value_counts().sort_index().items()}}

    # ---------------- check 6: errors against the human median
    out["check6_overall"] = err_block(df, judges)
    out["check6_overall"]["spearman_with_human"] = {j: r4(sp(df[j], df.human)) for j in judges}
    out["check6_overall"]["auroc_for_human_gt0"] = {j: r4(auroc(df[j], (df.human > 0).astype(int))) for j in judges}
    out["check6_overall"]["auroc_for_human_ge_0.5"] = {j: r4(auroc(df[j], (df.human >= 0.5).astype(int))) for j in judges}
    # leave-one-labeller-out: labeller i against the median of the others, and each judge against the same median
    loo = {"human": []}
    loo.update({j: [] for j in MAIN})
    for r in df[df.n_labels >= 3].itertuples():
        vals = [getattr(r, l) for l in labs if not pd.isna(getattr(r, l))]
        for i in range(len(vals)):
            med = float(np.median(vals[:i] + vals[i + 1:]))
            loo["human"].append(abs(vals[i] - med))
            for j in MAIN:
                loo[j].append(abs(getattr(r, j) - med))
    out["check6_loo_mae_vs_median_of_other_labellers"] = {k: r4(np.mean(v)) for k, v in loo.items()}
    out["check6_loo_mae_vs_median_of_other_labellers"]["n_pairs"] = len(loo["human"])

    strata = {}
    for col in ["category", "jailbreak", "model"]:
        strata[col] = {str(k): err_block(g, MAIN) for k, g in df.groupby(col)}
    q = pd.qcut(df.n_words, 4, labels=False, duplicates="drop")
    edges = [int(x) for x in np.percentile(df.n_words, [0, 25, 50, 75, 100])]
    strata["length_quartile"] = {f"Q{i+1} ({edges[i]}-{edges[i+1]} words)": err_block(df[q == i], MAIN) for i in range(4)}
    props = {
        "very_short (<50 words)": df.n_words < 50,
        "very_long (>=350 words)": df.n_words >= 350,
        "refusal_open (refusal phrase in first 150 chars)": df.refusal_open,
        "refuse_then_comply (refusal_open and >=150 words)": df.refuse_then_comply,
        "refusal_late (refusal phrase only after 150 chars)": df.refusal_late,
        "no_refusal_phrase": ~df.refusal_any,
        "code": df.code, "list (>=3 list lines)": df.list,
        "low_overlap_with_prompt (<0.25)": df.overlap < 0.25,
        "degenerate (repetitive or non-ascii)": df.degenerate,
        "partial (human median strictly between 0 and 1)": (df.human > 0) & (df.human < 1),
    }
    strata["response_property"] = {k: err_block(df[m], MAIN) for k, m in props.items()}
    out["check6_strata"] = strata

    # rubric refusal flag: score is forced to 0 when the judge says "refused"
    rf = df.refusal == 1
    out["check6_rubric_refusal_flag"] = {
        "rows_flagged_refusal": int(rf.sum()),
        "rubric_score_when_flagged_max": r4(df.loc[rf, "strongreject_rubric"].max()),
        "flagged_with_human_gt0": int((rf & (df.human > 0)).sum()),
        "flagged_with_human_ge_0.5": int((rf & (df.human >= 0.5)).sum()),
        "flagged_with_human_eq_1": int((rf & (df.human == 1)).sum()),
        "human_gt0_rows": int((df.human > 0).sum()),
        "share_of_human_gt0_zeroed_by_flag": r4((rf & (df.human > 0)).sum() / (df.human > 0).sum()),
        "flagged_with_human_ge_0.5_by_property": {
            "refuse_then_comply": int((rf & (df.human >= 0.5) & df.refuse_then_comply).sum()),
            "refusal_open_short": int((rf & (df.human >= 0.5) & df.refusal_open & ~df.refuse_then_comply).sum()),
            "no_refusal_phrase": int((rf & (df.human >= 0.5) & ~df.refusal_any).sum())},
        "flagged_with_human_ge_0.5_by_jailbreak": df[rf & (df.human >= 0.5)].jailbreak.value_counts().to_dict(),
        "flagged_with_human_ge_0.5_rows": df[rf & (df.human >= 0.5)].row.tolist(),
        "not_flagged_but_human_0": int((~rf & (df.human == 0)).sum()),
        "not_flagged_but_human_0_mean_rubric": r4(df.loc[~rf & (df.human == 0), "strongreject_rubric"].mean()),
    }
    # responses humans scored >= 0.5 that a judge scores below 0.25, by jailbreak
    hi = df[df.human >= 0.5]
    out["check6_missed_when_human_ge_0.5"] = {
        "n_human_ge_0.5": len(hi),
        **{j: {"missed": int((hi[j] < 0.25).sum()), "share": r4((hi[j] < 0.25).mean()),
               "by_jailbreak": {k: [int((g[j] < 0.25).sum()), len(g)] for k, g in hi.groupby("jailbreak") if (g[j] < 0.25).sum() > 0}}
           for j in MAIN}}
    # human analogue: a single labeller below 0.25 where the median of the other labellers is >= 0.5
    miss, missj = [], {}
    for r in df[df.n_labels >= 3].itertuples():
        vals = [getattr(r, l) for l in labs if not pd.isna(getattr(r, l))]
        for i in range(len(vals)):
            if np.median(vals[:i] + vals[i + 1:]) >= 0.5:
                miss.append(vals[i] < 0.25)
                missj.setdefault(r.jailbreak, []).append(vals[i] < 0.25)
    out["check6_missed_when_human_ge_0.5"]["human_loo_single_labeller_miss_share"] = r4(np.mean(miss))
    out["check6_missed_when_human_ge_0.5"]["human_loo_by_jailbreak"] = {k: [int(sum(v)), len(v)] for k, v in missj.items()}
    lo = df[df.human == 0]
    out["check6_credited_when_human_0"] = {
        "n_human_0": len(lo),
        **{j: {"over_0.5": int((lo[j] >= 0.5).sum()), "share": r4((lo[j] >= 0.5).mean()),
               "by_jailbreak": {k: [int((g[j] >= 0.5).sum()), len(g)] for k, g in lo.groupby("jailbreak") if (g[j] >= 0.5).sum() > 0}}
           for j in MAIN}}

    # largest errors by row id (ids only)
    out["check6_largest_errors"] = {j: {"over": df.assign(e=df[j] - df.human).nlargest(15, "e")[["row", "prompt_id", "jailbreak"]].to_dict("records"),
                                        "under": df.assign(e=df[j] - df.human).nsmallest(15, "e")[["row", "prompt_id", "jailbreak"]].to_dict("records")}
                                    for j in MAIN}

    # ---------------- check 1: content-blind features
    groups = df.prompt_id.to_numpy()
    targets = ["human"] + judges
    single = {}
    for f in ["n_words", "refusal_any", "refusal_open", "refusal_count", "code", "list", "overlap"]:
        x = df[f].astype(float).fillna(0)
        row = {t: r4(sp(x, df[t])) for t in targets}
        for j in MAIN:
            row[f"diff_{j}_minus_human"] = r4(row[j] - row["human"])
            row[f"diff_{j}_minus_human_ci"] = cluster_boot(df, "prompt_id", lambda s, f=f, j=j: sp(s[f].astype(float).fillna(0), s[j]) - sp(s[f].astype(float).fillna(0), s.human))
        single[f] = row
    out["check1_single_feature_spearman"] = single

    X = df[["log_words", "refusal_any", "refusal_open", "refusal_count", "code", "list"]].astype(float).to_numpy()
    gkf = GroupKFold(n_splits=5)
    rng = np.random.default_rng(SEED)

    def oof(y):
        p = np.zeros(len(y))
        for tr, te in gkf.split(X, y, groups):
            p[te] = Ridge(alpha=1.0).fit(X[tr], y[tr]).predict(X[te])
        return p
    reg = {}
    for t in ["human"] + MAIN:
        y = df[t].to_numpy(float)
        p = oof(y)
        null = []
        for _ in range(200):
            yp = y.copy()
            for g in np.unique(groups):
                ii = np.flatnonzero(groups == g)
                yp[ii] = yp[rng.permutation(ii)]
            null.append(sp(oof(yp), yp))
        reg[t] = {"oof_spearman": r4(sp(p, y)), "oof_mae": r4(np.abs(p - y).mean()),
                  "null95_spearman": r4(np.percentile(null, 95)),
                  "auroc_for_gt0": r4(auroc(p, (y > 0).astype(int)))}
    reg["judges_auroc_for_human_gt0_for_comparison"] = {j: r4(auroc(df[j], (df.human > 0).astype(int))) for j in judges}
    reg["note"] = "ridge on log words, refusal phrase flags and count, code, list; 5-fold GroupKFold by prompt (39 prompts); null permutes the target within prompt"
    out["check1_ridge_content_blind"] = reg

    # tie-fair comparison: binarise each judge at the cut that gives the same positive rate as human>0,
    # then compare how well length and the content-blind logistic model predict each binary label
    from sklearn.linear_model import LogisticRegression
    rate = float((df.human > 0).mean())
    binz = {"human": (df.human > 0).astype(int).to_numpy()}
    for j in MAIN:
        cut = np.quantile(df[j], 1 - rate)
        binz[j] = (df[j] > cut).astype(int).to_numpy() if (df[j] > cut).mean() > 0 else (df[j] >= cut).astype(int).to_numpy()
    matched = {"human_gt0_rate": r4(rate)}
    for t, y in binz.items():
        p = np.zeros(len(y))
        for tr, te in gkf.split(X, y, groups):
            p[te] = LogisticRegression(max_iter=2000).fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
        matched[t] = {"positive_rate": r4(y.mean()), "auroc_words": r4(auroc(df.n_words, y)),
                      "auroc_refusal_open": r4(auroc(df.refusal_open.astype(float), y)),
                      "oof_logistic_auroc": r4(auroc(p, y)),
                      "agreement_with_human_bin": r4((y == binz["human"]).mean())}
    for j in MAIN:
        matched[f"diff_auroc_words_{j}_minus_human"] = r4(matched[j]["auroc_words"] - matched["human"]["auroc_words"])
    out["check1_rate_matched_binary"] = matched

    cond = {}
    for hv, name in [(0.0, "human=0"), (1.0, "human=1")]:
        s = df[df.human == hv]
        cond[name] = {"n": len(s)}
        for j in MAIN:
            cond[name][j] = {"spearman_words": r4(sp(s.n_words, s[j])),
                             "ci": cluster_boot(s, "prompt_id", lambda t, j=j: sp(t.n_words, t[j])),
                             "mean_by_length_quartile": [r4(s[pd.qcut(s.n_words, 4, labels=False, duplicates="drop") == i][j].mean()) for i in range(4)]}
    # human analogue: among rows with median 0, does length predict a dissenting labeller (any label > 0)?
    s = df[(df.human == 0) & (df.n_labels >= 3)]
    dissent = (s[labs].fillna(0) > 0).any(axis=1).astype(int)
    cond["human_analogue: any labeller >0 among median-0 rows"] = {"n": len(s), "with_dissent": int(dissent.sum()),
                                                                   "auroc_words": r4(auroc(s.n_words, dissent))}
    for j in MAIN:
        cond["human_analogue: any labeller >0 among median-0 rows"][f"auroc_words_for_{j}_gt0"] = r4(auroc(s.n_words, (s[j] > 0).astype(int)))
    out["check1_conditional"] = cond

    Path(args.out).write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print(json.dumps({k: out[k] for k in ["n_rows", "n_prompts", "check6_overall", "check6_loo_mae_vs_median_of_other_labellers",
                                         "check6_rubric_refusal_flag", "check1_single_feature_spearman",
                                         "check1_ridge_content_blind", "check1_rate_matched_binary", "check1_conditional"]}, indent=0, default=str))


if __name__ == "__main__":
    main()
