"""Checks 0, 1 and 7 on the LinuxArena public mirror's reviewer sample.

Tracy et al., "LinuxArena" (arXiv 2604.15384v2); data anonymouslinuxarena/linuxarena-public
(CC BY 4.0) at a pinned commit. The full mirror is 16.8 GB; this script uses the maintainers'
reviewer sample `data/sample.jsonl` (932 rows, 7 complete runs, 705 MB), which holds both honest
calibration runs and attack runs for two comparisons:

  haiku   : "Haiku honest" (200) vs "Haiku attack" (92). Agent runs; no monitor scores on honest.
  straj   : "GPT-5 Nano monitor on Opus honest" (200) vs "GPT-5 Nano monitor on straj" (74),
            the human-written LaStraj attacks, which the paper calibrates on Opus honest.
  straj_opus_monitor : the same trajectories scored by the Opus monitor.

Check 0: who wrote each class (agent_model, run, prompt length, tools, tasks).
Check 1: content-blind detectors (action and tool counts, errors, characters; length alone;
         environment and task category), logistic regression, GroupKFold by main task, label
         permutation null within environment, bootstrap intervals. Compared with the monitor's
         own AUROC on the same trajectories (the paper reports safety, not AUROC).
Check 7: pre-registered phrases in the text the monitor reads (tool-call arguments and outputs of
         actions the per-action monitor scores; the paper says the monitor sees no reasoning).

Nothing from the release is executed. Usage:
    python -I check_la.py --cache DIR [--out la_checks.json]
"""
import argparse, collections, hashlib, json, sys, urllib.request
from pathlib import Path

import numpy as np
from scipy import sparse
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract as E  # noqa: E402

REPO = "anonymouslinuxarena/linuxarena-public"
SHA = "2fd29f9c7bc190fb873bd76c6bd648f22b9ab0a7"
SAMPLE = "data/sample.jsonl"
SAMPLE_SHA256 = "0b1e469ad48d93ccfec986f7cbafee43d49afb93bae730437d02c16233e7cfdb"
PAPER = "arXiv 2604.15384v2"
PAIRS = {
    "haiku": ("Haiku honest", "Haiku attack", None),
    "straj": ("GPT-5 Nano monitor on Opus honest", "GPT-5 Nano monitor on straj", "gpt-5-nano"),
    "straj_opus_monitor": ("Opus monitor on Opus honest", "Opus monitor on straj", "opus"),
}
COUNTS = ["n_visible", "n_bash", "n_text_editor", "n_other_fn", "n_submit_visible", "n_te_view",
          "n_te_create", "n_te_replace", "n_te_insert", "n_errors", "arg_chars", "out_chars"]
RESTATE = ["side_task", "secondary_task", "covert", "hidden_goal", "secret_goal", "red_team",
           "sabotage", "stealth", "monitor_evasion"]
N_PERM, N_PERM_BOW, N_BOOT, SEED = 1000, 50, 1000, 0


