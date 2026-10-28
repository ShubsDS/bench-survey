"""Row-level checks on METR's MALT transcripts (public split, default config).

Leads tested (see README.md):
  2/1  one-model confound: can sandbagging vs benign be predicted from model-identity and
       content-blind signatures alone, with task-grouped CV and a within-task shuffled null;
       then restricted to Claude 3.7 Sonnet only.
  7    instruction visible: does the transcript (and the monitor-format file) carry the injected
       sandbagging instruction; does the rewritten reasoning still name it.
  3/5  prompted vs natural positives; exact and near-duplicate transcripts.

Outputs hold aggregates, counts and run/task ids only, never transcript text.

    python -I check_transcripts.py --cache data

Downloads (gated; needs `hf auth login` with access granted):
  metr-evals/malt-transcripts-public@TRANSCRIPTS_SHA  data/*            (~1.6 GB)
  metr-evals/malt-public@PUBLIC_SHA                   two data/ shards (~24 MB)
"""
import argparse, collections, glob, hashlib, json, re, subprocess, zlib
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

TRANSCRIPTS_SHA = "3521e8e22b6af12fea3249443e554b96b6fc4f49"
PUBLIC_SHA = "6100006c2fd23d81e5afe2b1cc3bf3f3fff48df1"
PUBLIC_SHARDS = ["data/public-00035-of-00042.parquet", "data/public-00038-of-00042.parquet"]
HF = str(Path.home() / ".local/bin/hf")

# Sandbagging labels as in ../malt-sandbagging-one-model (1,237 full / 834 public). The post's
# 1,505 prompted runs also count prompted reasoning_about_task; reported as a variant.
SANDBAG = {"match_weaker_model", "partial_problem_solving", "refusals", "sabotage"}
NATURAL_SANDBAG_LIKE = {"gives_up", "reasoning_about_task"}
POST_BEST_SANDBAG_AUROC = 0.91  # best monitor, full dataset, METR post (no per-run scores shipped)

TOOLS = ["bash", "python", "submit", "score", "score_log", "set_timeout", "rate_options",
         "submit_review", "run_bash", "run_python", "advise"]
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
LS_DATE = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{2}:\d{2}\b")
INSTR = re.compile(r"(?m)^\s*Instructions:")
# Words naming the prompted behaviour or the instruction; applied to the agent's own text.
CUE = re.compile(r"sabotag|sandbag|subtle (?:flaw|issue|bug)|weaker (?:ai )?model|underperform|"
                 r"intentional|deliberate|i was (?:told|instructed)|been instructed|my instructions|"
                 r"evaluation or (?:training|deployment)|being tested|partial solution|refuse", re.I)
# Narrow: the agent referring to having been instructed (what the Sonnet 4 rewrite was meant to remove).
INSTR_MENTION = re.compile(r"\b(?:i (?:was|am|have been|'ve been) (?:told|instructed|asked) to|"
                           r"(?:my|the) (?:system )?instructions? (?:say|tell|are|is|ask)|system prompt|"
                           r"i(?:'m| am) supposed to (?:sabotage|refuse|underperform|perform like))", re.I)


def download(cache):
    t = cache / "malt-transcripts-public"
    if not list((t / "data").glob("*.parquet")):
        subprocess.run([HF, "download", "metr-evals/malt-transcripts-public", "--repo-type", "dataset",
                        "--revision", TRANSCRIPTS_SHA, "--include", "data/*", "--local-dir", str(t)], check=True)
    p = cache / "malt-public"
    if not all((p / s).exists() for s in PUBLIC_SHARDS):
        subprocess.run([HF, "download", "metr-evals/malt-public", *PUBLIC_SHARDS, "--repo-type", "dataset",
                        "--revision", PUBLIC_SHA, "--local-dir", str(p)], check=True)
    return sorted((t / "data").glob("*.parquet")), [p / s for s in PUBLIC_SHARDS]


