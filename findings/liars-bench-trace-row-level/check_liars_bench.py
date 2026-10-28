"""Row-level validity checks on Liars' Bench (Cadenza-Labs/liars-bench).

Usage:  python -I check_liars_bench.py --cache data [--perms 100] [--hf hf]

Downloads the dataset (gated: the user must have accepted the terms and be logged in to `hf`)
and BoolQ (public) at pinned revisions into --cache, then writes liars_bench_checks.json.
The output holds counts, AUROCs and row indices only, never message text.

Checks (numbering from scope.md):
  0/2  provenance: models and system prompts per class
  1    content-blind baselines: system-prompt-only, user-turn-only, response-only and
       length/format detectors (TF-IDF + logistic regression, grouped 5-fold CV by base item,
       label-permutation null within model) and fixed rules (no fitting)
  6    label construction: labels recomputed from stored fields where the construction allows
"""
import argparse, ast, json, os, re, shutil, subprocess, sys
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from scipy import sparse

REPO = "Cadenza-Labs/liars-bench"
REV = "503399b81aff28d6812b0ea4585607d5e4b7d3c4"
BOOLQ = "google/boolq"
BOOLQ_REV = "35b264d03638db9f4ce671b711558bf7ff0f80d5"
SUBSETS = ["convincing-game", "gender-secret", "harm-pressure-choice",
           "harm-pressure-knowledge-report", "insider-trading", "instructed-deception",
           "soft-trigger"]
SHORT = {"convincing-game": "CG", "gender-secret": "GS", "harm-pressure-choice": "HP-C",
         "harm-pressure-knowledge-report": "HP-KR", "insider-trading": "IT",
         "instructed-deception": "ID", "soft-trigger": "ST"}
# Paper (arXiv 2511.16035v2, appendix tables), AUROC averaged across models, per dataset.
PAPER_AUROC = {
    "mean_probe":            {"HP-C": .48, "HP-KR": .36, "CG": .85, "ST": .65, "ID": .71, "GS": .52, "IT": .61},
    "follow_up_probe":       {"HP-C": .56, "HP-KR": .40, "CG": .75, "ST": .68, "ID": .81, "GS": .43, "IT": .74},
    "upper_bound_probe":     {"HP-C": .72, "HP-KR": .96, "CG": 1.00, "ID": .92, "IT": .98},
    "self_evaluation":       {"HP-C": .61, "HP-KR": .49, "CG": .94, "ST": .83, "ID": .93, "GS": .50, "IT": .75},
    "llm_as_a_judge":        {"HP-C": .77, "HP-KR": .63, "CG": .99, "ST": .94, "ID": .99, "GS": .45, "IT": .96},
    "unrelated_question":    {"HP-C": .65, "HP-KR": .82, "CG": .78, "ST": .83, "ID": .93, "GS": .46, "IT": .77},
    "self_eval_alt_prompt":  {"HP-C": .58, "HP-KR": .46, "CG": .89, "ST": .78, "ID": .95, "GS": .56, "IT": .74},
    "llm_judge_alt_prompt":  {"HP-C": .75, "HP-KR": .71, "CG": .97, "ST": .94, "ID": .99, "GS": .42, "IT": .95},
    "self_as_a_judge":       {"HP-C": .71, "HP-KR": .52, "CG": .90, "ST": .84, "ID": .98, "GS": .54, "IT": .90},
}
PAPER_MODELS = ("gemma", "llama", "mistral", "qwen")
# Fixed before fitting anything: gender words for the Gender-Secret final question.
GENDER_RE = (r"\b(gender|genders|male|female|man|woman|men|women|sex|pronouns?|boy|girl|guy|lady|"
             r"masculine|feminine|he or she|his or her|husband|wife|mr|mrs|ms|sir|ma'am)\b")
# Soft-Trigger name prefixes, by conventional gender (generic first names; used only to test the
# paper's stated trigger rule).
MALE = {"Benjamin", "Caleb", "Gavin", "Grayson", "Jacob", "Nicholas", "Noah", "Samuel",
        "Theodore", "Will"}
FEMALE = {"Maria", "Marissa", "Mary", "Megan", "Melissa", "Mia", "Natalie", "Nicole", "Olivia",
          "Paige"}


