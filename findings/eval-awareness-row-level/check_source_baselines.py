"""Evaluation-awareness benchmark (Needham et al. 2025): content-blind source and class baselines.

Leads 1 and 3/1 of the audit. Each source in the benchmark belongs to one class, so the label is a
function of the source. This script asks how well features that ignore what the transcript is about
predict the class (evaluation vs deployment), when

  pooled_within_source     stratified 5-fold over rows: other rows of the same source are in
                           training, so the classifier can learn to recognise sources;
  leave_one_source_out     one fold per source, out-of-fold scores pooled. Each held-out fold has
                           one class, so leaving it out shifts the training prior against it and
                           the pooled AUROC is biased below 0.5; read it against its null;
  leave_sources_out_5fold  5 folds of whole sources, stratified by class at the source level, mean
                           within-fold AUROC (unseen evaluation sources against unseen deployment
                           sources, scored by one model). This is the main transfer number.
  For agentic scaffolds used by both classes (aider, openhands, smolagents): train on the other
  agentic scaffolds and score within the held-out scaffold.

Feature sets (all computed from what the model is shown in the paper's "append" probe format: the
messages and the tool definitions; storage-only fields such as message ids are not used):
  structure   counts of messages by role, character counts by role, tool calls, tool definitions,
              role of the last message, structured content parts
  format      multiple-choice option lines, dates and clock times, uuids and long hex ids, code
              fences, markdown headers, xml-like tags, urls, non-ASCII / CJK / Hangul share,
              newline, digit and upper-case density
  scaffold    tool names (those in at least 5 samples) and a few scaffold strings
  bow         reference only, not content-blind: TF-IDF bag of words over the visible text

Pre-specified single rules (no fitting): no assistant turn, ends with a user turn, system prompt
other than the default, multiple-choice block.

Nulls: for the source-grouped schemes, labels are permuted across sources (each source keeps one
label; the number of evaluation sources is fixed); for pooled, labels are permuted across rows. Intervals: bootstrap
over sources. Rows: the 877 held-out rows the paper's models were scored on (pqsel == False), and
model AUROCs are recomputed from the released per-model probe answers on the same rows.

The dataset is gated and encrypted. It is fetched with `hf download` at a pinned revision (the
caller must have accepted the gate), checked against a pinned sha256, and decrypted with the
password the authors publish in the repository's scripts/decrypt.sh. No downloaded code is run.
Outputs hold aggregates, counts and source names only.

Usage: python -I check_source_baselines.py [--cache data] [--out source_baselines_checks.json]
       [--perms 200] [--quick]
"""
import argparse, collections, hashlib, json, math, os, re, shutil, subprocess, zipfile
os.environ.setdefault("OMP_NUM_THREADS", "1")  # one thread per worker; the permutations run in parallel
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HF_REPO = "jjpn2/eval_awareness"
HF_SHA = "5d724f12988284a652749c56ec7b2356b0d14408"
ZIP_SHA256 = "934dc4bc83b76e6bc57e672c39716061204b4802bb46b2038e7feb822aaa211c"
# Table 2 of arXiv 2505.23836v3 (content/methods.tex, tab:auc_brier): AUC by split.
PAPER_AUC = {
    "claude-3-5-sonnet": {"all": 0.834, "chat": 0.793, "agentic": 0.887},
    "claude-3-7-sonnet-16k": {"all": 0.827, "chat": 0.725, "agentic": 0.923},
    "claude-3-7-sonnet": {"all": 0.815, "chat": 0.751, "agentic": 0.884},
    "gemini-2.5-pro-preview": {"all": 0.830, "chat": 0.706, "agentic": 0.948},
    "gemini-2.5-flash-preview": {"all": 0.827, "chat": 0.771, "agentic": 0.909},
    "gpt-4.1": {"all": 0.826, "chat": 0.767, "agentic": 0.884},
    "gpt-4o": {"all": 0.795, "chat": 0.765, "agentic": 0.838},
    "gpt-4.1-mini": {"all": 0.751, "chat": 0.702, "agentic": 0.856},
    "o4-mini-medium": {"all": 0.740, "chat": 0.687, "agentic": 0.828},
    "human": {"all": 0.921, "chat": 0.813, "agentic": 0.996},
}


