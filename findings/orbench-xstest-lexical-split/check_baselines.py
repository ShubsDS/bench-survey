"""Check 1: can "safe" vs "unsafe/toxic" be read off surface cues?

Tasks (positive class = the set a model is meant to refuse):
  orb_hard   OR-Bench Hard-1K (1,319, labelled seemingly toxic but safe) vs OR-Bench-Toxic (655)
  orb_80k    a seeded sample of 5,000 OR-Bench-80K prompts not in Hard-1K vs OR-Bench-Toxic
  xstest     XSTest 250 safe vs 200 unsafe ("contrast_*") prompts

Detectors, each scored by AUROC with a 1,000-resample bootstrap interval:
  length_chars, length_words   prompt length, raw (direction chosen by sign; reported both ways)
  category_only                (OR-Bench) the released category tag, one-hot, cross-validated
  hedge_count                  count of words from a fixed lexicon written before looking at the
                               data (HEDGES below): words that announce benign intent. Higher =
                               more likely safe, so the score is minus the count.
  best_single_word             within each training fold, the one word (presence) with the largest
                               chi-square against the label; scored on the held-out fold
  bow_lr                       logistic regression on word 1-2-gram TF-IDF, 5-fold stratified CV
Operating point: for each score, the share of the safe set above the threshold that puts 90% of
the unsafe set above it (a "refuse if score > t" rule tuned to refuse 90% of the unsafe set).
Nulls: bow_lr and best_single_word rerun with the label permuted (--perms times); the 95th
percentile is reported. Length and hedge_count have no fitted parameters; their null is the AUROC
of the same score under permuted labels.

Usage: python -I check_baselines.py [--cache data] [--out baseline_checks.json] [--perms 200]
"""
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.feature_selection import chi2
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import OneHotEncoder

from common import OR_REV, XS_COMMIT, load_orbench, load_xstest

HEDGES = ["legal", "legally", "legitimate", "lawful", "ethical", "ethically", "safe", "safely",
          "responsible", "responsibly", "respectful", "respectfully", "harmless", "without",
          "consent", "permission", "fictional", "hypothetical", "hypothetically", "educational",
          "research", "understand", "awareness", "prevent", "protect", "ensure", "avoid",
          "appropriate", "constructive", "positive", "healthy", "compliance", "regulations"]
TOK = re.compile(r"[a-z']+")


def boot(y, s, n=1000, seed=0):
    rng = np.random.default_rng(seed)
    out = []
    idx = np.arange(len(y))
    for _ in range(n):
        b = rng.choice(idx, len(idx))
        if y[b].min() == y[b].max():
            continue
        out.append(roc_auc_score(y[b], s[b]))
    return [round(float(np.percentile(out, 2.5)), 3), round(float(np.percentile(out, 97.5)), 3)]


def op_point(y, s, recall=0.9):
    """Refusal rate on the safe set when the score's threshold refuses `recall` of the unsafe set."""
    t = np.quantile(s[y == 1], 1 - recall)
    return round(float((s[y == 0] >= t).mean()), 3)


def auc_entry(y, s, perms, seed=0):
    a = roc_auc_score(y, s)
    rng = np.random.default_rng(seed + 1)
    null = [roc_auc_score(rng.permutation(y), s) for _ in range(perms)]
    return {"auroc": round(float(a), 3), "ci95": boot(y, s),
            "null_p95": round(float(np.percentile(null, 95)), 3),
            "safe_refused_at_90pct_unsafe_refused": op_point(y, s)}


def cv_scores(texts, y, kind, cats=None, seed=0):
    skf = StratifiedKFold(5, shuffle=True, random_state=seed)
    s = np.zeros(len(y))
    for tr, te in skf.split(texts, y):
        if kind == "bow_lr":
            v = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
            Xtr = v.fit_transform([texts[i] for i in tr])
            m = LogisticRegression(C=4.0, max_iter=2000).fit(Xtr, y[tr])
            s[te] = m.predict_proba(v.transform([texts[i] for i in te]))[:, 1]
        elif kind == "best_single_word":
            v = CountVectorizer(binary=True, min_df=3)
            Xtr = v.fit_transform([texts[i] for i in tr])
            c, _ = chi2(Xtr, y[tr])
            c = np.nan_to_num(c)
            j = int(c.argmax())
            col = Xtr[:, j].toarray().ravel()
            sign = 1 if y[tr][col == 1].mean() > y[tr].mean() else -1
            s[te] = sign * v.transform([texts[i] for i in te])[:, j].toarray().ravel()
        elif kind == "category_only":
            enc = OneHotEncoder(handle_unknown="ignore")
            Xtr = enc.fit_transform(cats[tr].reshape(-1, 1))
            m = LogisticRegression(max_iter=2000).fit(Xtr, y[tr])
            s[te] = m.predict_proba(enc.transform(cats[te].reshape(-1, 1)))[:, 1]
    return s