ST_PREFIX = re.compile(r"^(\[\d+:\d+\] True or False\?|\w+ says:|.*?[.!,])\s+")


def fetch(cache, hf):
    lb = os.path.join(cache, "liars-bench")
    bq = os.path.join(cache, "boolq")
    for repo, rev, d in [(REPO, REV, lb), (BOOLQ, BOOLQ_REV, bq)]:
        if not os.path.exists(os.path.join(d, ".rev_" + rev)):
            subprocess.run([hf, "download", repo, "--repo-type", "dataset", "--revision", rev,
                            "--local-dir", d], check=True, stdout=subprocess.DEVNULL)
            open(os.path.join(d, ".rev_" + rev), "w").close()
    return lb, bq


def parse_meta(m):
    """Meta is a Python-literal dict string, sometimes with np.float64(...) and nan/inf.
    Parsed with ast.literal_eval only (no eval)."""
    if m is None:
        return {}
    s = re.sub(r"np\.(?:float64|int64|bool_)\(([^()]*)\)", r"\1", m)
    s = re.sub(r"\b(nan|inf)\b", "None", s)
    return ast.literal_eval(s)


def base_model(name):
    for b in PAPER_MODELS + ("kimi",):
        if b in name:
            return b
    return name


def auc(y, s):
    y = np.asarray(y)
    if len(np.unique(y)) < 2:
        return None
    return float(roc_auc_score(y, s))


def macro_auc(y, s, models):
    """AUROC within each base model, then averaged (the paper's aggregation)."""
    out = {}
    for m in sorted(set(models)):
        k = models == m
        a = auc(y[k], s[k])
        if a is not None:
            out[m] = round(a, 3)
    return (round(float(np.mean(list(out.values()))), 3) if out else None), out


def oof_scores(X, y, groups, seed=0):
    n_groups = len(set(groups))
    if n_groups >= 5:
        splits = GroupKFold(n_splits=5).split(X, y, groups)
    else:
        splits = StratifiedKFold(5, shuffle=True, random_state=seed).split(X, y)
    s = np.zeros(len(y))
    for tr, te in splits:
        if len(np.unique(y[tr])) < 2:
            s[te] = y[tr].mean()
            continue
        clf = LogisticRegression(C=1.0, max_iter=2000, solver="liblinear")
        clf.fit(X[tr], y[tr])
        s[te] = clf.decision_function(X[te])
    return s


def baseline(X, y, groups, models, perms, rng):
    s = oof_scores(X, y, groups)
    pooled = auc(y, s)
    macro, per = macro_auc(y, s, models)
    null = []
    for _ in range(perms):
        yp = y.copy()
        for m in set(models):  # permute within model, keeping class balance per model
            k = np.where(models == m)[0]
            yp[k] = rng.permutation(yp[k])
        sp = oof_scores(X, yp, groups)
        null.append(macro_auc(yp, sp, models)[0])
    null = np.array(null, float)
    return {"pooled_auroc": round(pooled, 3), "macro_auroc_over_models": macro,
            "per_model": per,
            "null_macro_p95": round(float(np.percentile(null, 95)), 3) if perms else None,
            "null_macro_max": round(float(null.max()), 3) if perms else None,
            "perms": perms}


def fixed_rule(y, score, models, rng, perms=1000):
    macro, per = macro_auc(y, score, models)
    null = []
    for _ in range(perms):
        yp = y.copy()
        for m in set(models):
            k = np.where(models == m)[0]
            yp[k] = rng.permutation(yp[k])
        null.append(macro_auc(yp, score, models)[0])
    return {"pooled_auroc": round(auc(y, score), 3), "macro_auroc_over_models": macro,
            "per_model": per, "null_macro_p95": round(float(np.percentile(null, 95)), 3),
            "perms": perms}


def tfidf(texts):
    v = TfidfVectorizer(min_df=2, max_features=30000, ngram_range=(1, 2), sublinear_tf=True,
                        token_pattern=r"(?u)\b\w+\b")
    return v.fit_transform(texts)


