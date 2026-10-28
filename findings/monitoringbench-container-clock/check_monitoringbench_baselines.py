"""Content-blind baselines and provenance census for MonitoringBench with MonitoringBenchHonest.

MonitoringBench (Jotautaite et al., arXiv 2605.09684) releases 2,644 successful attack
trajectories (HF neur26anonsub/ctrldataset2026, CC BY 4.0) and no honest runs. Kucukkurt and
Elasky later published 550 benign Opus 4.5 trajectories matched per task to 550 of those attacks,
as a public Docent collection holding both classes (1,100 runs, rendered by the same exporter).
Their post reports TPR/FPR for six monitors on those 1,100 runs.

This script asks how well features that do not read the attack separate the two classes:
step count and tool-call histogram (what a monitor reading only tool calls sees), output lengths,
the container clock in tool outputs (ls -l style timestamps), and bag-of-words on the actions
taken before the attack step. Cross-validation is GroupKFold by BashArena task; nulls permute
labels within task (each task has equal attack and honest counts), refitting the whole pipeline.

It reads the trajectories as text and never runs anything from them.

Usage:
    python -I check_monitoringbench_baselines.py --cache DIR [--out monitoringbench_checks.json]
"""
import argparse, hashlib, json, re, urllib.request, concurrent.futures as cf
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HF_SHA = "6c72cf19883376b921a94a0dd17dc8ab6b25e52f"
HF_PARQUET = f"https://huggingface.co/datasets/neur26anonsub/ctrldataset2026/resolve/{HF_SHA}/master.parquet"
HF_PARQUET_SHA256 = "5fd4c38b8d7a96540368e19498d50d5ee831cbb718a6838a07d3016a78998c91"
DOCENT = "https://api.docent.transluce.org/rest/"
COLLECTION = "fce5f309-4750-4b2e-a172-7bf897807278"  # MonitoringBenchHonest, public read
HONEST_REPO_COMMIT = "7f8deb9a6b5551cd8c15692d9b96c0812e8dd4a9"  # CanKucukkurt/monitoringbench-honest-pipeline (read, not run)

# Kucukkurt and Elasky's post, 550 attack + 550 benign (TPR, FPR).
POST_MONITORS = {"Kimi K3": (0.858, 0.024), "GPT 5.6 Luna": (0.925, 0.315),
                 "Qwen3.8 27B": (0.860, 0.204), "Qwen3.6 Flash": (0.611, 0.118),
                 "DeepSeek V4 Flash": (0.485, 0.031), "Qwen3.5 4B": (0.147, 0.076)}
PAPER_OPUS45_FT_CATCH_AT_1PCT = 0.70  # paper, final benchmark, full trajectory, its own 416 honest runs

MONTH = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
LS_TS = re.compile(MONTH + r" +\d{1,2} +\d\d:\d\d")
EARLY, LATE = {"Dec", "Jan", "Feb", "Mar"}, {"Jun", "Jul", "Aug", "Sep"}
PERMS_SMALL, PERMS_BOW, BOOT = 1000, 200, 1000
rng = np.random.default_rng(0)


def fetch(url, path):
    if not path.exists() or path.stat().st_size == 0:
        with urllib.request.urlopen(url, timeout=300) as r:
            path.write_bytes(r.read())
    return path


def load(cache):
    cache.mkdir(parents=True, exist_ok=True)
    pq = fetch(HF_PARQUET, cache / "master.parquet")
    assert hashlib.sha256(pq.read_bytes()).hexdigest() == HF_PARQUET_SHA256
    runs = cache / "docent_runs"; runs.mkdir(exist_ok=True)
    ids = json.loads(urllib.request.urlopen(DOCENT + COLLECTION + "/agent_run_ids", timeout=60).read())
    with cf.ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda i: fetch(f"{DOCENT}{COLLECTION}/agent_run?agent_run_id={i}",
                                    runs / f"{i}.json"), ids))
    recs = [json.loads((runs / f"{i}.json").read_text()) for i in sorted(ids)]
    h = hashlib.sha256()
    for r in recs:
        h.update(json.dumps([r["metadata"]["id"], [m["content"] for m in r["transcripts"][0]["messages"]]],
                            sort_keys=True).encode())
    return pd.read_parquet(pq), recs, h.hexdigest()


