"""HarmBench classifier against HarmBench's own human labels: where it disagrees, and what surface
features predict its verdict.

Data: `data/classifier_val_sets/text_behaviors_val_set.json` in centerforaisafety/HarmBench at a
pinned commit. It holds 602 completions (301 behaviours x 2) with three human labels
(`human_0..2`) and the verdicts of several judges. `cls` is taken to be
cais/HarmBench-Llama-2-13b-cls (its agreement with the human majority is checked against the
paper's 93.2%); `cls_mistral` is the validation classifier cais/HarmBench-Mistral-7b-val-cls.
No model is run. Nothing downloaded is imported or executed. Outputs hold ids, categories and
aggregates only, never completion or behaviour text.

Checks:
  6  agreement of `cls` with the human majority, overall and by behaviour category, attack
     method, target model and response property (length, refusal phrase position,
     refusal-then-comply, code, lists, low overlap with the behaviour, degenerate text);
     compared with human-human agreement.
  1  content-blind features (length, refusal phrases, code, lists) as predictors of the `cls`
     verdict and of the human majority: single-feature AUROCs, a cross-validated logistic model,
     within-behaviour permutation nulls, and the conditional test (does length predict `cls`
     among items humans call negative?).

Usage:
    python -I check_harmbench.py [--cache ../data] [--out harmbench_checks.json]
"""
import argparse, json, math, re, urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

HB_COMMIT = "8e1604d1171fe8a48d8febecd22f600e462bdcdd"  # centerforaisafety/HarmBench main, 2024-08-05
HB = f"https://raw.githubusercontent.com/centerforaisafety/HarmBench/{HB_COMMIT}/"
FILES = {
    "val_set": ("data/classifier_val_sets/text_behaviors_val_set.json",
                "e740727b6874e492063e097122a9916833d57f9bd2ce3e86713ec188741a41c8"),
    "behaviors_all": ("data/behavior_datasets/harmbench_behaviors_text_all.csv",
                      "8d81accedd38eaaf8b760618622bb888417d1fd0c86eba65c427a16f1cbb4afc"),
    "behaviors_test": ("data/behavior_datasets/harmbench_behaviors_text_test.csv",
                       "75d257b3e7428c52eb7b0154318f455af3e01b09a3794b5e2f3d36054f3c0e29"),
    "behaviors_val": ("data/behavior_datasets/harmbench_behaviors_text_val.csv",
                      "7bfaaa5e2b9b95002c89e2d33c019f58e9e8496e2fc65d368f1eeb8179e69534"),
}
JUDGES = ["cls", "cls_mistral", "gpt-4-0613", "gpt-4-1106-preview", "llama_guard", "advbench",
          "GPTFuzz", "mixtral", "chatglm", "gpt-3.5-turbo-0613", "PAIR_gpt-4-0613"]
SEED = 0


def fetch(cache, key):
    import hashlib
    rel, sha = FILES[key]
    p = Path(cache) / "hb" / Path(rel).name
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(HB + rel, timeout=120) as r:
            p.write_bytes(r.read())
    got = hashlib.sha256(p.read_bytes()).hexdigest()
    assert got == sha, f"{p}: sha256 {got} != pinned {sha}"
    return p


# ------------------------------------------------------------------ response features (shared)
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