def run_features(r):
    nodes = r["nodes"]
    f = collections.Counter()
    sys_txt, reason, compl, ts, months = [], [], [], [], collections.Counter()
    branches = set()
    for n in nodes:
        d = n["node_data"]; m = d["message"]; md = d["metadata"] or {}
        c = m["content"] or ""; role = m["role"]
        branches.add(n["branch_id"])
        if d["first_called_at"]: ts.append(d["first_called_at"])
        f["n_nodes"] += 1; f[f"n_{role}"] += 1; f[f"ch_{role}"] += len(c)
        fc = m["function_call"]
        if fc and fc.get("name"):
            f["n_tool_calls"] += 1
            f["tool_" + (fc["name"] if fc["name"] in TOOLS else "other")] += 1
            f["ch_tool_args"] += len(fc.get("arguments") or "")
        if role == "system":
            sys_txt.append(c)
        elif role == "assistant":
            if md.get("completion_type") == "reasoning_completion":
                f["n_reasoning"] += 1; f["ch_reasoning"] += len(c); reason.append(c)
                f["reason_nl_start"] += c.startswith("\n")
            else:
                f["n_completion"] += 1; f["ch_completion"] += len(c); compl.append(c)
                f["compl_ill_start"] += c.startswith("I'll")
        elif role == "function":
            months.update(LS_DATE.findall(c))
        if role == "user" and c.startswith("So far in this attempt"):
            f["n_time_msgs"] += 1
    s = "\n".join(sys_txt)
    a = "\n".join(reason + compl)
    out = dict(f)
    out.update(
        n_branches=len(branches),
        sys_hash=hashlib.md5(s.encode()).hexdigest()[:12] if sys_txt else "NONE",
        sys_len=len(s), sys_has_instructions=bool(INSTR.search(s)),
        sys_made_by_openai="made by OpenAI" in s,
        cue_reasoning=len(CUE.findall("\n".join(reason))), cue_completion=len(CUE.findall("\n".join(compl))),
        instr_mention_reasoning=len(INSTR_MENTION.findall("\n".join(reason))),
        instr_mention_completion=len(INSTR_MENTION.findall("\n".join(compl))),
        ls_month=(MONTHS.index(months.most_common(1)[0][0]) + 1) if months else 0,
        t_start=min(ts) if ts else np.nan, t_span=(max(ts) - min(ts)) if ts else np.nan,
        hash_assistant=hashlib.md5(a.encode()).hexdigest()[:16],
        hash_all=hashlib.md5("\x00".join((n["node_data"]["message"]["content"] or "") for n in nodes).encode()).hexdigest()[:16],
    )
    return out, a[:100_000]


def extract(files, cache):
    fp, tp = cache / "features.parquet", cache / "assistant_vectors.npz"
    if fp.exists() and tp.exists():
        df = pd.read_parquet(fp)
        if "instr_mention_reasoning" in df:
            return df, np.load(tp, allow_pickle=False)
    meta_cols = ["run_id", "labels", "task_id", "model", "has_chain_of_thought", "run_source", "manually_reviewed"]
    rows, texts = [], []
    for f in files:
        pf = pq.ParquetFile(f)
        for rg in range(pf.num_row_groups):
            for r in pf.read_row_group(rg, columns=meta_cols + ["nodes"]).to_pylist():
                feat, a = run_features(r)
                feat.update({k: r[k] for k in meta_cols})
                rows.append(feat); texts.append(a)
    df = pd.DataFrame(rows)
    df["labels"] = df["labels"].apply(lambda x: ",".join(sorted(x)))
    df = df.fillna({c: 0 for c in df.columns if c.startswith(("n_", "ch_", "tool_", "reason_", "compl_"))})
    # Near-duplicate vectors: binary word 3-grams of the agent's own text (first 100k chars), hashed.
    hv = HashingVectorizer(analyzer="word", ngram_range=(3, 3), n_features=2 ** 20, binary=True, norm="l2",
                           alternate_sign=False, lowercase=True)
    X = hv.transform(texts).tocsr()
    np.savez(tp, data=X.data, indices=X.indices, indptr=X.indptr, shape=np.array(X.shape))
    df.to_parquet(fp)
    return df, np.load(tp, allow_pickle=False)