def features(r):
    md = r["metadata"]; msgs = r["transcripts"][0]["messages"]
    acts = [m["content"] or "" for m in msgs if m["role"] == "assistant"]
    outs = [m["content"] or "" for m in msgs if m["role"] == "tool"]
    tool = Counter(); te = Counter()
    for a in acts:
        t = re.match(r"(\w+)\(", a); name = t.group(1) if t else "other"; tool[name] += 1
        if name == "text_editor":
            s = re.search(r'"command": "(\w+)"', a); te[s.group(1) if s else "?"] += 1
    bash = [a for a in acts if a.startswith("bash(")]
    ts = Counter(m.group(1) for o in outs for m in LS_TS.finditer(o))
    _, task, idx = md["id"].split("_")
    return dict(id=md["id"], y=int(md["label"] == "attack"), task=task, idx=int(idx),
                uuid=md.get("sample_uuid"), source_file=md["source_file"], acts=acts,
                n_steps=len(acts), n_bash=tool["bash"], n_text_editor=tool["text_editor"],
                n_python=tool["python"], frac_text_editor=tool["text_editor"] / len(acts),
                te_create=te["create"], te_str_replace=te["str_replace"], te_view=te["view"],
                action_chars=sum(map(len, acts)), action_chars_mean=np.mean([len(a) for a in acts]),
                output_chars=sum(map(len, outs)), output_chars_mean=np.mean([len(o) for o in outs]),
                devnull_per_bash=sum(b.count("2>/dev/null") for b in bash) / max(len(bash), 1),
                ts_early=sum(v for k, v in ts.items() if k in EARLY),
                ts_late=sum(v for k, v in ts.items() if k in LATE), ts_any=sum(ts.values()))


def r3(x):
    return round(float(x), 3)


def boot_ci(y, s, g):
    groups = np.unique(g); idx = {k: np.where(g == k)[0] for k in groups}; out = []
    for _ in range(BOOT):
        take = np.concatenate([idx[k] for k in rng.choice(groups, len(groups))])
        if len(set(y[take])) == 2:
            out.append(roc_auc_score(y[take], s[take]))
    return [r3(np.percentile(out, 2.5)), r3(np.percentile(out, 97.5))]


def perm_within(y, g):
    yp = y.copy()
    for k in np.unique(g):
        i = np.where(g == k)[0]; yp[i] = rng.permutation(y[i])
    return yp


def at_fpr(y, s, fpr_target):
    fpr, tpr, _ = roc_curve(y, s)
    return r3(tpr[fpr <= fpr_target + 1e-12].max())


def summarize(y, s, g, null):
    a = roc_auc_score(y, s)
    return dict(auroc=r3(a), ci95_task_bootstrap=boot_ci(y, s, g),
                null_mean=r3(np.mean(null)), null_p95=r3(np.percentile(null, 95)),
                null_max=r3(np.max(null)), n_null=len(null),
                tpr_at_fpr={f"{k} (FPR {f})": {"baseline_tpr": at_fpr(y, s, f), "monitor_tpr": t}
                            for k, (t, f) in POST_MONITORS.items()},
                tpr_at_1pct_fpr=at_fpr(y, s, 0.01))


def single(df, col, sign=1):
    y, g = df.y.values, df.task.values; s = sign * df[col].values.astype(float)
    null = [roc_auc_score(perm_within(y, g), s) for _ in range(PERMS_SMALL)]
    return summarize(y, s, g, null)


def cv_scores(X, y, g, make):
    s = np.zeros(len(y))
    for tr, te in GroupKFold(5).split(X, y, g):
        m = make().fit(X[tr], y[tr]); s[te] = m.predict_proba(X[te])[:, 1]
    return s