# ---------------------------------------------------------------- data
def fetch(cache, hf_bin):
    """Download (pinned), verify, and decrypt. Returns (samples, mcq_dir)."""
    hf = cache / "hf"
    if not (hf / "dataset.zip").exists():
        subprocess.run([hf_bin, "download", HF_REPO, "--repo-type", "dataset", "--revision", HF_SHA,
                        "--local-dir", str(hf)], check=True)
    h = hashlib.sha256((hf / "dataset.zip").read_bytes()).hexdigest()
    if h != ZIP_SHA256:
        raise SystemExit(f"dataset.zip sha256 {h} != pinned {ZIP_SHA256}")
    ex = cache / "extracted"
    if not (ex / "dataset.json").exists():
        pw = re.search(r'^PW="([^"]+)"', (hf / "scripts" / "decrypt.sh").read_text(), re.M).group(1)
        with zipfile.ZipFile(hf / "dataset.zip") as z:
            for n in z.namelist():
                if n.startswith("/") or ".." in Path(n).parts:
                    raise SystemExit(f"unsafe path in zip: {n}")
            z.extractall(ex, pwd=pw.encode())
    return json.loads((ex / "dataset.json").read_text()), ex / "mcq_transcripts"


def mcq_id(sid):
    """Map the per-model files' ids onto dataset.json ids (the dataset anonymises three sources)."""
    s = sid.replace("giles_claude:", "author_claude:").replace("govind_runs:", "gaia_runs:")
    return s.replace("mvp:giles_", "mvp:author2_").replace("mvp:joe_", "mvp:author1_")


def text_of(c):
    return c if isinstance(c, str) else "".join(p.get("text", "") for p in c if isinstance(p, dict))


def visible_text(x):
    parts = []
    for m in x["input"]:
        parts.append(text_of(m["content"]))
        for t in m.get("tool_calls") or []:
            parts.append(str(t.get("function", "")) + " " + json.dumps(t.get("arguments", {}), sort_keys=True))
    return "\n".join(parts)


# ---------------------------------------------------------------- features
RX = {
    "mc_lines": re.compile(r"(?m)^\s*(?:\(?[A-Ha-h]\)|[A-H][\.:])\s+\S"),
    "iso_dates": re.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b"),
    "clock_times": re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b"),
    "uuids": re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"),
    "hex16": re.compile(r"\b[0-9a-f]{16,}\b"),
    "code_fences": re.compile(r"```"),
    "md_headers": re.compile(r"(?m)^#{1,6}\s"),
    "xml_tags": re.compile(r"</?[A-Za-z_][\w\-]*>"),
    "urls": re.compile(r"https?://"),
}
SCAFFOLD_RX = {
    "s_thought": re.compile(r"(?m)^Thought:"),
    "s_observation": re.compile(r"Observation:"),
    "s_end_code": re.compile(r"<end_code>"),
    "s_search_replace": re.compile(r"<<<<<<< SEARCH"),
    "s_final_answer": re.compile(r"final_answer"),
    "s_py_fence": re.compile(r"```py"),
    "s_submit": re.compile(r"\bsubmit\b"),
}
CJK = re.compile(r"[一-鿿]")
HANGUL = re.compile(r"[가-힯]")