# ------------------------------------------------------------------ stats
def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def auroc(score, y):
    score, y = np.asarray(score, float), np.asarray(y, int)
    pos, neg = score[y == 1], score[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    r = pd.Series(np.concatenate([pos, neg])).rank().to_numpy()
    return (r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def cluster_boot(df, group, fn, B=1000, seed=SEED):
    rng = np.random.default_rng(seed)
    g = df[group].to_numpy()
    ug = np.unique(g)
    idx = {k: np.flatnonzero(g == k) for k in ug}
    out = []
    for _ in range(B):
        s = rng.choice(ug, len(ug), replace=True)
        ii = np.concatenate([idx[k] for k in s])
        v = fn(df.iloc[ii])
        if v is not None and not (isinstance(v, float) and np.isnan(v)):
            out.append(v)
    out = np.array(out)
    return [round(float(np.percentile(out, 2.5)), 4), round(float(np.percentile(out, 97.5)), 4)] if len(out) else None


def perm_within(y, groups, rng):
    y = y.copy()
    for g in np.unique(groups):
        ii = np.flatnonzero(groups == g)
        y[ii] = y[rng.permutation(ii)]
    return y


def r4(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 4)


def agree_block(sub, judge="cls", gold="human_maj"):
    n = len(sub)
    a = int((sub[judge] == sub[gold]).sum())
    neg, pos = sub[sub[gold] == 0], sub[sub[gold] == 1]
    fp, fn = int((neg[judge] == 1).sum()), int((pos[judge] == 0).sum())
    return dict(n=n, human_pos=int(sub[gold].sum()), judge_pos=int(sub[judge].sum()),
                agreement=r4(a / n) if n else None, agreement_ci=wilson(a, n),
                false_pos=fp, fpr=r4(fp / len(neg)) if len(neg) else None, fpr_ci=wilson(fp, len(neg)),
                false_neg=fn, fnr=r4(fn / len(pos)) if len(pos) else None, fnr_ci=wilson(fn, len(pos)),
                judge_minus_human_rate=r4((sub[judge].mean() - sub[gold].mean())) if n else None,
                ppv=r4(1 - fp / sub[judge].sum()) if sub[judge].sum() else None,
                npv=r4(1 - fn / (n - sub[judge].sum())) if n - sub[judge].sum() else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="../data")
    ap.add_argument("--out", default="harmbench_checks.json")
    args = ap.parse_args()

    val = json.loads(fetch(args.cache, "val_set").read_text(encoding="utf-8"))
    beh = pd.read_csv(fetch(args.cache, "behaviors_all"))
    test_ids = set(pd.read_csv(fetch(args.cache, "behaviors_test")).BehaviorID)
    val_ids = set(pd.read_csv(fetch(args.cache, "behaviors_val")).BehaviorID)
    bmap = beh.set_index("BehaviorID")

    rows = []
    for bid, items in val.items():
        for j, e in enumerate(items):
            prompt = bmap.Behavior.get(bid, "") if bid in bmap.index else ""
            r = dict(item=f"{bid}#{j}", behavior_id=bid, method=e["method"], experiment=e["experiment"],
                     semantic=bmap.SemanticCategory.get(bid, "unknown") if bid in bmap.index else "unknown",
                     functional=bmap.FunctionalCategory.get(bid, "unknown") if bid in bmap.index else "unknown",
                     split="test" if bid in test_ids else "val" if bid in val_ids else "not_in_release")
            for k in ["human_0", "human_1", "human_2"]:
                r[k] = int(e[k])
            for k in JUDGES:
                v = e[k]
                if k == "gpt-3.5-turbo-0613":
                    v = int(str(v).strip().lower().startswith("yes"))
                elif k == "PAIR_gpt-4-0613":
                    v = int(int(re.findall(r"\[\[(\d+)\]\]", v)[0]) == 10)
                r[k] = int(v)
            r.update(features(e["generation"], prompt))
            rows.append(r)
    df = pd.DataFrame(rows)
    df["human_votes"] = df[["human_0", "human_1", "human_2"]].sum(axis=1)
    df["human_maj"] = (df.human_votes >= 2).astype(int)
    df["unanimous"] = df.human_votes.isin([0, 3])
    out = {"pins": {"harmbench_commit": HB_COMMIT, "files": {k: v[0] for k, v in FILES.items()},
                    "sha256": {k: v[1] for k, v in FILES.items()},
                    "classifier_model": "cais/HarmBench-Llama-2-13b-cls @ bda705349d1144fa618770bea64d99ce54e3835b (not run)",
                    "val_classifier_model": "cais/HarmBench-Mistral-7b-val-cls @ 51182c7cdaf9b2e5f05b745b81b047b67e7384a1 (not run)"},
           "n_items": len(df), "n_behaviors": int(df.behavior_id.nunique()),
           "behaviors_by_split": df.drop_duplicates("behavior_id").split.value_counts().to_dict()}

    # ---------------- check 6: how the labelled set was drawn, and the paper's numbers
    per_beh = df.groupby("behavior_id")
    pattern = per_beh.cls.apply(lambda s: tuple(s.tolist()))
    out["check6_selection"] = {
        "note": "paper B.5.1: 600 completions, one positive and one negative per behaviour as identified by our classifier; GPT-4 prompts were then tuned on this set and distillation rounds tracked accuracy on it",
        "behaviors_with_one_cls_pos_one_cls_neg": int(per_beh.cls.sum().eq(1).sum()),
        "behaviors_cls_pattern_first_second": {str(k): int(v) for k, v in pattern.value_counts().items()},
        "items_where_cls_differs_from_cls_mistral": int((df.cls != df.cls_mistral).sum()),
        "cls_errors": int((df.cls != df.human_maj).sum()), "cls_mistral_errors": int((df.cls_mistral != df.human_maj).sum()),
        "errors_shared": int(((df.cls != df.human_maj) & (df.cls_mistral != df.human_maj)).sum()),
        "paper_claims": {"test_classifier_agreement": 0.932, "test_classifier_errors": 41,
                         "val_classifier_agreement": 0.886, "val_classifier_errors": 51, "shared_errors": 26,
                         "table3": {"standard": {"advbench": 71.14, "GPTFuzz": 77.36, "chatglm": 65.67, "llama_guard": 68.41, "PAIR_gpt-4-0613": 89.8, "cls": 94.53},
                                    "contextual": {"advbench": 67.5, "GPTFuzz": 71.5, "chatglm": 62.5, "llama_guard": 64.0, "PAIR_gpt-4-0613": 85.5, "cls": 90.5}}},
        "released_by_functional": {f: {j: r4(100 * (g[j] == g.human_maj).mean()) for j in JUDGES}
                                   for f, g in df.groupby("functional") if f != "unknown"},
    }
    # ASR implied by the released PPV/NPV, if the selected items stand for all items with that verdict
    ppv = 1 - ((df.cls == 1) & (df.human_maj == 0)).sum() / (df.cls == 1).sum()
    npv = 1 - ((df.cls == 0) & (df.human_maj == 1)).sum() / (df.cls == 0).sum()
    out["check6_implied_asr"] = {"ppv": r4(ppv), "npv": r4(npv),
                                 "cls_asr_to_human_asr": {str(a): r4(a * ppv + (1 - a) * (1 - npv)) for a in [0.1, 0.2, 0.3, 0.5, 0.7, 0.9]},
                                 "caveat": "assumes the one positive and one negative picked per behaviour are typical of all completions with that verdict; the pick rule is not documented"}

    # ---------------- check 6: agreement
    hh = []
    for a, b in [("human_0", "human_1"), ("human_0", "human_2"), ("human_1", "human_2")]:
        hh.append((df[a] == df[b]).mean())
    judge_vs_ind = {j: r4(np.mean([(df[j] == df[h]).mean() for h in ["human_0", "human_1", "human_2"]])) for j in JUDGES}
    # leave-one-out: each human against the majority of the other two, on items where the other two agree
    loo = []
    for h in ["human_0", "human_1", "human_2"]:
        o = [x for x in ["human_0", "human_1", "human_2"] if x != h]
        m = df[o[0]] == df[o[1]]
        loo.append(((df.loc[m, h] == df.loc[m, o[0]]).mean(), (df.loc[m, "cls"] == df.loc[m, o[0]]).mean()))
    out["check6_overall"] = {
        "judges_vs_majority": {j: agree_block(df, j) for j in JUDGES},
        "human_pairwise_agreement_mean": r4(np.mean(hh)),
        "judge_vs_individual_human_mean": judge_vs_ind,
        "loo_human_vs_other_two_when_they_agree": r4(np.mean([x[0] for x in loo])),
        "loo_cls_vs_other_two_when_they_agree": r4(np.mean([x[1] for x in loo])),
        "cls_on_unanimous": agree_block(df[df.unanimous]),
        "cls_on_split_2_1": agree_block(df[~df.unanimous]),
        "share_split_2_1": r4((~df.unanimous).mean()),
        "cls_agreement_ci_cluster_by_behavior": cluster_boot(df, "behavior_id", lambda s: float((s.cls == s.human_maj).mean())),
    }
    strata = {}
    for col in ["semantic", "functional", "method", "experiment", "split"]:
        strata[col] = {str(k): agree_block(g) for k, g in df.groupby(col)}
    q = pd.qcut(df.n_words, 4, labels=False)
    edges = [int(x) for x in np.percentile(df.n_words, [0, 25, 50, 75, 100])]
    strata["length_quartile"] = {f"Q{i+1} ({edges[i]}-{edges[i+1]} words)": agree_block(df[q == i]) for i in range(4)}
    props = {
        "very_short (<50 words)": df.n_words < 50,
        "very_long (>=350 words)": df.n_words >= 350,
        "refusal_open (refusal phrase in first 150 chars)": df.refusal_open,
        "refuse_then_comply (refusal_open and >=150 words)": df.refuse_then_comply,
        "refusal_open and <150 words": df.refusal_open & ~df.refuse_then_comply,
        "refusal_late (refusal phrase only after 150 chars)": df.refusal_late,
        "no_refusal_phrase": ~df.refusal_any,
        "code": df.code,
        "list (>=3 list lines)": df.list,
        "low_overlap_with_behavior (<0.25)": df.overlap < 0.25,
        "degenerate (repetitive or non-ascii)": df.degenerate,
        "contextual and refusal_open": (df.functional == "contextual") & df.refusal_open,
    }
    strata["response_property"] = {k: agree_block(df[m]) for k, m in props.items()}
    out["check6_strata"] = strata
    # which strata fall below the scope's 90% flag line with the interval wholly below it
    flagged = []
    for col, d in strata.items():
        for k, b in d.items():
            if b["n"] >= 20 and b["agreement_ci"][1] is not None and b["agreement_ci"][1] < 0.90:
                flagged.append({"stratum": f"{col}={k}", "n": b["n"], "agreement": b["agreement"],
                                "ci": b["agreement_ci"], "fpr": b["fpr"], "fnr": b["fnr"]})
    out["check6_flagged_strata_ci_below_0.90"] = flagged
    errs = df[df.cls != df.human_maj]
    out["check6_error_items"] = {
        "false_pos_ids": errs[errs.cls == 1].item.tolist(), "false_neg_ids": errs[errs.cls == 0].item.tolist(),
        "errors_split_vote_share": r4((~errs.unanimous).mean()),
        "false_pos_with_one_human_vote": int(((errs.cls == 1) & (errs.human_votes == 1)).sum()),
        "false_neg_with_two_human_votes": int(((errs.cls == 0) & (errs.human_votes == 2)).sum()),
    }
    # mistakes shared with the validation classifier (same family)
    out["check6_cls_and_cls_mistral_same_error"] = int(((df.cls != df.human_maj) & (df.cls_mistral == df.cls)).sum())

    # ---------------- check 1: content-blind baselines
    rng = np.random.default_rng(SEED)
    groups = df.behavior_id.to_numpy()
    feats = ["n_words", "refusal_any", "refusal_open", "refusal_count", "code", "list", "overlap"]
    single = {}
    for f in feats:
        x = df[f].astype(float).fillna(0).to_numpy()
        row = {}
        for tgt in ["cls", "human_maj"]:
            y = df[tgt].to_numpy()
            a = auroc(x, y)
            null = [auroc(x, perm_within(y, groups, rng)) for _ in range(1000)]
            row[tgt] = {"auroc": r4(a), "null95": r4(np.percentile(np.abs(np.array(null) - 0.5) + 0.5, 95))}
        row["diff_cls_minus_human"] = r4(row["cls"]["auroc"] - row["human_maj"]["auroc"])
        row["diff_ci"] = cluster_boot(df, "behavior_id",
                                      lambda s, f=f: float(auroc(s[f].astype(float).fillna(0), s.cls) - auroc(s[f].astype(float).fillna(0), s.human_maj)))
        single[f] = row
    out["check1_single_feature_auroc"] = single

    X = df[["log_words", "refusal_any", "refusal_open", "refusal_count", "code", "list"]].astype(float).to_numpy()
    gkf = GroupKFold(n_splits=5)

    def oof(y):
        p = np.zeros(len(y))
        for tr, te in gkf.split(X, y, groups):
            m = LogisticRegression(max_iter=2000).fit(X[tr], y[tr])
            p[te] = m.predict_proba(X[te])[:, 1]
        return p
    lr = {}
    for tgt in ["cls", "human_maj"] + [h for h in ["human_0", "human_1", "human_2"]]:
        y = df[tgt].to_numpy()
        p = oof(y)
        null = None
        if tgt in ("cls", "human_maj"):
            null = []
            for _ in range(200):
                yp = perm_within(y, groups, rng)
                null.append(auroc(oof(yp), yp))
        lr[tgt] = {"oof_auroc": r4(auroc(p, y)), "oof_accuracy_at_0.5": r4(((p > 0.5) == y).mean()),
                   "null95": r4(np.percentile(null, 95)) if null else None}
    lr["judges_auroc_vs_human_maj_for_comparison"] = {j: r4(auroc(df[j], df.human_maj)) for j in JUDGES}
    lr["note"] = "features: log words, any refusal phrase, refusal phrase in first 150 chars, refusal count, code, list; 5-fold GroupKFold by behaviour"
    out["check1_logistic_content_blind"] = lr

    # conditional: does length predict cls among items the humans call negative / positive?
    cond = {}
    for gval, name in [(0, "human_maj=0"), (1, "human_maj=1")]:
        s = df[df.human_maj == gval]
        y = s.cls.to_numpy()
        cond[name] = {"n": len(s), "cls_pos": int(y.sum()),
                      "auroc_words_for_cls": r4(auroc(s.n_words, y)),
                      "auroc_refusal_open_for_cls": r4(auroc(s.refusal_open.astype(float), y)),
                      "ci_words": cluster_boot(s, "behavior_id", lambda t: float(auroc(t.n_words, t.cls)))}
    # human analogue: among majority-negative items, does length predict one dissenting positive vote?
    s = df[df.human_votes <= 1]
    cond["human_analogue: votes 1 vs 0 among majority-negative"] = {
        "n": len(s), "with_one_vote": int((s.human_votes == 1).sum()),
        "auroc_words": r4(auroc(s.n_words, (s.human_votes == 1).astype(int)))}
    s = df[df.human_votes >= 2]
    cond["human_analogue: votes 3 vs 2 among majority-positive"] = {
        "n": len(s), "with_three_votes": int((s.human_votes == 3).sum()),
        "auroc_words": r4(auroc(s.n_words, (s.human_votes == 3).astype(int)))}
    # length-matched comparison: positive-rate by length quartile for cls and humans
    cond["positive_rate_by_length_quartile"] = {
        f"Q{i+1}": {"cls": r4(df[q == i].cls.mean()), "human_maj": r4(df[q == i].human_maj.mean()),
                    "mean_human_votes_over_3": r4(df[q == i].human_votes.mean() / 3)} for i in range(4)}
    out["check1_conditional"] = cond

    Path(args.out).write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    o6 = out["check6_overall"]["judges_vs_majority"]["cls"]
    print("cls agreement", o6["agreement"], o6["agreement_ci"], "fpr", o6["fpr"], "fnr", o6["fnr"])
    print("human pairwise", out["check6_overall"]["human_pairwise_agreement_mean"], "cls vs indiv", judge_vs_ind["cls"])
    print("flagged", json.dumps(flagged, indent=0))
    print(json.dumps(single, indent=0))
    print(json.dumps(lr, indent=0))
    print(json.dumps(cond, indent=0))


if __name__ == "__main__":
    main()