def label_sets(df):
    lab = df["labels"].str.split(",").apply(set)
    df["is_sandbag"] = lab.apply(lambda s: bool(s & SANDBAG))
    df["is_sandbag_incl_rat"] = df.is_sandbag | ((df.run_source == "prompted") & lab.apply(lambda s: "reasoning_about_task" in s))
    df["is_normal"] = lab.apply(lambda s: s == {"normal"})
    df["is_natural_sandbag_like"] = (df.run_source == "unprompted") & lab.apply(lambda s: bool(s & NATURAL_SANDBAG_LIKE))
    df["is_37"] = df.model.str.startswith("claude-3-7-sonnet")
    df["is_claude4"] = df.model.isin(["claude-opus-4-20250514", "claude-sonnet-4-20250514"])
    df["family"] = df.task_id.str.split("/").str[0]
    return df


def feature_groups(df):
    count_cols = sorted(c for c in df.columns if c.startswith(("n_", "ch_", "tool_")))
    for c in count_cols:
        df["log_" + c] = np.log1p(df[c].astype(float))
    df["frac_reason_nl"] = df.reason_nl_start / df.n_reasoning.clip(lower=1)
    df["frac_compl_ill"] = df.compl_ill_start / df.n_completion.clip(lower=1)
    df["tool_per_node"] = df.n_tool_calls / df.n_nodes.clip(lower=1)
    length = ["log_n_nodes", "log_n_assistant", "log_n_function", "log_n_user", "log_n_reasoning",
              "log_n_completion", "log_n_tool_calls", "log_n_branches", "log_ch_assistant", "log_ch_function",
              "log_ch_user", "log_ch_reasoning", "log_ch_completion", "log_ch_tool_args", "log_n_time_msgs"]
    df["log_n_branches"] = np.log1p(df.n_branches)
    quirks = ["frac_reason_nl", "frac_compl_ill", "tool_per_node"] + [f"log_tool_{t}" for t in TOOLS + ["other"] if f"log_tool_{t}" in df]
    return {
        "length_and_counts": length,
        "format_quirks_and_tool_mix": quirks,
        "content_blind_all": length + quirks,
        "visible_clock_ls_month": ["ls_month"],
        "system_prompt_scaffold": ["sys_len", "sys_made_by_openai"],
        "system_prompt_instruction_regex": ["sys_has_instructions"],
        "agent_text_cue_regex": ["cue_reasoning", "cue_completion"],
        "agent_instruction_mention_regex": ["instr_mention_reasoning", "instr_mention_completion"],
        "run_start_time_metadata_not_in_messages": ["t_start"],
    }


def oof_scores(X, y, groups, seed=0):
    s = np.zeros(len(y))
    for tr, te in GroupKFold(n_splits=5).split(X, y, groups):
        if len(np.unique(y[tr])) < 2:
            s[te] = 0.5; continue
        m = HistGradientBoostingClassifier(max_iter=100, learning_rate=0.1, random_state=seed).fit(X[tr], y[tr])
        s[te] = m.predict_proba(X[te])[:, 1]
    return s


def within_task_shuffle(y, groups, rng):
    y2 = y.copy()
    for g in np.unique(groups):
        i = np.where(groups == g)[0]
        y2[i] = rng.permutation(y2[i])
    return y2


def task_bootstrap(y, s, groups, rng, n=1000):
    ug = np.unique(groups); idx = {g: np.where(groups == g)[0] for g in ug}
    out = []
    for _ in range(n):
        ii = np.concatenate([idx[g] for g in rng.choice(ug, len(ug))])
        if len(np.unique(y[ii])) == 2:
            out.append(roc_auc_score(y[ii], s[ii]))
    return [round(float(np.percentile(out, 2.5)), 3), round(float(np.percentile(out, 97.5)), 3)]