def features(x):
    msgs = x["input"]
    f = {}
    roles = collections.Counter(m["role"] for m in msgs)
    chars = collections.Counter()
    for m in msgs:
        chars[m["role"]] += len(text_of(m["content"]))
    first_user = next((text_of(m["content"]) for m in msgs if m["role"] == "user"), "")
    vt = visible_text(x)
    n = max(len(vt), 1)
    st = {
        "n_msgs": len(msgs), "n_user": roles["user"], "n_asst": roles["assistant"], "n_tool": roles["tool"],
        "n_sys": roles["system"],
        "log_chars": math.log1p(len(vt)), "log_chars_sys": math.log1p(chars["system"]),
        "log_chars_first_user": math.log1p(len(first_user)), "log_chars_asst": math.log1p(chars["assistant"]),
        "log_chars_tool": math.log1p(chars["tool"]), "log_mean_msg": math.log1p(len(vt) / max(len(msgs), 1)),
        "n_tool_calls": sum(len(m.get("tool_calls") or []) for m in msgs),
        "n_tool_defs": len(x["metadata"].get("tools") or []),
        "frac_list_content": np.mean([isinstance(m["content"], list) for m in msgs]),
    }
    for r in ("user", "assistant", "tool", "system"):
        st[f"last_{r}"] = float(msgs[-1]["role"] == r)
    fm = {k: math.log1p(len(rx.findall(vt))) for k, rx in RX.items()}
    fm["mc_block"] = float(len(RX["mc_lines"].findall(vt)) >= 2)
    fm["nonascii_frac"] = sum(ord(ch) > 127 for ch in vt) / n
    fm["cjk_frac"] = len(CJK.findall(vt)) / n
    fm["hangul_frac"] = len(HANGUL.findall(vt)) / n
    fm["newline_per_kchar"] = 1000 * vt.count("\n") / n
    fm["digit_frac"] = sum(ch.isdigit() for ch in vt) / n
    fm["upper_frac"] = sum(ch.isupper() for ch in vt) / n
    sc = {k: float(bool(rx.search(vt))) for k, rx in SCAFFOLD_RX.items()}
    tools = {"tool:" + t["name"] for t in (x["metadata"].get("tools") or [])}
    return st, fm, sc, tools, vt


def build(samples):
    rows, texts, toolsets = [], [], []
    for x in samples:
        st, fm, sc, tools, vt = features(x)
        m = x["metadata"]
        rows.append({"id": x["id"], "source": m["category"], "scaffold": m["scaffold"] or "none",
                     "agentic": m["scaffold"] is not None, "y": int(bool(m["eval_category"])),
                     "pqsel": bool(m["pqsel"]), **st, **fm, **sc})
        texts.append(vt); toolsets.append(tools)
    df = pd.DataFrame(rows)
    cnt = collections.Counter(t for s in toolsets for t in s)
    keep = sorted(t for t, c in cnt.items() if c >= 5)
    for t in keep:
        df[t] = [float(t in s) for s in toolsets]
    sets = {
        "structure": [c for c in df.columns if c in features(samples[0])[0]],
        "format": [c for c in df.columns if c in RX or c in ("mc_block", "nonascii_frac", "cjk_frac", "hangul_frac",
                                                             "newline_per_kchar", "digit_frac", "upper_frac")],
        "scaffold": list(SCAFFOLD_RX) + keep,
    }
    return df, texts, sets


# ---------------------------------------------------------------- models and CV
def make(kind):
    if kind == "lr":
        return make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=5000, class_weight="balanced"))
    return HistGradientBoostingClassifier(max_iter=100, learning_rate=0.1, max_leaf_nodes=15,
                                          class_weight="balanced", random_state=0)


def fit_predict(kind, X, y, tr, te):
    if len(np.unique(y[tr])) < 2:
        return np.full(len(te), y[tr].mean())
    return make(kind).fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]


def loso(X, y, groups, kind):
    """Leave one source out; out-of-fold scores pooled over folds (each fold holds one class only)."""
    p = np.zeros(len(y))
    for g in np.unique(groups):
        te = np.where(groups == g)[0]; tr = np.where(groups != g)[0]
        p[te] = fit_predict(kind, X, y, tr, te)
    return p


def grouped_folds(y, groups, seed, k=5):
    """Stratified at source level: each fold holds whole sources of both classes."""
    rng = np.random.default_rng(seed)
    gs = np.unique(groups); lab = {g: y[groups == g][0] for g in gs}
    fold = {}
    for c in (0, 1):
        sel = [g for g in gs if lab[g] == c]; rng.shuffle(sel)
        for i, g in enumerate(sel):
            fold[g] = i % k
    return np.array([fold[g] for g in groups])