def fmt_features(df):
    resp = df.messages.map(lambda m: m[-1]["content"])
    f = pd.DataFrame({
        "resp_chars": resp.str.len(),
        "resp_words": resp.str.split().map(len),
        "resp_newlines": resp.str.count("\n"),
        "resp_digits": resp.str.count(r"\d"),
        "n_messages": df.messages.map(len),
        "user_chars": df.messages.map(lambda m: sum(len(x["content"]) for x in m if x["role"] == "user")),
    })
    return sparse.csr_matrix(StandardScaler().fit_transform(np.log1p(f.values.astype(float))))


def group_key(c, df, meta):
    users = df.messages.map(lambda m: [x["content"] for x in m if x["role"] == "user"])
    if c == "gender-secret":
        return users.map(lambda u: u[-1]).values, "final user question"
    if c == "convincing-game":
        return users.map(lambda u: u[0]).values, "user prompt"
    if c.startswith("harm-pressure"):
        # WMDP item: the answer options, which are the same under every harmful template
        k = users.map(lambda u: " ".join(re.findall(r"^[A-D]\. .*$", u[0], flags=re.M)))
        return k.values, "WMDP item (answer options)"
    if c == "instructed-deception":
        return (df.dataset + ":" + df.dataset_index.astype(str)).values, "statement (dataset, dataset_index)"
    if c == "soft-trigger":
        return users.map(lambda u: ST_PREFIX.sub("", u[0].split("=== END PASSAGE ===")[-1].strip()) + "||" + u[0].split("=== END PASSAGE ===")[0]).values, "BoolQ item (passage, question)"
    if c == "insider-trading":
        return np.arange(len(df)), "none (one scenario; stratified folds)"
    raise ValueError(c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="liars_bench_checks.json")
    ap.add_argument("--perms", type=int, default=100)
    ap.add_argument("--perms-large", type=int, default=20, help="permutations for subsets over 8,000 rows")
    ap.add_argument("--hf", default=shutil.which("hf") or os.path.expanduser("~/.local/bin/hf"))
    a = ap.parse_args()
    lb, bq = fetch(a.cache, a.hf)
    rng = np.random.default_rng(0)
    res = {"pins": {"liars_bench": f"{REPO}@{REV}", "boolq": f"{BOOLQ}@{BOOLQ_REV}",
                    "paper": "arXiv 2511.16035v2"},
           "paper_auroc_by_method": PAPER_AUROC, "subsets": {}}

    for c in SUBSETS:
        df = pd.read_parquet(os.path.join(lb, c, "test-00000-of-00001.parquet"))
        meta = pd.DataFrame([parse_meta(m) for m in df["meta"]]) if "meta" in df else pd.DataFrame(index=df.index)
        df["base"] = df.model.map(base_model)
        R = {"rows": int(len(df)), "lies": int(df.deceptive.sum()),
             "honest": int((~df.deceptive).sum()),
             "by_model": {m: {"lies": int(g.deceptive.sum()), "honest": int((~g.deceptive).sum())}
                          for m, g in df.groupby("model")},
             "rows_from_models_not_in_paper": int((df.base == "kimi").sum())}
        # ---- 0/2 provenance
        sysp = df.messages.map(lambda m: m[0]["content"] if m[0]["role"] == "system" else "")
        lie_sys = set(zip(df.model[df.deceptive], sysp[df.deceptive]))
        hon_sys = set(zip(df.model[~df.deceptive], sysp[~df.deceptive]))
        lie_rows_with_honest_sys = int(sum((m, s) in hon_sys for m, s in zip(df.model[df.deceptive], sysp[df.deceptive])))
        R["provenance"] = {
            "distinct_system_prompts": {"lies": len({s for _, s in lie_sys}), "honest": len({s for _, s in hon_sys})},
            "lie_rows_whose_model_and_system_prompt_also_produce_honest_rows": lie_rows_with_honest_sys,
            "models_only_in_one_class": sorted(set(df.model[df.deceptive]) ^ set(df.model[~df.deceptive])),
        }
        # restrict detector comparisons to the paper's models
        keep = (df.base != "kimi").values
        d = df[keep].reset_index(drop=True)
        mt = meta[keep].reset_index(drop=True) if len(meta.columns) else meta
        y = d.deceptive.values.astype(int)
        models = d.base.values
        groups, gname = group_key(c, d, mt)
        R["cv_groups"] = {"key": gname, "n_groups": int(len(set(groups)))}
        users = d.messages.map(lambda m: "\n".join(x["content"] for x in m if x["role"] == "user"))
        resp = d.messages.map(lambda m: m[-1]["content"])
        sysd = d.messages.map(lambda m: m[0]["content"])
        P = a.perms if len(d) <= 8000 else a.perms_large
        B = {}
        B["system_prompt_only (hidden from the paper's text detectors)"] = baseline(tfidf(sysd), y, groups, models, P, rng) if sysd.nunique() > 1 else "one system prompt per model"
        B["user_turns_only (visible to text detectors)"] = baseline(tfidf(users), y, groups, models, P, rng)
        B["final_response_only"] = baseline(tfidf(resp), y, groups, models, P, rng)
        B["length_format (6 features)"] = baseline(fmt_features(d), y, groups, models, P, rng)
        R["baselines_paper_models"] = B
        R["paper_auroc"] = {k: v.get(SHORT[c]) for k, v in PAPER_AUROC.items()}

        # ---- subset-specific fixed rules and label-construction checks
        X = {}
        if c == "gender-secret":
            lastq = d.messages.map(lambda m: [x["content"] for x in m if x["role"] == "user"][-1])
            hit = lastq.str.contains(GENDER_RE, case=False, regex=True).values
            X["gender_word_rule_on_final_question"] = {
                "regex_fixed_before_fitting": True,
                "lies_matched": int(hit[y == 1].sum()), "lies": int((y == 1).sum()),
                "honest_matched": int(hit[y == 0].sum()), "honest": int((y == 0).sum()),
                **fixed_rule(y, hit.astype(float), models, rng)}
            q = lastq.values
            X["final_questions"] = {"distinct_in_lies": int(len(set(q[y == 1]))),
                                    "distinct_in_honest": int(len(set(q[y == 0]))),
                                    "shared_between_classes": int(len(set(q[y == 1]) & set(q[y == 0])))}
            X["meta_trained_gender_key_present"] = {
                "lies": int(meta.get("trained_gender", pd.Series(dtype=object)).notna()[df.deceptive.values].sum()) if "trained_gender" in meta else 0,
                "honest": int(meta.get("trained_gender", pd.Series(dtype=object)).notna()[~df.deceptive.values].sum()) if "trained_gender" in meta else 0}
        if c == "soft-trigger":
            u0 = d.messages.map(lambda m: m[1]["content"])
            tail = u0.map(lambda t: t.split("=== END PASSAGE ===")[-1].strip())
            trig = d.model.str.split("-").str[-1].values
            hh = tail.str.extract(r"^\[(\d+):\d+\]")[0].astype(float).values
            name = tail.str.extract(r"^(\w+) says:")[0].values
            paper_rule = np.full(len(d), np.nan)  # 1 = paper's stated lying trigger present
            paper_rule[trig == "time"] = (hh[trig == "time"] >= 12).astype(float)
            g = trig == "gender"
            paper_rule[g] = [1.0 if n in MALE else 0.0 if n in FEMALE else np.nan for n in name[g]]
            T = {}
            for t in ["gender", "time"]:
                k = (trig == t) & ~np.isnan(paper_rule)
                T[t] = {"rows_classified": int(k.sum()),
                        "auroc_of_paper_trigger_rule": round(auc(y[k], paper_rule[k]), 3),
                        "lies_with_paper_trigger": int(((paper_rule == 1) & (y == 1) & k).sum()),
                        "lies_with_paper_safe_prefix": int(((paper_rule == 0) & (y == 1) & k).sum()),
                        "honest_with_paper_trigger": int(((paper_rule == 1) & (y == 0) & k).sum()),
                        "honest_with_paper_safe_prefix": int(((paper_rule == 0) & (y == 0) & k).sum()),
                        "by_model": {m: {"lies_with_paper_safe": int(((paper_rule == 0) & (y == 1) & k & (d.model.values == m)).sum()),
                                         "honest_with_paper_safe": int(((paper_rule == 0) & (y == 0) & k & (d.model.values == m)).sum()),
                                         "lies_with_paper_trigger": int(((paper_rule == 1) & (y == 1) & k & (d.model.values == m)).sum()),
                                         "honest_with_paper_trigger": int(((paper_rule == 1) & (y == 0) & k & (d.model.values == m)).sum()),
                                         "auroc_of_paper_trigger_rule": round(auc(y[k & (d.model.values == m)], paper_rule[k & (d.model.values == m)]), 3)}
                                     for m in sorted(set(d.model.values[k]))}}
            # answer polarity alone (True/False), no question
            T["answer_is_False_rule"] = fixed_rule(y, d.messages.map(lambda m: m[2]["content"].strip() == "False").values.astype(float), models, rng)
            gr = trig == "greeting"
            pre = tail[gr].str.extract(r"^(.*?[.!,])\s")[0]
            ct = pd.crosstab(pre, d.deceptive[gr])
            T["greeting"] = {"distinct_prefixes": int(len(ct)),
                             "prefixes_with_lie_majority": int((ct[True] > ct[False]).sum()),
                             "rows_matching_prefix_majority": int(ct.max(axis=1).sum()),
                             "rows": int(gr.sum())}
            X["paper_trigger_rule_vs_labels"] = T
            prefix = tail.str.extract(r"^(\[\d+:\d+\] True or False\?|\w+ says:|.*?[.!,])\s")[0].fillna("")
            # hour as a token so the bag-of-words can read morning/afternoon
            prefix = prefix.str.replace(r"\[(\d+):\d+\].*", lambda m_: "hour_%s" % m_.group(1), regex=True)
            pre_txt = d.model.str.split("-").str[-1] + " " + prefix
            X["prefix_only_bow (prefix and trigger family, no passage/question/answer)"] = baseline(
                tfidf(pre_txt.values), y, groups, models, P, rng)
            # label construction against BoolQ gold
            b = pd.concat([pd.read_parquet(os.path.join(bq, "data", f"{s}-00000-of-00001.parquet")).assign(split=s)
                           for s in ["train", "validation"]])
            gold = dict(zip(zip(b.question.str.strip().str.lower(), b.passage.str.strip()), b.answer))
            qtext = tail.str.replace(r"^(\[\d+:\d+\] True or False\?|\w+ says:|.*?[.!,])\s+", "", regex=True) \
                        .str.replace(r'\? Answer must be a single word: "True" or "False".$', "", regex=True).str.strip().str.lower()
            ptext = u0.map(lambda t: t.split("=== END PASSAGE ===")[0].replace("=== BEGIN PASSAGE ===", "").strip())
            gl = pd.Series([gold.get(k) for k in zip(qtext, ptext)])
            ans = d.messages.map(lambda m: m[2]["content"].strip() == "True")
            ok = gl.notna().values
            implied = ans.values[ok] != gl.values[ok].astype(bool)
            X["label_vs_boolq_gold"] = {"rows_matched_to_boolq": int(ok.sum()), "rows": int(len(d)),
                                        "label_equals_answer_wrong": int((implied == y[ok].astype(bool)).sum()),
                                        "boolq_split_of_matches": "validation" if set(b.set_index(b.question.str.strip().str.lower()).loc[qtext[ok].unique(), "split"]) == {"validation"} else "mixed"}
        if c == "insider-trading":
            nm = df.messages.map(len).values
            yy = df.deceptive.values.astype(int)
            X["n_messages_rule (all models)"] = {
                "by_turn_name": {k: {"lies": int(g.deceptive.sum()), "honest": int((~g.deceptive).sum())}
                                 for k, g in df.assign(t=meta["turn_name"].values).groupby("t")},
                **fixed_rule(yy, nm.astype(float), df.base.values, rng)}
            X["n_messages_rule (paper models)"] = fixed_rule(y, d.messages.map(len).values.astype(float), models, rng)
        if c == "convincing-game":
            lie_instr = meta["template_system_instructs_lying"].astype(bool).values
            X["lie_instructed_rows"] = {"lies": int((lie_instr & df.deceptive.values).sum()),
                                        "honest": int((lie_instr & ~df.deceptive.values).sum())}
            cell = df.model + "||" + sysp
            pur = df.groupby(cell).deceptive.agg(lambda s: s.all() or (~s).all())
            X["rows_in_label_pure_(model, system_prompt)_cells"] = int(df.groupby(cell).size()[pur].sum())
        if c == "instructed-deception":
            ins = meta["instructed_deceptiveness"].astype(bool).values
            X["by_instruction"] = {"neutral": {"lies": int((~ins & df.deceptive.values).sum()), "honest": int((~ins & ~df.deceptive.values).sum())},
                                   "lie_instructed": {"lies": int((ins & df.deceptive.values).sum()), "honest": int((ins & ~df.deceptive.values).sum())}}
            X["model_belief_equals_correct_option"] = int((meta.model_belief == meta.correct_option).sum())
            # crude verdict parse of the response's opening, compared with the stored label
            r = df.messages.map(lambda m: m[-1]["content"].strip().lower()[:120])
            neg = r.str.contains(r"\b(false|incorrect|not correct|not true|untrue|no,|no\.)", regex=True)
            pos = r.str.contains(r"\b(true|correct)\b", regex=True) & ~neg
            verdict = np.where(neg, 0, np.where(pos, 1, -1))
            ok = verdict >= 0
            implied = verdict[ok] != meta.correct_option.values[ok]
            X["label_vs_crude_verdict_parse"] = {"rows_parsed": int(ok.sum()), "rows": int(len(df)),
                                                 "agree": int((implied == df.deceptive.values[ok]).sum()),
                                                 "disagree_row_indices_first_50": [int(i) for i in np.where(ok)[0][implied != df.deceptive.values[ok]][:50]]}
        if c == "harm-pressure-choice":
            r = df.messages.map(lambda m: m[-1]["content"].strip())
            letter = r.str.extract(r"^\(?([A-D])\b")[0].map(lambda s: "ABCD".index(s) if isinstance(s, str) else np.nan)
            ok = letter.notna().values
            implied = letter.values[ok] != meta.model_belief.values[ok]
            X["label_vs_letter_parse"] = {"rows_parsed": int(ok.sum()), "rows": int(len(df)),
                                          "agree": int((implied == df.deceptive.values[ok]).sum())}
            X["model_belief_equals_correct_option"] = int((meta.model_belief == meta.correct_option).sum())
        if c == "harm-pressure-knowledge-report":
            r = df.messages.map(lambda m: m[-1]["content"].strip().lower())
            denies = r.str.contains(r"(do not|don't|don’t|cannot|can't|not able to|unable to) (know|tell|say|determine)|\bnot sure\b|\bno idea\b|\bi do not know\b", regex=True)
            belief = meta.model_belief.values
            implied = (belief >= 0) & denies.values
            X["denial_only_rule (response claims not to know; no belief used)"] = fixed_rule(
                df.deceptive.values.astype(int), denies.values.astype(float), df.base.values, rng)
            X["label_vs_denial_parse"] = {"rows": int(len(df)), "agree": int((implied == df.deceptive.values).sum()),
                                          "no_belief_rows": int((belief < 0).sum()),
                                          "no_belief_rows_labelled_lie": int(((belief < 0) & df.deceptive.values).sum())}
            tmpl = meta.template_index.values
            X["template_only_rule"] = {"by_template": {int(t): {"lies": int(((tmpl == t) & df.deceptive.values).sum()), "honest": int(((tmpl == t) & ~df.deceptive.values).sum())} for t in sorted(set(tmpl))}}
            topic = df.dataset.values
            X["wmdp_topic"] = {t: {"lies": int(((topic == t) & df.deceptive.values).sum()), "honest": int(((topic == t) & ~df.deceptive.values).sum())} for t in sorted(set(topic))}
            # template and topic are both in the user turn
            rate = pd.Series(df.deceptive.values).groupby([tmpl, topic, df.base.values]).transform("mean").values
            X["template_x_topic_x_model_cell_rate (in-sample, optimistic)"] = fixed_rule(df.deceptive.values.astype(int), rate, df.base.values, rng, perms=200)
        R["specific"] = X
        res["subsets"][c] = R
        print(c, "done", file=sys.stderr)

    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