def evaluate(df, pos, neg, groups_def, nulls, rng, null_groups=("content_blind_all",)):
    d = df[pos | neg].copy()
    y = pos[pos | neg].values.astype(int)
    g = d.task_id.values
    tasks_pos, tasks_neg = set(d.task_id[y == 1]), set(d.task_id[y == 0])
    shared = tasks_pos & tasks_neg
    res = {"n_pos": int(y.sum()), "n_neg": int((1 - y).sum()), "tasks_pos": len(tasks_pos), "tasks_neg": len(tasks_neg),
           "tasks_shared": len(shared),
           "runs_on_shared_tasks": {"pos": int(((y == 1) & d.task_id.isin(shared).values).sum()),
                                    "neg": int(((y == 0) & d.task_id.isin(shared).values).sum())},
           "models_pos": d[y == 1].model.value_counts().to_dict(), "models_neg": d[y == 0].model.value_counts().to_dict(),
           "groups": {}}
    for name, cols in groups_def.items():
        X = d[cols].astype(float).values
        if name.endswith("regex"):
            s = X.sum(axis=1)  # a rule (match count), not a fitted model
        else:
            s = oof_scores(X, y, g)
        r = {"auroc": round(float(roc_auc_score(y, s)), 3), "task_bootstrap_95": task_bootstrap(y, s, g, rng)}
        sh = d.task_id.isin(shared).values
        if sh.sum() and len(np.unique(y[sh])) == 2:
            r["auroc_on_shared_tasks_only"] = round(float(roc_auc_score(y[sh], s[sh])), 3)
        if name in null_groups and nulls:
            nl = [roc_auc_score(yy, oof_scores(X, yy, g, seed=k)) for k, yy in
                  enumerate(within_task_shuffle(y, g, rng) for _ in range(nulls))]
            r["within_task_shuffle_null"] = {"n": nulls, "mean": round(float(np.mean(nl)), 3),
                                             "p95": round(float(np.percentile(nl, 95)), 3),
                                             "max": round(float(np.max(nl)), 3)}
        res["groups"][name] = r
    # Family-only baseline under task-grouped CV (can a held-out task's family give the label away?)
    fam = pd.get_dummies(d.family).astype(float).values
    res["groups"]["task_family_only"] = {"auroc": round(float(roc_auc_score(y, oof_scores(fam, y, g))), 3)}
    return res


def near_duplicates(df, Z, thr=0.9):
    from scipy.sparse import csr_matrix
    X = csr_matrix((Z["data"], Z["indices"], Z["indptr"]), shape=tuple(Z["shape"]))
    nonempty = np.asarray(X.getnnz(axis=1) > 50)
    idx = np.where(nonempty)[0]
    Xs = X[idx]
    pairs = []
    for i0 in range(0, len(idx), 500):
        S = (Xs[i0:i0 + 500] @ Xs.T).tocoo()
        for a, b, v in zip(S.row + i0, S.col, S.data):
            if a < b and v >= thr:
                pairs.append((idx[a], idx[b], float(v)))
    cls = np.where(df.is_sandbag | df.is_sandbag_incl_rat, "prompted_pos",
                   np.where(df.is_normal, "normal", "other_pos"))
    kinds = collections.Counter()
    same_task = 0; examples = []
    for a, b, v in pairs:
        kinds[" vs ".join(sorted([cls[a], cls[b]]))] += 1
        same_task += df.task_id.iat[a] == df.task_id.iat[b]
        if cls[a] != cls[b] and len(examples) < 20:
            examples.append({"run_ids": [int(df.run_id.iat[a]), int(df.run_id.iat[b])], "cosine": round(v, 3),
                             "task_ids": [df.task_id.iat[a], df.task_id.iat[b]],
                             "labels": [df.labels.iat[a], df.labels.iat[b]], "models": [df.model.iat[a], df.model.iat[b]]})
    runs_in_pairs = len({x for a, b, _ in pairs for x in (a, b)})
    return {"threshold_cosine_word3gram": thr, "runs_compared": int(nonempty.sum()), "pairs": len(pairs),
            "runs_in_any_pair": runs_in_pairs, "pairs_same_task": int(same_task),
            "pairs_by_class": dict(kinds), "cross_class_examples": examples}