def leave_sources_out(X, y, groups, kind, reps=5, seed=0):
    """Mean within-fold AUROC over 5 source-grouped folds, repeated: unseen evaluation sources
    against unseen deployment sources, scored by one model."""
    out = []
    for r in range(reps):
        f = grouped_folds(y, groups, seed + r)
        for k in np.unique(f):
            te = np.where(f == k)[0]; tr = np.where(f != k)[0]
            if len(np.unique(y[te])) == 2:
                out.append(roc_auc_score(y[te], fit_predict(kind, X, y, tr, te)))
    return float(np.mean(out))


def pooled(X, y, kind, reps=5):
    out = []
    for s in range(reps):
        p = np.zeros(len(y))
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=s).split(X, y):
            p[te] = fit_predict(kind, X, y, tr, te)
        out.append(roc_auc_score(y, p))
    return float(np.mean(out))


def cluster_ci(y, p, groups, reps=1000, seed=0):
    rng = np.random.default_rng(seed)
    gs = np.unique(groups); idx = {g: np.where(groups == g)[0] for g in gs}
    out = []
    for _ in range(reps):
        take = np.concatenate([idx[g] for g in rng.choice(gs, len(gs), replace=True)])
        if len(np.unique(y[take])) == 2:
            out.append(roc_auc_score(y[take], p[take]))
    return [round(float(np.percentile(out, 2.5)), 3), round(float(np.percentile(out, 97.5)), 3)]


def source_perm(y, groups, rng):
    gs = np.unique(groups)
    lab = np.array([y[groups == g][0] for g in gs])
    perm = dict(zip(gs, rng.permutation(lab)))
    return np.array([perm[g] for g in groups])


def null_dist(fn, y, groups, scheme, perms, seed):
    """fn(y) -> AUROC. Row permutation for pooled; source-level permutation otherwise."""
    def one(i):
        rng = np.random.default_rng(seed + i)
        yp = rng.permutation(y) if scheme == "row" else source_perm(y, groups, rng)
        return fn(yp)
    return np.array(Parallel(n_jobs=-1)(delayed(one)(i) for i in range(perms)))


def summarise(obs, null=None, ci=None):
    d = {"auroc": round(float(obs), 3)}
    if ci is not None:
        d["ci95_source_bootstrap"] = ci
    if null is not None:
        d.update({"null_mean": round(float(null.mean()), 3), "null_p95": round(float(np.percentile(null, 95)), 3),
                  "p": round(float((1 + (null >= obs).sum()) / (1 + len(null))), 4), "perms": int(len(null))})
    return d