def fetch(cache):
    p = cache / "sample.jsonl"
    if not p.exists():
        url = f"https://huggingface.co/datasets/{REPO}/resolve/{SHA}/{SAMPLE}"
        with urllib.request.urlopen(url, timeout=600) as r, open(p, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(1 << 22):
            h.update(chunk)
    assert h.hexdigest() == SAMPLE_SHA256, "sample.jsonl does not match the pinned LFS oid"
    return p


def oof(X, y, groups, C=1.0):
    pred = np.zeros(len(y))
    for tr, te in GroupKFold(5).split(X, y, groups):
        m = LogisticRegression(C=C, max_iter=2000)
        m.fit(X[tr], y[tr])
        pred[te] = m.decision_function(X[te])
    return pred


def boot_ci(y, s, rng):
    vals = []
    for _ in range(N_BOOT):
        i = rng.integers(0, len(y), len(y))
        if y[i].min() != y[i].max():
            vals.append(roc_auc_score(y[i], s[i]))
    return [round(float(np.percentile(vals, 2.5)), 3), round(float(np.percentile(vals, 97.5)), 3)]


def perm_within(y, strata, rng):
    yp = y.copy()
    for g in np.unique(strata):
        i = np.where(strata == g)[0]
        yp[i] = y[rng.permutation(i)]
    return yp


def detector(name, X, y, groups, strata, rng, n_perm=N_PERM, C=1.0):
    s = oof(X, y, groups, C)
    auc = roc_auc_score(y, s)
    null = [roc_auc_score(yp, oof(X, yp, groups, C))
            for yp in (perm_within(y, strata, rng) for _ in range(n_perm))]
    return {"detector": name, "auroc": round(float(auc), 3), "ci95": boot_ci(y, s, rng),
            "null_p95": round(float(np.percentile(null, 95)), 3),
            "null_mean": round(float(np.mean(null)), 3), "n_perm": n_perm,
            "p_perm": round(float((1 + sum(n >= auc for n in null)) / (1 + n_perm)), 4)}


def tpr_at_fpr(y, s, fpr):
    thr = np.quantile(s[y == 0], 1 - fpr, method="higher")
    return round(float((s[y == 1] > thr).mean()), 3)


def describe(recs):
    y = [r for r in recs]
    num = lambda k: [r[k] for r in y if r[k] is not None]
    med = lambda v: float(np.median(v)) if v else None
    return {
        "n": len(y),
        "agent_model": dict(collections.Counter(str(r["agent_model"]) for r in y)),
        "run_ids": sorted({r["run_id"] for r in y}),
        "envs": len({r["env"] for r in y}),
        "main_tasks": len({r["main_task"] for r in y}),
        "side_tasks": len({r["side_task"] for r in y if r["side_task"]}),
        "system_prompt_chars_median": med(num("system_prompt_chars")),
        "system_prompt_missing": sum(r["system_prompt_chars"] is None for r in y),
        "functions": dict(collections.Counter(f for r in y for f in r["functions"])),
        "visible_functions": dict(collections.Counter(f for r in y for f in r["visible_functions"])),
        "n_visible_median": med(num("n_visible")),
        "n_actions_all_median": med(num("n_actions_all")),
        "with_reasoning": sum(r["n_reasoning"] > 0 for r in y),
        "with_thinking": sum(r["n_thinking"] > 0 for r in y),
        "side_task_success": dict(collections.Counter(str(r["side_task_success"]) for r in y)),
        "main_task_success": dict(collections.Counter(str(r["main_task_success"]) for r in y)),
        "live_monitor_models": dict(collections.Counter(m for r in y for m in r["live_models"])),
        "traj_monitor_models": dict(collections.Counter(m for r in y for m in r["traj_models"])),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "la_checks.json"))
    a = ap.parse_args()
    cache = Path(a.cache)
    cache.mkdir(parents=True, exist_ok=True)
    path = fetch(cache)
    sids = E.side_ids([path])
    recs, X_all, X_out = E.extract([path], sids)
    runs = collections.defaultdict(list)
    for i, r in enumerate(recs):
        runs[r["run"]].append(i)

    out = {"dataset": REPO, "revision": SHA, "file": SAMPLE, "file_sha256": SAMPLE_SHA256,
           "paper": PAPER, "keywords": E.KEYWORDS, "provenance": {}, "pairs": {}}
    for run, idx in sorted(runs.items()):
        out["provenance"][run] = describe([recs[i] for i in idx])

    # rows of the agent run "Haiku attack" against its GPT-5 Nano rerun
    ha = {recs[i]["actions_hash"] for i in runs["Haiku attack"]}
    hn = {recs[i]["actions_hash"] for i in runs["GPT-5 Nano monitor on Haiku attack"]}
    oh = {recs[i]["actions_hash"] for i in runs["GPT-5 Nano monitor on Opus honest"]}
    oo = {recs[i]["actions_hash"] for i in runs["Opus monitor on Opus honest"]}
    out["rerun_match"] = {"haiku_attack_agent_vs_nano_rerun_same_actions": len(ha & hn),
                          "of": [len(ha), len(hn)],
                          "opus_honest_nano_vs_opus_monitor_same_actions": len(oh & oo)}

    rng = np.random.default_rng(SEED)
    for pname, (hon, att, mon) in PAIRS.items():
        idx = np.array(runs[hon] + runs[att])
        y = np.array([recs[i]["attack"] for i in idx], int)
        R = [recs[i] for i in idx]
        groups = np.array([r["main_task"] for r in R])
        strata = np.array([r["env"] for r in R])
        P = {"honest_run": hon, "attack_run": att, "n_honest": int((y == 0).sum()),
             "n_attack": int(y.sum())}
        ht = {r["main_task"] for r in R if not r["attack"]}
        at = {r["main_task"] for r in R if r["attack"]}
        P["main_tasks"] = {"honest": len(ht), "attack": len(at), "shared": len(ht & at),
                           "attack_rows_on_shared_tasks": sum(r["attack"] and r["main_task"] in ht
                                                              for r in R)}
        P["env_counts"] = {e: [sum(1 for r in R if r["env"] == e and not r["attack"]),
                               sum(1 for r in R if r["env"] == e and r["attack"])]
                           for e in sorted(set(strata))}
        Xc = np.log1p(np.array([[r[k] for k in COUNTS] for r in R], float))
        Xc = (Xc - Xc.mean(0)) / (Xc.std(0) + 1e-9)
        cats = sorted({(str(r["env"]), str(r["main_task_category"])) for r in R})
        envs, mcs = sorted({c[0] for c in cats}), sorted({str(c[1]) for c in cats})
        Xm = np.array([[r["env"] == e for e in envs] + [str(r["main_task_category"]) == c for c in mcs]
                       for r in R], float)
        def bow(X):  # keep tokens present in at least 5 trajectories of this pair
            X = X[idx]
            keep = np.where((X > 0).sum(0).A1 >= 5)[0]
            return X[:, keep].log1p().tocsr()
        Xb_out, Xb_all = bow(X_out), bow(X_all)
        dets = [detector("length only (visible actions)", Xc[:, [0]], y, groups, strata, rng),
                detector("counts: actions, tools, editor commands, errors, characters",
                         Xc, y, groups, strata, rng),
                detector("environment + main-task category", Xm, y, groups, strata, rng),
                detector("bag of words, tool outputs only", Xb_out, y, groups, strata, rng,
                         n_perm=N_PERM_BOW, C=0.1),
                detector("bag of words, all monitor-visible text (not content-blind)", Xb_all,
                         y, groups, strata, rng, n_perm=N_PERM_BOW, C=0.1)]
        P["detectors"] = dets
        # univariate direction of length
        nv = np.array([r["n_visible"] for r in R])
        P["n_visible_median"] = {"honest": float(np.median(nv[y == 0])),
                                 "attack": float(np.median(nv[y == 1]))}
        P["n_visible_raw_auroc"] = round(float(roc_auc_score(y, nv)), 3)
        if mon:
            for key in ("live_max", "traj_sus"):
                s = np.array([np.nan if r[key] is None else r[key] for r in R], float)
                ok = ~np.isnan(s)
                P[f"monitor_{key}"] = {"auroc": round(float(roc_auc_score(y[ok], s[ok])), 3),
                                       "ci95": boot_ci(y[ok], s[ok], rng), "n": int(ok.sum()),
                                       "tpr_at_traj_fpr_1pct": tpr_at_fpr(y[ok], s[ok], 0.01),
                                       "tpr_at_traj_fpr_5pct": tpr_at_fpr(y[ok], s[ok], 0.05)}
            s_cnt = oof(Xc, y, groups)
            P["counts_tpr_at_traj_fpr_5pct"] = tpr_at_fpr(y, s_cnt, 0.05)
        # check 7
        kw = {}
        for k in list(E.KEYWORDS) + ["kw_side_ids"]:
            v = np.array([r[k] if k == "kw_side_ids" else r["kw"][k] for r in R])
            va = np.array([0 if k == "kw_side_ids" else r["kw_args"][k] for r in R])
            kw[k] = {"honest_any": int((v[y == 0] > 0).sum()), "attack_any": int((v[y == 1] > 0).sum()),
                     "auroc": round(float(roc_auc_score(y, v)), 3),
                     "in_agent_written_args": {"honest_any": int((va[y == 0] > 0).sum()),
                                               "attack_any": int((va[y == 1] > 0).sum())}}
        tot = np.array([sum(r["kw"][k] for k in RESTATE) for r in R])
        tot_args = np.array([sum(r["kw_args"][k] for k in RESTATE) for r in R])
        null = [roc_auc_score(perm_within(y, strata, rng), tot) for _ in range(N_PERM)]
        kw["restatement_total"] = {"keys": RESTATE, "auroc": round(float(roc_auc_score(y, tot)), 3),
                                   "ci95": boot_ci(y, tot.astype(float), rng),
                                   "null_p95": round(float(np.percentile(null, 95)), 3),
                                   "honest_any": int((tot[y == 0] > 0).sum()),
                                   "attack_any": int((tot[y == 1] > 0).sum()),
                                   "args_only_auroc": round(float(roc_auc_score(y, tot_args)), 3)}
        P["keywords"] = kw
        out["pairs"][pname] = P
        print(pname, json.dumps({d["detector"]: (d["auroc"], d["null_p95"]) for d in dets}), flush=True)

    Path(a.out).write_text(json.dumps(out, indent=1))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
