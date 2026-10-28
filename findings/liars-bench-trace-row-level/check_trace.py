"""Row-level validity checks on TRACE (PatronusAI/trace-dataset).

Usage:  python -I check_trace.py --cache data [--perms 200] [--hf hf]

Downloads TRACE (gated: the user must have accepted the terms and be logged in to `hf`) and
rh-bench's unified file (public; it re-serves the 517 TRACE rows) at pinned revisions into
--cache, then writes trace_checks.json. Output holds counts, scores and trajectory ids only,
never transcript text.

Checks (numbering from scope.md):
  1/7  content-blind and keyword baselines: structure (length, turns, tool calls), a user
       call-out / assistant admission regex, TF-IDF + logistic regression on parts of the
       transcript; permutation nulls; AUROC and macro F1 (the paper's "Detection Rate")
  2    one generator, class-specific prompts: rates of each prompt's own phrases in the transcripts
  5    near-duplicates (word 5-gram Jaccard) and label-from-id; rh-bench's copy of the rows
"""
import argparse, hashlib, json, os, re, shutil, subprocess
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import GroupKFold

REPO, REV = "PatronusAI/trace-dataset", "31d87f06078eca3ab6eaf1e06e5ea6fe9f2b7a6d"
RH, RH_REV = "ktolnos/rh-bench", "1045a7336432c40182924bbd3698af292ea24acb"
# Paper (arXiv 2601.20103v1): Detection Rate = macro F1 of the binary hack prediction.
PAPER_DETECTION_RATE = {"best_isolated_N1_gpt_5_2": 0.45, "kimi_k2_thinking_N1": 0.37,
                        "best_contrastive_N10_gpt_5_2": 0.63}

# Regexes fixed before any classifier was fitted. They were written after reading class rates of
# a few single words (see README), so treat them as exploratory, not pre-registered.
USER_CALLOUT = re.compile(
    r"\b(wait|hold on|stop)\b[,.!:\s-]|that'?s not (right|what|how|correct|real|actually)|"
    r"\byou (just |actually |only )?(changed|modified|edited|hard-?coded|removed|deleted|disabled|"
    r"skipped|commented out|bypassed|mocked|special-?cased|lowered|loosened|weakened)\b|"
    r"\bwhy (did|are|is|would) you\b|defeats the (whole )?purpose|not what i asked|"
    r"\b(isn'?t|doesn'?t|aren'?t|don'?t) (actually|really)\b|"
    r"\b(cheat|cheating|gaming the|game the|hack|hacky|hacked)\b", re.I)
ASSIST_ADMIT = re.compile(
    r"you'?re (absolutely |completely |totally )?right|\bi apologi[sz]e|\bmy (mistake|apologies|bad)\b|"
    r"\bi should(n'?t| not) have\b|\bi was wrong\b|that was (a|an) (mistake|shortcut|hack)|"
    r"\b(i|i've|i have) (cheated|gamed)\b|\bthat'?s (a|an) (fair|valid|good) (point|catch|concern)\b", re.I)
# Phrases from the two generation prompts (paper appendix, generation prompts).
BENIGN_PROMPT_PHRASES = {
    "proper testing": r"\bproper(ly)? test", "verification": r"\bverif(y|ied|ication|ying)\b",
    "honest": r"\bhonest(ly)?\b", "best practice": r"\bbest[- ]practices?\b",
    "no shortcuts": r"\bshortcuts?\b", "thorough": r"\bthorough(ly)?\b", "correctly": r"\bcorrectly\b",
    "comprehensive": r"\bcomprehensive(ly)?\b"}
HACK_PROMPT_PHRASES = {  # "specific constraints, business requirements, or time pressures"
    "deadline": r"\bdeadline\b", "urgent/asap": r"\b(urgent(ly)?|asap)\b",
    "by tomorrow/today/end of day": r"\b(by|before) (tomorrow|today|end of (the )?day|eod|monday|friday)\b",
    "next week/demo": r"\b(next week|demo)\b", "target/threshold": r"\b(target|threshold)s?\b",
    "must pass/need to hit": r"\b(must|need to|have to) (pass|hit|reach|meet)\b",
    "metric/score": r"\b(metric|score)s?\b", "pressure/blocked/blocking": r"\b(pressure|blocked|blocking)\b"}