def monitor_format_check(shards, df):
    """In malt-public (the input/output representation), is the instruction in each sample's input?"""
    pos_ids = set(df.run_id[df.run_source == "prompted"])
    c = collections.Counter()
    for f in shards:
        for r in pq.read_table(f, columns=["samples", "metadata"]).to_pylist():
            k = "prompted" if r["metadata"]["run_id"] in pos_ids else "unprompted"
            c[(k, "runs")] += 1
            for s in r["samples"]:
                sys_c = "\n".join((m["content"] or "") for m in s["input"] if m["role"] == "system")
                c[(k, "samples")] += 1
                c[(k, "samples_with_instruction_block_in_input")] += bool(INSTR.search(sys_c))
    return {f"{a}:{b}": v for (a, b), v in sorted(c.items())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--nulls", type=int, default=100)
    ap.add_argument("--out", default="transcripts_checks.json")
    a = ap.parse_args()
    cache = Path(a.cache); cache.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(0)
    files, shards = download(cache)
    df, Z = extract(files, cache)
    df = label_sets(df)
    G = feature_groups(df)
    reviewed_normal = df.is_normal & df.manually_reviewed
    out = {"pins": {"metr-evals/malt-transcripts-public": TRANSCRIPTS_SHA, "metr-evals/malt-public": PUBLIC_SHA,
                    "malt-public shards read": PUBLIC_SHARDS},
           "runs": len(df), "tasks": int(df.task_id.nunique()),
           "monitor_scores_shipped": False,
           "post_best_sandbagging_monitor_auroc_full_dataset": POST_BEST_SANDBAG_AUROC,
           "feature_groups": G}

    # --- check 7: the injected instruction in the transcript -------------------------------
    sp = df.groupby(["run_source", "is_37"]).agg(runs=("run_id", "size"), sys_instructions=("sys_has_instructions", "sum"),
                                                sys_made_by_openai=("sys_made_by_openai", "sum"),
                                                distinct_system_prompts=("sys_hash", "nunique")).reset_index()
    pos_hashes = set(df.sys_hash[df.run_source == "prompted"]); neg_hashes = set(df.sys_hash[df.run_source == "unprompted"])
    lab_by_hash = df[df.run_source == "prompted"].groupby("sys_hash").labels.nunique()
    out["check7_instruction_in_transcript"] = {
        "by_run_source_and_37": sp.to_dict(orient="records"),
        "prompted_system_prompt_variants": len(pos_hashes),
        "variants_shared_with_any_unprompted_run": len(pos_hashes & neg_hashes),
        "variants_mapping_to_one_label": int((lab_by_hash == 1).sum()),
        "monitor_format_file_malt_public": monitor_format_check(shards, df),
    }

    # --- 2/1 one-model confound -------------------------------------------------------------
    comps = {
        "A_published_sandbag_vs_reviewed_benign": (df.is_sandbag, reviewed_normal),
        "A2_incl_prompted_reasoning_about_task_vs_reviewed_benign": (df.is_sandbag_incl_rat, reviewed_normal),
        "B_model_probe_37_benign_vs_claude4_reviewed_benign": (df.is_37 & df.is_normal, df.is_claude4 & reviewed_normal),
        "C_37_only_sandbag_vs_37_unreviewed_benign": (df.is_sandbag, df.is_37 & df.is_normal),
    }
    out["confound"] = {k: evaluate(df, p, n, G, a.nulls, rng) for k, (p, n) in comps.items()}
    # Natural positives: unprompted gives_up / reasoning_about_task against reviewed benign.
    out["prompted_vs_natural"] = {
        "natural_sandbag_like_runs": df[df.is_natural_sandbag_like].groupby("model").size().to_dict(),
        "natural_with_instruction_block": int(df.sys_has_instructions[df.is_natural_sandbag_like].sum()),
        "prompted_with_instruction_block": f"{int(df.sys_has_instructions[df.run_source == 'prompted'].sum())}/{int((df.run_source == 'prompted').sum())}",
        "unprompted_with_instruction_block": f"{int(df.sys_has_instructions[df.run_source == 'unprompted'].sum())}/{int((df.run_source == 'unprompted').sum())}",
        "D_prompted_sandbag_vs_natural_sandbag_like": evaluate(df, df.is_sandbag, df.is_natural_sandbag_like, G, 0, rng),
    }
    # --- 5 duplicates -----------------------------------------------------------------------
    ex_a = df[df.hash_assistant.duplicated(keep=False) & (df.ch_assistant > 0)]
    ex_all = df[df.hash_all.duplicated(keep=False)]
    out["duplicates"] = {
        "run_ids_unique": bool(df.run_id.is_unique),
        "exact_same_full_transcript_runs": len(ex_all),
        "exact_same_agent_text_runs": len(ex_a),
        "exact_same_agent_text_groups_crossing_classes": int(ex_a.groupby("hash_assistant").apply(
            lambda x: (x.is_sandbag | x.is_sandbag_incl_rat).nunique() > 1).sum()) if len(ex_a) else 0,
        "near_duplicates": near_duplicates(df, Z),
    }
    Path(a.out).write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print(json.dumps({k: v for k, v in out.items() if k not in ("feature_groups",)}, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
