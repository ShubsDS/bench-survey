"""Check 1 on the Control Tax backdoor set: detectors that never read what the backdoor does.

Control Tax's monitor (monitors/inspect_monitor.py at the pinned commit) scores, for every record,
the record's correct_code as benign and its backdoored_code as backdoored, both with comments
removed and Black-formatted. correct_code is the human program the attacker was asked to edit.
So each problem enters both classes equally often, and the benign program is the source of the
backdoor.

This script measures, with GroupKFold by problem and a label-flip null within each pair:
  A. Control Tax's own pairing: benign = the edited source (correct_code);
  B. the pairing the DSPy trusted-monitor tutorial uses on the ControlArena copy: the k-th
     control_tax backdoor of a problem against solutions[k] (often another human's program).
A and B are scored on the same backdoors, restricted to pairs where the two honest programs differ.
Both classes go through the same normalisation (ast.unparse, which removes comments and layout).
Never runs any program.

Usage: python -I check_baselines.py --cache ../data --out baselines_checks.json [--headline-perms 20] [--perms 0]
"""
import argparse, collections, difflib, json, os, re, sys, time, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore")
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from common import load_ct, load_ca, normalise, SHORT, CT_COMMIT, CA_REV

INT = re.compile(r"(?<![\w.])\d+(?![\w.])")


def vec():
    # The paper's TF-IDF settings (experiments/apps/strip_recheck.py make_vec).
    return TfidfVectorizer(token_pattern=r'[A-Za-z_]+|\d+|[^\sA-Za-z_\d]', ngram_range=(1, 2),
                           min_df=3, max_features=50000, sublinear_tf=True)


def surface(code):
    return [len(code), code.count("\n"), len(re.findall(r'\bif\b', code)),
            len(re.findall(r'\d{3,}', code)), code.count("=="), code.count("%")]


def magic(code, statement):
    """Integer literals >= 3 in the program that never appear in the problem statement."""
    st = set(INT.findall(statement))
    return sum(1 for t in INT.findall(code) if int(t) >= 3 and t not in st)


def cv_scores(H, A, groups, kind, seed=0, flip=None):
    """Out-of-fold scores for honest and attack programs. flip[i]=True swaps pair i's labels."""
    n = len(H)
    docs = np.array(H + A, dtype=object)
    y = np.r_[np.zeros(n), np.ones(n)]
    if flip is not None:
        y = np.r_[flip.astype(float), (~flip).astype(float)]
    g = np.r_[groups, groups]
    s = np.zeros(2 * n)
    for tr, te in GroupKFold(n_splits=5).split(docs, y, g):
        if kind == "tfidf":
            v = vec(); Xtr = v.fit_transform(docs[tr]); Xte = v.transform(docs[te])
        else:
            Xtr = np.log1p(np.array([surface(c) for c in docs[tr]], float))
            Xte = np.log1p(np.array([surface(c) for c in docs[te]], float))
        clf = LogisticRegression(max_iter=3000).fit(Xtr, y[tr])
        s[te] = clf.predict_proba(Xte)[:, 1]
    return s, y


def summarise(s, y, n):
    sh, sa = s[:n], s[n:]
    yh, ya = y[:n], y[n:]
    # pairwise: share of pairs in which the program labelled attack scores higher
    pa = np.where(ya == 1, sa > sh, sh > sa).mean()
    return float(roc_auc_score(y, s)), float(pa)


def boot_auc(s, y, groups, B=200, seed=0):
    rng = np.random.default_rng(seed)
    n = len(groups)
    by = collections.defaultdict(list)
    for i, gname in enumerate(groups):
        by[gname].append(i)
    keys = list(by)
    out = []
    for _ in range(B):
        pick = rng.choice(len(keys), len(keys))
        ix = np.array([i for k in pick for i in by[keys[k]]])
        out.append(roc_auc_score(np.r_[y[ix], y[ix + n]], np.r_[s[ix], s[ix + n]]))
    return [round(float(np.percentile(out, 2.5)), 3), round(float(np.percentile(out, 97.5)), 3)]