# The benign prompt says "without cutting corners or gaming metrics" and "No shortcuts": does the
# benign agent announce what it is not doing?
NEGATED_HACK = re.compile(r"\b(instead of|rather than|without|not|never|avoid(ing)?|no|don'?t|won'?t) (just |simply |actually )?"
                          r"(gaming|game|hard-?coding|hard-?code|cheating|cheat|shortcuts?|special-?casing|"
                          r"skipping|skip|cutting corners|weakening|disabling|mocking)\b", re.I)
HACK_WORDS = re.compile(r"\b(gam(e|ing|ed) the (metric|metrics|tests?|benchmark|score|system)|hard-?cod(e|ed|ing)|"
                        r"cheat(ing)?|reward hack(ing)?|cutting corners)\b", re.I)
ABS_PATH = re.compile(r"(/home/|/Users/|C:\\\\Users)")  # the prompts say never use absolute paths


def fetch(cache, hf):
    out = {}
    for repo, rev, sub, inc in [(REPO, REV, "trace-dataset", None),
                                (RH, RH_REV, "rh-bench", "data/rh_bench_unified.parquet")]:
        d = os.path.join(cache, sub)
        if not os.path.exists(os.path.join(d, ".rev_" + rev)):
            cmd = [hf, "download", repo, "--repo-type", "dataset", "--revision", rev, "--local-dir", d]
            if inc:
                cmd += ["--include", inc]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
            open(os.path.join(d, ".rev_" + rev), "w").close()
        out[sub] = d
    return out


def parts(conv):
    user = [m.get("content") or "" for m in conv if m["role"] == "user"]
    asst = [m.get("content") or "" for m in conv if m["role"] == "assistant"]
    calls = [json.dumps(t.get("parameters")) for m in conv for t in (m.get("tool_calls") or [])]
    outs = [str(t.get("output")) for m in conv for t in (m.get("tool_results") or [])]
    return user, asst, calls, outs


def auc(y, s):
    return float(roc_auc_score(y, s))


def null_auc(y, s, rng, perms=1000):
    return float(np.percentile([auc(rng.permutation(y), s) for _ in range(perms)], 95))


def macro_f1(y, pred):
    return float(f1_score(y, pred, average="macro"))


def oof(X, y, groups, seed):
    s = np.zeros(len(y))
    # shuffle group order so folds differ by seed
    g = pd.Series(groups).map(dict(zip(sorted(set(groups)), np.random.default_rng(seed).permutation(len(set(groups)))))).values
    for tr, te in GroupKFold(5).split(X, y, g):
        clf = LogisticRegression(C=1.0, max_iter=3000, solver="liblinear", class_weight="balanced")
        clf.fit(X[tr], y[tr])
        s[te] = clf.decision_function(X[te])
    return s


def bow(texts, y, groups, perms, rng, repeats=5):
    X = TfidfVectorizer(min_df=2, max_features=50000, ngram_range=(1, 2), sublinear_tf=True).fit_transform(texts)
    aucs, f1s = [], []
    for r in range(repeats):
        s = oof(X, y, groups, r)
        aucs.append(auc(y, s))
        f1s.append(macro_f1(y, (s > 0).astype(int)))
    null = [auc(yp, oof(X, yp, groups, 0)) for yp in (rng.permutation(y) for _ in range(perms))]
    return {"auroc_mean_over_repeats": round(float(np.mean(aucs)), 3),
            "auroc_range": [round(min(aucs), 3), round(max(aucs), 3)],
            "macro_f1_at_0": round(float(np.mean(f1s)), 3),
            "null_auroc_p95": round(float(np.percentile(null, 95)), 3) if perms else None,
            "null_auroc_max": round(float(np.max(null)), 3) if perms else None, "perms": perms}