def top_words(texts, y, k=15):
    v = CountVectorizer(binary=True, min_df=3)
    X = v.fit_transform(texts)
    c, _ = chi2(X, y)
    c = np.nan_to_num(c)
    vocab = np.array(v.get_feature_names_out())
    out = []
    for j in np.argsort(-c)[:k]:
        col = X[:, j].toarray().ravel()
        out.append({"word": str(vocab[j]), "chi2": round(float(c[j]), 1),
                    "rate_safe": round(float(col[y == 0].mean()), 3),
                    "rate_unsafe": round(float(col[y == 1].mean()), 3)})
    return out


def run_task(texts, y, cats, perms):
    y = np.asarray(y)
    r = {"n_safe": int((y == 0).sum()), "n_unsafe": int((y == 1).sum())}
    L = np.array([len(t) for t in texts], float)
    W = np.array([len(TOK.findall(t.lower())) for t in texts], float)
    H = np.array([sum(w in HEDGES for w in TOK.findall(t.lower())) for t in texts], float)
    r["length_chars_shorter_is_unsafe"] = auc_entry(y, -L, perms)
    r["length_words_shorter_is_unsafe"] = auc_entry(y, -W, perms)
    r["hedge_count"] = auc_entry(y, -H, perms)
    r["hedge_any_rate"] = {"safe": round(float((H[y == 0] > 0).mean()), 3),
                           "unsafe": round(float((H[y == 1] > 0).mean()), 3)}
    r["mean_chars"] = {"safe": round(float(L[y == 0].mean()), 1), "unsafe": round(float(L[y == 1].mean()), 1)}
    kinds = ["best_single_word", "bow_lr"] + (["category_only"] if cats is not None else [])
    for kind in kinds:
        s = cv_scores(texts, y, kind, None if cats is None else np.asarray(cats))
        e = {"auroc": round(float(roc_auc_score(y, s)), 3), "ci95": boot(y, s),
             "safe_refused_at_90pct_unsafe_refused": op_point(y, s)}
        rng = np.random.default_rng(7)
        np_ = perms if kind != "bow_lr" else max(20, perms // 4)
        null = [roc_auc_score(yp, cv_scores(texts, yp, kind, None if cats is None else np.asarray(cats), seed=i))
                for i, yp in enumerate(rng.permutation(y) for _ in range(np_))]
        e["null_p95"] = round(float(np.percentile(null, 95)), 3)
        e["null_perms"] = np_
        r[kind] = e
    r["top_chi2_words"] = top_words(texts, y)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="baseline_checks.json")
    ap.add_argument("--perms", type=int, default=200)
    a = ap.parse_args()
    orb = load_orbench(a.cache)
    xs = load_xstest(a.cache)
    h, t, e = orb["or-bench-hard-1k"], orb["or-bench-toxic"], orb["or-bench-80k"]
    res = {"sources": {"or_bench_revision": OR_REV, "xstest_commit": XS_COMMIT},
           "positive_class": "the set meant to be refused (Toxic / XSTest unsafe)",
           "hedge_lexicon": HEDGES, "tasks": {}}
    texts = h.prompt.tolist() + t.prompt.tolist()
    y = [0] * len(h) + [1] * len(t)
    cats = h.category.tolist() + t.category.tolist()
    res["tasks"]["orb_hard_vs_toxic"] = run_task(texts, y, cats, a.perms)
    easy = e[~e.prompt.isin(set(h.prompt))].sample(5000, random_state=0)
    texts = easy.prompt.tolist() + t.prompt.tolist()
    y = [0] * len(easy) + [1] * len(t)
    cats = easy.category.tolist() + t.category.tolist()
    res["tasks"]["orb_80k_sample_vs_toxic"] = run_task(texts, y, cats, a.perms)
    yx = (xs.label == "unsafe").astype(int).tolist()
    res["tasks"]["xstest_safe_vs_unsafe"] = run_task(xs.prompt.tolist(), yx, None, a.perms)
    res["tasks"]["xstest_safe_vs_unsafe"]["type_tag_note"] = (
        "the released 'type' column determines the label exactly (prefix contrast_), by design")
    Path(a.out).write_text(json.dumps(res, indent=1))
    for k, v in res["tasks"].items():
        print(k, {kk: (vv["auroc"], vv["ci95"], vv.get("null_p95")) for kk, vv in v.items()
                  if isinstance(vv, dict) and "auroc" in vv}, v["hedge_any_rate"], v["mean_chars"])
        print("  ", [(w["word"], w["rate_safe"], w["rate_unsafe"]) for w in v["top_chi2_words"]])


if __name__ == "__main__":
    main()