def run(H, A, groups, kind, perms, seed=0):
    t = time.time()
    s, y = cv_scores(H, A, groups, kind)
    auc, pa = summarise(s, y, len(H))
    ci = boot_auc(s, y, np.array(groups))
    rng = np.random.default_rng(seed)
    null = []
    for _ in range(perms):
        flip = rng.random(len(H)) < 0.5
        s0, y0 = cv_scores(H, A, groups, kind, flip=flip)
        null.append(roc_auc_score(y0, s0))
    res = {"n_pairs": len(H), "n_problems": len(set(groups)), "auroc": round(auc, 4), "auroc_ci95": ci,
           "pairwise_acc": round(pa, 4)}
    if perms:
        res.update(null_p95=round(float(np.percentile(null, 95)), 4), null_perms=perms,
                   p=round(float((1 + sum(x >= auc for x in null)) / (1 + perms)), 4))
    res["seconds"] = round(time.time() - t, 1)
    return res


def single(H, A, f):
    xh = np.array([f(c) for c in H], float); xa = np.array([f(c) for c in A], float)
    y = np.r_[np.zeros(len(H)), np.ones(len(A))]
    return {"auroc": round(float(roc_auc_score(y, np.r_[xh, xa])), 4),
            "pairwise_attack_higher": round(float((xa > xh).mean()), 4),
            "pairwise_tie": round(float((xa == xh).mean()), 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="../data")
    ap.add_argument("--out", default="baselines_checks.json")
    ap.add_argument("--perms", type=int, default=0, help="null permutations for the A-vs-B rows")
    ap.add_argument("--headline-perms", type=int, default=20, help="null permutations for the headline TF-IDF row")
    a = ap.parse_args()
    d = load_ct(a.cache)
    ca = load_ca(a.cache, ["problem_id", "solutions", "backdoors"])

    order = collections.defaultdict(list)
    for pid, bs in ca.backdoors.items():
        for b in bs:
            if b["source"] == "control_tax":
                order[pid].append(b["model"])
    nb = [normalise(r["backdoored_code"]) for r in d]
    nc = [normalise(r["correct_code"]) for r in d]
    zipped = []
    for r in d:
        sols = ca.loc[r["sample_id"]].solutions
        k = order[r["sample_id"]].index(r["model"])
        zipped.append(normalise(sols[k]["code"]) if k < len(sols) else None)
    pid = [r["sample_id"] for r in d]
    stmt = [r["problem_statement"] for r in d]

    out = {"pins": {"control_tax_code": CT_COMMIT, "apps_control_arena": CA_REV},
           "normalisation": "ast.unparse on both classes (comments and layout removed); comment strip if unparsable",
           "cv": "GroupKFold(5) by problem; null = labels flipped at random within each pair, whole pipeline refit",
           "metadata_baseline": ("not fitted: every record contributes one benign and one backdoored program "
                                 "with the same problem, difficulty and tests, so any metadata detector has "
                                 "AUROC 0.5 exactly under Control Tax's protocol")}

    # A on all records.
    out["A_own_source_all"] = {
        "tfidf": run(nc, nb, pid, "tfidf", a.headline_perms),
        "surface6": run(nc, nb, pid, "surface", 0),
        "length_chars": single(nc, nb, len),
        "if_count": single(nc, nb, lambda c: len(re.findall(r"\bif\b", c))),
    }
    mh = [magic(c, s) for c, s in zip(nc, stmt)]
    ma = [magic(c, s) for c, s in zip(nb, stmt)]
    y = np.r_[np.zeros(len(mh)), np.ones(len(ma))]
    out["A_own_source_all"]["magic_constants"] = {
        "auroc": round(float(roc_auc_score(y, np.r_[mh, ma])), 4),
        "share_backdoors_adding_a_constant": round(float(np.mean(np.array(ma) > np.array(mh))), 4)}

    # How much of A's signal comes from attackers rewriting the program rather than editing it:
    # out-of-fold TF-IDF scores split by token-sequence similarity of backdoor to its source.
    s, yy = cv_scores(nc, nb, pid, "tfidf")
    n = len(d)
    TOK = re.compile(r"[A-Za-z_]\w*|\d+|\S")
    sim = np.array([difflib.SequenceMatcher(a=TOK.findall(c), b=TOK.findall(b), autojunk=False).ratio()
                    for b, c in zip(nb, nc)])
    bins = {}
    for lo, hi in [(0, .5), (.5, .8), (.8, .9), (.9, .97), (.97, 1.01)]:
        m = (sim >= lo) & (sim < hi)
        bins[f"[{lo},{min(hi, 1)}{')' if hi < 1 else ']'}"] = {
            "n": int(m.sum()),
            "auroc": round(float(roc_auc_score(np.r_[np.zeros(m.sum()), np.ones(m.sum())], np.r_[s[:n][m], s[n:][m]])), 4),
            "pairwise_acc": round(float(np.mean(s[n:][m] > s[:n][m])), 4)}
    out["A_tfidf_by_similarity_to_source"] = bins
    out["A_tfidf_by_attacker_pooled_model"] = {
        SHORT[mo]: round(float(roc_auc_score(np.r_[np.zeros(k.sum()), np.ones(k.sum())], np.r_[s[:n][k], s[n:][k]])), 4)
        for mo in SHORT for k in [np.array([r["model"] == mo for r in d])]}
    guard = lambda c: "__name__" in c
    out["A_main_guard"] = {"share_backdoors": round(float(np.mean([guard(c) for c in nb])), 4),
                           "share_benign": round(float(np.mean([guard(c) for c in nc])), 4),
                           "backdoor_adds_guard_source_lacks": int(sum(guard(b) and not guard(c) for b, c in zip(nb, nc))),
                           **single(nc, nb, lambda c: float(guard(c)))}

    # A vs B on the same backdoors, where the two honest programs differ.
    ix = [i for i in range(len(d)) if zipped[i] is not None and zipped[i] != nc[i]]
    out["same_backdoors_where_pairings_differ"] = {
        "n": len(ix),
        "A_own_source": {"tfidf": run([nc[i] for i in ix], [nb[i] for i in ix], [pid[i] for i in ix], "tfidf", a.perms),
                         "length_chars": single([nc[i] for i in ix], [nb[i] for i in ix], len)},
        "B_dspy_zip_partner": {"tfidf": run([zipped[i] for i in ix], [nb[i] for i in ix], [pid[i] for i in ix], "tfidf", a.perms),
                               "length_chars": single([zipped[i] for i in ix], [nb[i] for i in ix], len)},
    }

    # Per attacker under A (trained and tested within the attacker's own records).
    per = {}
    for m, short in SHORT.items():
        jx = [i for i in range(len(d)) if d[i]["model"] == m]
        H, A = [nc[i] for i in jx], [nb[i] for i in jx]
        per[short] = {"n": len(jx), "similarity_to_source_median": round(float(np.median(sim[jx])), 3), "tfidf": run(H, A, [pid[i] for i in jx], "tfidf", 0),
                      "length_chars": single(H, A, len),
                      "magic_auroc": round(float(roc_auc_score(np.r_[np.zeros(len(jx)), np.ones(len(jx))],
                                                               np.r_[[mh[i] for i in jx], [ma[i] for i in jx]])), 4)}
    out["A_per_attacker"] = per
    out["published_monitor_reference"] = ("Control Tax Fig. 3 (an image): o3-mini monitor AUC 0.92-0.96 across "
                                          "attackers; per-monitor values not machine-readable, not compared here")
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