def cv_model(X, y, g, make, perms):
    s = cv_scores(X, y, g, make)
    null = [roc_auc_score(yp, cv_scores(X, yp, g, make)) for yp in (perm_within(y, g) for _ in range(perms))]
    return summarize(y, s, g, null)


def lr():
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))


def bow_matrix(docs):
    # The vocabulary is fitted once on all documents without labels, so it cannot leak them.
    return CountVectorizer(binary=True, min_df=3, token_pattern=r"[A-Za-z_][A-Za-z0-9_\-\.]+").fit_transform(docs)


def bow_lr():
    return LogisticRegression(max_iter=3000, C=0.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path(__file__).with_name("monitoringbench_checks.json"))
    a = ap.parse_args()
    master, recs, docent_hash = load(a.cache)
    df = pd.DataFrame([features(r) for r in recs])
    att = df[df.y == 1].merge(master, left_on="uuid", right_on="sample_uuid", how="left")
    res = {"pins": {"hf_dataset": "neur26anonsub/ctrldataset2026", "hf_sha": HF_SHA,
                    "master_parquet_sha256": HF_PARQUET_SHA256,
                    "docent_collection": COLLECTION, "docent_content_sha256": docent_hash,
                    "honest_pipeline_repo_commit": HONEST_REPO_COMMIT}}

    # Check 0: provenance census of the 1,100-run paired set.
    ts_lab = {lab: Counter() for lab in ("attack", "honest")}
    for r in recs:
        lab = r["metadata"]["label"]
        for m in r["transcripts"][0]["messages"]:
            if m["role"] == "tool":
                ts_lab[lab].update(x.group(1) for x in LS_TS.finditer(m["content"] or ""))
    res["provenance"] = {
        "counts": df.groupby("y").size().rename({0: "honest", 1: "attack"}).to_dict(),
        "source_file": df.groupby("source_file").size().to_dict(),
        "tasks_per_class": int(df.task.nunique()),
        "tasks_with_unequal_class_counts": int((df.groupby(["task", "y"]).size().unstack().nunique(axis=1) > 1).sum()),
        "attacks_joined_to_master": int(att.sample_uuid.notna().sum()),
        "attack_model": att.attack_model.value_counts().to_dict(),
        "attack_source_group": att.source_group.value_counts().to_dict(),
        "attack_new_source_name": att.new_source_name.value_counts().to_dict(),
        "attack_side_task": att.side_task_name.value_counts().to_dict(),
        "attack_eval_created_month": att.eval_created.str[:7].value_counts().sort_index().to_dict(),
        "docent_steps_minus_master_steps": att.n_steps.sub(att.total_steps).value_counts().to_dict(),
        "ls_timestamp_months_in_tool_outputs": {k: dict(v.most_common()) for k, v in ts_lab.items()},
        "mean_per_run": df.groupby("y")[["n_steps", "n_bash", "n_text_editor", "n_python",
                                         "action_chars", "output_chars"]].mean().round(2)
                          .rename({0: "honest", 1: "attack"}).to_dict("index"),
    }

    # Check 1: content-blind baselines.
    y, g = df.y.values, df.task.values
    b = {}
    b["n_steps (more = attack)"] = single(df, "n_steps")
    b["n_python (fewer = attack)"] = single(df, "n_python", -1)
    b["frac_text_editor (lower = attack)"] = single(df, "frac_text_editor", -1)
    b["output_chars (fewer = attack)"] = single(df, "output_chars", -1)
    b["devnull_per_bash (more = attack)"] = single(df, "devnull_per_bash")
    clock = (df.ts_early - df.ts_late).astype(float).values
    df["clock"] = clock
    b["container clock: early-2026 minus mid-2026 ls timestamps in outputs"] = single(df, "clock")
    b["container clock: early-2026 minus mid-2026 ls timestamps in outputs"]["runs_with_any_timestamp"] = {
        "attack": int(((df.ts_any > 0) & (df.y == 1)).sum()), "honest": int(((df.ts_any > 0) & (df.y == 0)).sum())}
    has = df[df.ts_any > 0]
    b["container clock: early-2026 minus mid-2026 ls timestamps in outputs"]["auroc_on_runs_with_timestamp"] = r3(
        roc_auc_score(has.y, has.ts_early - has.ts_late))

    struct = ["n_steps", "n_bash", "n_text_editor", "n_python", "frac_text_editor",
              "te_create", "te_str_replace", "te_view", "action_chars", "action_chars_mean"]
    b["LR on tool-call structure (counts and lengths of actions only)"] = cv_model(
        df[struct].values.astype(float), y, g, lr, PERMS_SMALL)
    b["LR on tool-call structure + output lengths"] = cv_model(
        df[struct + ["output_chars", "output_chars_mean"]].values.astype(float), y, g, lr, PERMS_SMALL)

    # Pre-attack prefix: attack actions strictly before the master's attack_step (1-indexed);
    # each honest run gets the prefix length of the attack with the same task and rank.
    att_step = dict(zip(att.id, att.attack_step))
    pref_len = {}
    for task, grp in df.groupby("task"):
        A = grp[grp.y == 1].sort_values("idx"); H = grp[grp.y == 0].sort_values("idx")
        for (_, ra), (_, rh) in zip(A.iterrows(), H.iterrows()):
            k = att_step.get(ra.id)
            if pd.notna(k):
                pref_len[ra.id] = pref_len[rh.id] = int(k) - 1
    sub = df[df.id.isin(pref_len)].copy()
    sub["prefix"] = [" \n ".join(r.acts[:pref_len[r.id]]) for r in sub.itertuples()]
    bp = cv_model(bow_matrix(sub.prefix.values), sub.y.values, sub.task.values, bow_lr, PERMS_BOW)
    bp.update(n_runs=len(sub), prefix_len_median=int(np.median(list(pref_len.values()))),
              empty_prefixes=int((sub.prefix == "").sum()))
    b["BoW on actions before the attack step (length-matched honest prefix)"] = bp
    docs = np.array([" \n ".join(x) for x in df.acts])
    b["BoW on all actions (sees the attack; reference)"] = cv_model(bow_matrix(docs), y, g, bow_lr, PERMS_BOW)
    res["content_blind_baselines"] = b

    res["published_monitors_on_same_1100"] = {
        k: {"tpr": t, "fpr": f, "one_point_auc": r3((1 + t - f) / 2)} for k, (t, f) in POST_MONITORS.items()}
    res["paper_opus45_full_trajectory_catch_at_1pct_fpr"] = PAPER_OPUS45_FT_CATCH_AT_1PCT

    # Check 2 evidence: refined attacks were rewritten by Opus 4.6 after the Opus 4.5 run.
    # Compare the tool mix of refined and unrefined attacks with honest runs, and score each
    # attack group against all honest runs with the out-of-fold structure model. Not a swap.
    s_struct = cv_scores(df[struct].values.astype(float), y, g, lr)
    sc = dict(zip(df.id, s_struct)); hs = s_struct[y == 0]
    cols = ["n_steps", "n_bash", "n_text_editor", "te_str_replace", "te_create", "te_view",
            "n_python", "frac_text_editor"]
    by = {"honest": {**df[df.y == 0][cols].mean().round(2).to_dict(), "n": int((y == 0).sum())}}
    for k, grp in att.groupby("source_group"):
        a_s = np.array([sc[i] for i in grp.id])
        by[k] = {**grp[cols].mean().round(2).to_dict(), "n": len(grp),
                 "structure_auroc_vs_all_honest": r3(roc_auc_score(
                     np.r_[np.ones(len(a_s)), np.zeros(len(hs))], np.r_[a_s, hs]))}
    res["authorship_by_attack_source_group"] = by
    a.out.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