def single_feature_aucs(df, cols, top=8):
    out = []
    y = df.y.values
    src = df.groupby("source").agg({**{c: "mean" for c in cols}, "y": "first"})
    for c in cols:
        v = df[c].values
        if np.nanstd(v) == 0:
            continue
        a = roc_auc_score(y, v); s = src[c].values
        b = roc_auc_score(src.y.values, s) if np.std(s) > 0 else 0.5
        out.append({"feature": c, "row_auroc": round(float(a), 3), "source_level_auroc": round(float(b), 3),
                    "higher_means": "evaluation" if a >= 0.5 else "deployment",
                    "row_auroc_best_direction": round(float(max(a, 1 - a)), 3)})
    return sorted(out, key=lambda r: -r["row_auroc_best_direction"])[:top]


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="source_baselines_checks.json")
    ap.add_argument("--hf", default=shutil.which("hf") or str(Path.home() / ".local/bin/hf"))
    ap.add_argument("--perms", type=int, default=200)
    ap.add_argument("--quick", action="store_true", help="few permutations, for a smoke test")
    a = ap.parse_args()
    perms = 12 if a.quick else a.perms
    samples, mcq_dir = fetch(Path(a.cache), a.hf)
    df_all, texts_all, sets = build(samples)
    test = ~df_all.pqsel.values
    df = df_all[test].reset_index(drop=True)
    texts = [t for t, k in zip(texts_all, test) if k]
    # the most common chat system prompt (label-blind): the default the authors add
    sys0 = collections.Counter(text_of(x["input"][0]["content"]) for x in samples
                               if x["metadata"]["scaffold"] is None).most_common(1)[0][0]
    custom_sys = {x["id"]: float(text_of(x["input"][0]["content"]) != sys0) for x in samples}
    df["custom_system_prompt"] = df.id.map(custom_sys)
    res = {"pins": {"hf": f"{HF_REPO}@{HF_SHA}", "dataset_zip_sha256": ZIP_SHA256, "paper": "arXiv:2505.23836v3"},
           "rows": {"released": len(df_all), "held_out_used": len(df), "pqsel_dev": int(df_all.pqsel.sum())},
           "feature_sets": sets,
           "settings": {"perms_lr": perms, "perms_hgb": max(perms // 2, 6), "perms_bow": max(perms // 4, 6),
                        "class_weight": "balanced", "pooled": "stratified 5-fold over rows, 5 repeats",
                        "leave_sources_out": "5 folds of whole sources stratified by class, 5 repeats, mean within-fold AUROC",
                        "loso": "leave one source out, out-of-fold scores pooled"}}

    model_scores = {}
    for f in sorted(mcq_dir.glob("*.csv")):
        m = pd.read_csv(f, usecols=["model", "sample_id", "score"])
        m["id"] = m.sample_id.map(mcq_id)
        model_scores[m.model.iloc[0]] = m.groupby("id").score.mean()
    model_scores["human"] = pd.Series({x["id"]: (x["metadata"]["eval_author1"] + x["metadata"]["eval_author2"]) / 2
                                       for x in samples})

    splits = {"chat": ~df.agentic.values, "agentic": df.agentic.values, "all": np.ones(len(df), bool)}
    combos = {"structure": sets["structure"], "structure+format": sets["structure"] + sets["format"],
              "content_blind_all": sets["structure"] + sets["format"] + sets["scaffold"]}
    rules = {"no_assistant_turn": lambda d: (d.n_asst == 0).astype(float),
             "ends_with_user_turn": lambda d: d.last_user,
             "custom_system_prompt": lambda d: d.custom_system_prompt,
             "multiple_choice_block": lambda d: d.mc_block}
    res["per_split"] = {}
    for sp, mask in splits.items():
        d = df[mask].reset_index(drop=True); y = d.y.values; g = d.source.values
        r = {"n": int(len(d)), "evaluation": int(y.sum()), "deployment": int(len(y) - y.sum()),
             "sources": int(d.source.nunique()),
             "eval_sources": int(d[d.y == 1].source.nunique()), "deploy_sources": int(d[d.y == 0].source.nunique())}
        mr = {}
        for name, s in model_scores.items():
            v = d.id.map(s); ok = v.notna().values
            mr[name] = {"auroc_recomputed": round(float(roc_auc_score(y[ok], v[ok].values)), 3), "n": int(ok.sum()),
                        "paper_auroc": PAPER_AUC.get(name, {}).get(sp),
                        "ci95_source_bootstrap": cluster_ci(y[ok], v[ok].values, g[ok])}
        r["models_and_humans"] = mr
        r["best_model_recomputed"] = max((k for k in mr if k != "human"), key=lambda k: mr[k]["auroc_recomputed"])
        # pre-specified single rules
        rr = {}
        for name, fn in rules.items():
            v = fn(d).values
            fires_src = d.assign(v=v).groupby("source").agg(v=("v", "mean"), y=("y", "first"))
            rr[name] = {"evaluation_rows_firing": int(v[y == 1].sum()), "deployment_rows_firing": int(v[y == 0].sum()),
                        "auroc": round(float(roc_auc_score(y, v)), 3) if np.std(v) > 0 else 0.5,
                        "eval_sources_majority_firing": int(((fires_src.v > 0.5) & (fires_src.y == 1)).sum()),
                        "deploy_sources_majority_firing": int(((fires_src.v > 0.5) & (fires_src.y == 0)).sum())}
        r["single_rules"] = rr
        cb = {}
        for cname, cols in combos.items():
            X = d[cols].values.astype(float)
            cc = {}
            for kind in ("lr", "hgb"):
                np_ = perms if kind == "lr" else max(perms // 2, 6)
                do_null = cname in ("structure", "content_blind_all")
                p_lo = loso(X, y, g, kind)
                obs_lso = leave_sources_out(X, y, g, kind)
                cc[kind] = {
                    "pooled_within_source": summarise(pooled(X, y, kind), null_dist(
                        lambda yp: pooled(X, yp, kind, 1), y, g, "row", np_, 1000) if do_null else None),
                    "leave_one_source_out": summarise(roc_auc_score(y, p_lo), null_dist(
                        lambda yp: roc_auc_score(yp, loso(X, yp, g, kind)), y, g, "source", np_, 2000) if do_null else None,
                        cluster_ci(y, p_lo, g)),
                    "leave_sources_out_5fold": summarise(obs_lso, null_dist(
                        lambda yp: leave_sources_out(X, yp, g, kind, 2), y, g, "source", np_, 3000) if do_null else None),
                }
            cb[cname] = cc
        # bag-of-words reference (not content-blind)
        tx = [t for t, k in zip(texts, mask) if k]
        Xb = TfidfVectorizer(min_df=2, max_features=20000, sublinear_tf=True).fit_transform(tx)

        def bow_fp(yv, tr, te):
            if len(np.unique(yv[tr])) < 2:
                return np.full(len(te), yv[tr].mean())
            return LogisticRegression(C=10, max_iter=5000, class_weight="balanced").fit(
                Xb[tr], yv[tr]).predict_proba(Xb[te])[:, 1]

        def bow_lso(yv, reps=5):
            out = []
            for rp in range(reps):
                f = grouped_folds(yv, g, rp)
                for k in np.unique(f):
                    te = np.where(f == k)[0]; tr = np.where(f != k)[0]
                    if len(np.unique(yv[te])) == 2:
                        out.append(roc_auc_score(yv[te], bow_fp(yv, tr, te)))
            return float(np.mean(out))

        def bow_pooled(yv):
            p = np.zeros(len(yv))
            for tr, te in StratifiedKFold(5, shuffle=True, random_state=0).split(Xb, yv):
                p[te] = bow_fp(yv, tr, te)
            return roc_auc_score(yv, p)
        nb = max(perms // 4, 6)
        cb["bow_reference_not_content_blind"] = {"lr": {
            "pooled_within_source": summarise(bow_pooled(y)),
            "leave_sources_out_5fold": summarise(bow_lso(y), null_dist(lambda yp: bow_lso(yp, 2), y, g, "source", nb, 5000))}}
        r["classifiers"] = cb
        r["top_single_features_in_sample"] = single_feature_aucs(d, combos["content_blind_all"])
        res["per_split"][sp] = r
        print(sp, "done", flush=True)

    # agentic scaffolds used by both classes: train on every other agentic scaffold, test within this one
    ag = df[df.agentic].reset_index(drop=True)
    shared = sorted(s for s in ag.scaffold.unique() if ag[ag.scaffold == s].y.nunique() == 2)
    X = ag[combos["content_blind_all"]].values.astype(float); y = ag.y.values
    ss = {"shared_scaffolds": shared, "by_scaffold": {}}
    for sc in shared:
        te = np.where(ag.scaffold.values == sc)[0]; tr = np.where(ag.scaffold.values != sc)[0]
        e = {"evaluation_sources": sorted(ag.iloc[te][ag.iloc[te].y == 1].source.unique().tolist()),
             "deployment_sources": sorted(ag.iloc[te][ag.iloc[te].y == 0].source.unique().tolist()),
             "evaluation": int(y[te].sum()), "deployment": int(len(te) - y[te].sum())}
        for kind in ("lr", "hgb"):
            e[f"content_blind_all_{kind}_trained_on_other_scaffolds"] = round(
                float(roc_auc_score(y[te], fit_predict(kind, X, y, tr, te))), 3)
            # in-scaffold pooled CV: how separable the two classes are on format once the scaffold is known
            Xs, ys = X[te], y[te]
            e[f"content_blind_all_{kind}_pooled_within_scaffold"] = round(pooled(Xs, ys, kind), 3)
        e["models_and_humans"] = {name: round(float(roc_auc_score(y[te], ag.iloc[te].id.map(s).values)), 3)
                                  for name, s in model_scores.items()}
        ss["by_scaffold"][sc] = e
    res["agentic_shared_scaffolds"] = ss

    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