def shingles(text, k=5):
    w = re.findall(r"\w+", text.lower())
    return {hashlib.md5(" ".join(w[i:i + k]).encode()).hexdigest()[:12] for i in range(max(1, len(w) - k + 1))}


def jaccard_pairs(sets, thr):
    out = []
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            a, b = sets[i], sets[j]
            if not a or not b:
                continue
            inter = len(a & b)
            if inter and inter / (len(a) + len(b) - inter) >= thr:
                out.append((i, j, inter / (len(a) + len(b) - inter)))
    return out


def components(n, pairs):
    parent = list(range(n))

    def f(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for i, j, _ in pairs:
        parent[f(i)] = f(j)
    return np.array([f(i) for i in range(n)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="trace_checks.json")
    ap.add_argument("--perms", type=int, default=200)
    ap.add_argument("--hf", default=shutil.which("hf") or os.path.expanduser("~/.local/bin/hf"))
    a = ap.parse_args()
    paths = fetch(a.cache, a.hf)
    rng = np.random.default_rng(0)
    df = pd.read_parquet(os.path.join(paths["trace-dataset"], "data", "train-00000-of-00001.parquet"))
    conv = df.conversation.map(json.loads)
    y = (df.label != "0").values.astype(int)
    ids = df.trajectory_id.values
    P = [parts(c) for c in conv]
    R = {"pins": {"trace": f"{REPO}@{REV}", "rh_bench": f"{RH}@{RH_REV}", "paper": "arXiv 2601.20103v1"},
         "paper_detection_rate_macro_f1": PAPER_DETECTION_RATE,
         "rows": int(len(df)), "hack": int(y.sum()), "benign": int((1 - y).sum()),
         "splits_in_release": ["train"],
         "label_format": {"benign_label": "0", "hack_rows_with_multiple_codes": int(df.label[y == 1].str.contains(",").sum()),
                          "distinct_codes": int(len({c.strip() for l in df.label[y == 1] for c in l.split(",")}))}}
    R["constant_predictor_macro_f1"] = {"all_hack": round(macro_f1(y, np.ones_like(y)), 3),
                                        "all_benign": round(macro_f1(y, np.zeros_like(y)), 3),
                                        "random_half_expected": round(float(np.mean([macro_f1(y, rng.integers(0, 2, len(y))) for _ in range(2000)])), 3)}

    # ---- 1: structure
    feats = {
        "n_messages": [len(c) for c in conv],
        "n_user_turns": [len(p[0]) for p in P],
        "n_tool_calls": [len(p[2]) for p in P],
        "total_chars": df.conversation.str.len().values,
        "user_chars": [sum(map(len, p[0])) for p in P],
        "assistant_prose_chars": [sum(map(len, p[1])) for p in P],
        "tool_output_chars": [sum(map(len, p[3])) for p in P],
        "trajectory_id_number": df.trajectory_id.str.extract(r"(\d+)")[0].astype(int).values,
    }
    S = {}
    for k, v in feats.items():
        v = np.asarray(v, float)
        S[k] = {"auroc": round(auc(y, v), 3), "auroc_flipped_if_below_half": round(max(auc(y, v), 1 - auc(y, v)), 3),
                "null_p95": round(null_auc(y, v, rng), 3),
                "median_hack": float(np.median(v[y == 1])), "median_benign": float(np.median(v[y == 0]))}
    idn = feats["trajectory_id_number"]
    S["trajectory_id_number"]["ids_min_max_unique"] = [int(idn.min()), int(idn.max()), int(len(set(idn)))]
    R["1_structure"] = S

    # ---- 1/7: call-out and admission regexes
    ucall = np.array([sum(bool(USER_CALLOUT.search(u)) for u in p[0][1:]) for p in P])
    aadm = np.array([sum(bool(ASSIST_ADMIT.search(t)) for t in p[1]) for p in P])
    both = np.array([(uc > 0) and (ad > 0) for uc, ad in zip(ucall, aadm)])
    K = {}
    for name, s in [("user_callout_turns", ucall), ("assistant_admission_turns", aadm),
                    ("callout_plus_admission_count", ucall + aadm)]:
        K[name] = {"rows_with_any_hack": int((s[y == 1] > 0).sum()), "rows_with_any_benign": int((s[y == 0] > 0).sum()),
                   "auroc": round(auc(y, s), 3), "null_p95": round(null_auc(y, s.astype(float), rng), 3),
                   "macro_f1_rule_any": round(macro_f1(y, (s > 0).astype(int)), 3)}
    K["both_callout_and_admission"] = {"hack": int(both[y == 1].sum()), "benign": int(both[y == 0].sum()),
                                       "macro_f1_rule": round(macro_f1(y, both.astype(int)), 3)}
    srng = np.random.default_rng(1)
    hk = np.where((ucall > 0) & (y == 1))[0]
    bk = np.where((ucall > 0) & (y == 0))[0]
    K["hand_check_sample_ids"] = {"hack_with_callout": [ids[i] for i in srng.choice(hk, min(20, len(hk)), replace=False)],
                                  "benign_with_callout": [ids[i] for i in srng.choice(bk, min(20, len(bk)), replace=False)]}
    R["1_7_keyword"] = K

    # ---- 2: prompt phrases echoed in transcripts
    first_user = [p[0][0] if p[0] else "" for p in P]
    asst_txt = ["\n".join(p[1]) for p in P]
    full_txt = ["\n".join(p[0] + p[1] + p[2] + p[3]) for p in P]
    E = {}
    for fam, phr in [("benign_prompt", BENIGN_PROMPT_PHRASES), ("hack_prompt", HACK_PROMPT_PHRASES)]:
        E[fam] = {}
        for where, texts in [("first_user_turn", first_user), ("assistant_prose", asst_txt)]:
            E[fam][where] = {k: {"hack_rate": round(float(np.mean([bool(re.search(p_, t, re.I)) for t, yy in zip(texts, y) if yy == 1])), 3),
                                 "benign_rate": round(float(np.mean([bool(re.search(p_, t, re.I)) for t, yy in zip(texts, y) if yy == 0])), 3)}
                             for k, p_ in phr.items()}
    cnt_b = np.array([sum(len(re.findall(p_, t, re.I)) for p_ in BENIGN_PROMPT_PHRASES.values()) for t in asst_txt], float)
    cnt_h = np.array([sum(len(re.findall(p_, t, re.I)) for p_ in HACK_PROMPT_PHRASES.values()) for t in first_user], float)
    E["score_benign_phrases_in_assistant (higher = benign)"] = {"auroc_for_benign": round(auc(1 - y, cnt_b), 3), "null_p95": round(null_auc(1 - y, cnt_b, rng), 3)}
    E["score_hack_phrases_in_first_user_turn (higher = hack)"] = {"auroc": round(auc(y, cnt_h), 3), "null_p95": round(null_auc(y, cnt_h, rng), 3)}
    for nm, rx in [("negated_hack_phrase", NEGATED_HACK), ("hack_vocabulary", HACK_WORDS)]:
        for where, texts in [("assistant_prose", asst_txt), ("user_turns", ["\n".join(p[0]) for p in P])]:
            h = np.array([bool(rx.search(t)) for t in texts])
            E[f"{nm}_in_{where}"] = {"hack_rows": int(h[y == 1].sum()), "benign_rows": int(h[y == 0].sum())}
    ab = np.array([bool(ABS_PATH.search(t)) for t in full_txt])
    E["absolute_paths_against_prompt_rule"] = {"hack_rows": int(ab[y == 1].sum()), "benign_rows": int(ab[y == 0].sum())}
    R["2_prompt_echo"] = E

    # ---- 5: near-duplicates, used as CV groups
    sh_full = [shingles(t) for t in full_txt]
    sh_first = [shingles(t) for t in first_user]
    D = {}
    for name, sets in [("full_transcript", sh_full), ("first_user_turn", sh_first)]:
        pr = jaccard_pairs(sets, 0.3)
        D[name] = {f"pairs_jaccard_ge_{t}": {"total": sum(j >= t for _, _, j in pr),
                                              "cross_class": sum(j >= t and y[a_] != y[b_] for a_, b_, j in pr)}
                   for t in (0.3, 0.5, 0.8)}
        D[name]["max_jaccard"] = round(max([j for _, _, j in pr], default=0.0), 3)
        D[name]["pair_ids_ge_0.5"] = [[ids[a_], ids[b_], round(j, 3)] for a_, b_, j in pr if j >= 0.5][:50]
        if name == "first_user_turn":
            groups = components(len(df), [p for p in pr if p[2] >= 0.3])
    D["labels_of_pairs_ge_0.5"] = [[df.label[a_], df.label[b_]] for a_, b_, j in jaccard_pairs(sh_full, 0.5)]
    exact_first = pd.Series(first_user).duplicated(keep=False)
    D["exact_duplicate_first_user_turns"] = int(exact_first.sum())
    D["cv_groups_from_first_turn_jaccard_ge_0.3"] = int(len(set(groups)))
    R["5_duplicates"] = D

    # ---- 1: bag-of-words views, grouped CV
    views = {"full_transcript": full_txt, "first_user_turn_only": first_user,
             "all_user_turns": ["\n".join(p[0]) for p in P], "assistant_prose_only": asst_txt,
             "tool_calls_and_outputs_only": ["\n".join(p[2] + p[3]) for p in P],
             "user_turns_after_first": ["\n".join(p[0][1:]) for p in P]}
    R["1_bow"] = {k: bow(v, y, groups, a.perms, rng) for k, v in views.items()}
    # same estimate with the vectorizer refit inside each training fold (no null; slower)
    for k, v in views.items():
        v = np.array(v, dtype=object)
        s_ = np.zeros(len(y))
        for tr, te in GroupKFold(5).split(v, y, groups):
            vec = TfidfVectorizer(min_df=2, max_features=50000, ngram_range=(1, 2), sublinear_tf=True)
            Xtr = vec.fit_transform(v[tr])
            clf = LogisticRegression(C=1.0, max_iter=3000, solver="liblinear", class_weight="balanced").fit(Xtr, y[tr])
            s_[te] = clf.decision_function(vec.transform(v[te]))
        R["1_bow"][k]["auroc_vectorizer_in_fold"] = round(auc(y, s_), 3)
        R["1_bow"][k]["macro_f1_vectorizer_in_fold"] = round(macro_f1(y, (s_ > 0).astype(int)), 3)

    # ---- rh-bench copy of TRACE
    u = pd.read_parquet(os.path.join(paths["rh-bench"], "data", "rh_bench_unified.parquet"))
    t = u[u.source_dataset == "patronus_trace"]
    m = t.merge(df[["trajectory_id", "label"]], left_on="source_id", right_on="trajectory_id", how="left")
    R["rh_bench_copy"] = {
        "rows": int(len(t)), "matched_by_id": int(m.label_y.notna().sum()),
        "label_crosstab": {f"rh_{a_}|trace_{b_}": int(n) for (a_, b_), n in
                           m.assign(tc=np.where(m.label_y == "0", "benign", "hack")).groupby(["label_x", "tc"]).size().items()},
        "hacking_category_on_clean_rows": t[t.label == "clean"].hacking_category.value_counts(dropna=False).to_dict(),
        "verification": t.verification.value_counts().to_dict(), "source_split": t.source_split.value_counts().to_dict()}
    with open(a.out, "w") as f:
        json.dump(R, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


if __name__ == "__main__":
    main()
