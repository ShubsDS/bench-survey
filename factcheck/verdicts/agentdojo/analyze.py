"""Decompose 'secure' runs per model, with two-way (user task x injection task, within suite)
crossed bootstrap. Usage: python -I analyze.py <runs.csv> <scriptdir> <out_json>"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, sys.argv[2])
from common_fc import TABLE20, EXTRA, REPO_FOUR, load, v112  # noqa: E402

B = 2000
SEED = 12345
df = load(sys.argv[1])
OUT = sys.argv[3]


def ability_table(df):
    ab = df[df.kind == "ability"][["pipeline", "suite", "user_task", "utility"]]
    ab = ab.rename(columns={"user_task": "injection_task", "utility": "able"})
    return ab


def build(df, pipelines, attack="important_instructions", version="v1.1.2", saw_col="saw_full"):
    a = df[(df.kind == "attack") & (df.attack == attack) & df.pipeline.isin(pipelines)]
    if version == "v1.1.2":
        a = v112(a)
    a = a.merge(ability_table(df), on=["pipeline", "suite", "injection_task"], how="left")
    a["untraced"] = a.n_messages == 0
    a["saw"] = a[saw_col] & ~a.untraced
    a["secure"] = ~a.security.astype(bool)
    a["errored"] = a.error != ""
    a["able"] = a.able.fillna(False).astype(bool)
    a["c_untraced"] = a.secure & a.untraced
    a["c_never"] = a.secure & ~a.untraced & ~a.saw
    a["c_couldnot"] = a.secure & a.saw & ~a.able
    a["c_sawcould"] = a.secure & a.saw & a.able
    a["unable_any"] = a.secure & ~a.able  # alternative precedence: inability first
    a["never_and_unable"] = a.secure & ~a.untraced & ~a.saw & ~a.able
    a["sa"] = a.saw & a.able  # saw and could (all runs, for adjusted ASR)
    a["sa_succ"] = a.sa & a.security.astype(bool)
    a["sa_succ_noerr"] = a.sa & a.security.astype(bool) & ~a.errored
    a["saw_succ"] = a.saw & a.security.astype(bool)
    a["saw_succ_noerr"] = a.saw & a.security.astype(bool) & ~a.errored
    a["succ_noerr"] = a.security.astype(bool) & ~a.errored
    a["one"] = True
    return a


def matrices(a, cols):
    """per suite: dict col -> array [pipeline, U, I]"""
    out = {}
    pipes = sorted(a.pipeline.unique())
    for s, g in a.groupby("suite"):
        us = sorted(g.user_task.unique())
        its = sorted(g.injection_task.unique())
        ui = {u: k for k, u in enumerate(us)}
        ii = {u: k for k, u in enumerate(its)}
        pi = {p: k for k, p in enumerate(pipes)}
        arrs = {c: np.zeros((len(pipes), len(us), len(its))) for c in cols}
        P = g.pipeline.map(pi).values
        U = g.user_task.map(ui).values
        I = g.injection_task.map(ii).values
        for c in cols:
            np.add.at(arrs[c], (P, U, I), g[c].astype(float).values)
        out[s] = arrs
    return pipes, out


def boot_sums(pipes, mats, cols, B, seed):
    """returns dict col -> array [B+1, pipeline] of weighted sums; index 0 = point estimate"""
    rng = np.random.default_rng(seed)
    res = {c: np.zeros((B + 1, len(pipes))) for c in cols}
    for s, arrs in mats.items():
        nU, nI = next(iter(arrs.values())).shape[1:]
        WU = np.vstack([np.ones(nU), rng.multinomial(nU, np.ones(nU) / nU, size=B)])
        WI = np.vstack([np.ones(nI), rng.multinomial(nI, np.ones(nI) / nI, size=B)])
        for c in cols:
            # sum_b,p = WU[b] @ X[p] @ WI[b]
            res[c] += np.einsum("bu,pui,bi->bp", WU, arrs[c], WI)
    return res


def ratio(res, num, den):
    with np.errstate(invalid="ignore", divide="ignore"):
        return res[num] / res[den]


def ci(x):
    x = x[1:]
    x = x[~np.isnan(x)]
    return [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))] if len(x) else [None, None]


def rank_desc(v):
    return pd.Series(v).rank(ascending=False, method="average").values


COLS = ["one", "secure", "c_untraced", "c_never", "c_couldnot", "c_sawcould", "unable_any",
        "never_and_unable", "sa", "sa_succ", "sa_succ_noerr", "saw", "saw_succ", "saw_succ_noerr",
        "security", "succ_noerr", "untraced", "errored", "follow_saw_secure", "couldnot_follow"]


def summarise(a, B=B, seed=SEED, with_ranks=True):
    a = a.copy()
    a["security"] = a.security.astype(bool)
    a["follow_saw_secure"] = a.secure & a.saw & a.follow.fillna(False).astype(bool)
    a["couldnot_follow"] = a.c_couldnot & a.follow.fillna(False).astype(bool)
    pipes, mats = matrices(a, COLS)
    res = boot_sums(pipes, mats, COLS, B, seed)
    shares = {
        "share_never_saw": ratio(res, "c_never", "secure"),
        "share_untraced": ratio(res, "c_untraced", "secure"),
        "share_could_not": ratio(res, "c_couldnot", "secure"),
        "share_never_or_could_not": (res["c_never"] + res["c_couldnot"]) / res["secure"],
        "share_never_or_could_not_or_untraced": (res["c_never"] + res["c_couldnot"] + res["c_untraced"]) / res["secure"],
        "share_saw_and_could": ratio(res, "c_sawcould", "secure"),
        "share_unable_any": ratio(res, "unable_any", "secure"),
        "published_asr": ratio(res, "security", "one"),
        "asr_errors_not_counted": ratio(res, "succ_noerr", "one"),
        "asr_given_saw": ratio(res, "saw_succ", "saw"),
        "asr_given_saw_errors_not_counted": ratio(res, "saw_succ_noerr", "saw"),
        "adjusted_asr_given_saw_and_could": ratio(res, "sa_succ", "sa"),
        "adjusted_asr_given_saw_and_could_errors_not_counted": ratio(res, "sa_succ_noerr", "sa"),
        "exposure_rate_traced": res["saw"] / (res["one"] - res["untraced"]),
    }
    out = {}
    for k, p in enumerate(pipes):
        row = {c: int(res[c][0, k]) for c in ["one", "secure", "c_untraced", "c_never", "c_couldnot",
                                              "c_sawcould", "unable_any", "never_and_unable", "sa",
                                              "sa_succ", "saw", "saw_succ", "errored",
                                              "follow_saw_secure", "couldnot_follow"]}
        for name, arr in shares.items():
            row[name] = float(arr[0, k])
            row[name + "_ci"] = ci(arr[:, k])
        out[p] = row
    if with_ranks:
        for name in ["published_asr", "asr_errors_not_counted", "asr_given_saw", "asr_given_saw_errors_not_counted",
                     "adjusted_asr_given_saw_and_could", "adjusted_asr_given_saw_and_could_errors_not_counted"]:
            arr = shares[name]
            R = np.array([rank_desc(arr[b]) for b in range(arr.shape[0])])
            for k, p in enumerate(pipes):
                out[p]["rank_" + name] = float(R[0, k])
                out[p]["rank_" + name + "_ci"] = ci(R[:, k])
        # rank change vs published for each conditioned statistic
        Rp = np.array([rank_desc(shares["published_asr"][b]) for b in range(B + 1)])
        for name in ["asr_given_saw_errors_not_counted", "adjusted_asr_given_saw_and_could_errors_not_counted",
                     "asr_given_saw", "adjusted_asr_given_saw_and_could"]:
            Rc = np.array([rank_desc(shares[name][b]) for b in range(B + 1)])
            d = Rp - Rc
            for k, p in enumerate(pipes):
                out[p]["rank_gain_" + name] = float(d[0, k])
                out[p]["rank_gain_" + name + "_ci"] = ci(d[:, k])
        # distribution stats of the share across models, with bootstrap CI for the median/min/max
        for name in ["share_never_or_could_not", "share_never_or_could_not_or_untraced", "share_never_saw", "share_could_not"]:
            arr = shares[name]
            out.setdefault("_distribution", {})[name] = {
                "min": float(np.nanmin(arr[0])), "median": float(np.nanmedian(arr[0])), "max": float(np.nanmax(arr[0])),
                "median_ci": ci(np.nanmedian(arr, axis=1)),
                "n_models_gt_half": int((arr[0] > 0.5).sum()),
                "n_models_gt_half_boot_ci": ci((arr > 0.5).sum(axis=1).astype(float)),
            }
    return out


if __name__ == "__main__":
    results = {}
    a = build(df, TABLE20)
    results["main_v112_important_instructions_table20"] = summarise(a)
    # Excluding Opus untraced runs from the denominator entirely
    a2 = a[~a.untraced]
    results["main_traced_only"] = summarise(a2, with_ranks=False)
    # Extra pipelines (Llama 3.3 / Meta-SecAlign) at v1.1.2 subset and at full 949
    results["extra_v112"] = summarise(build(df, EXTRA), with_ranks=False)
    results["full949_pipelines_allversions"] = summarise(
        build(df, ["claude-3-7-sonnet-20250219", "gemini-2.0-flash-001"] + EXTRA, version="all"), with_ranks=False)
    # GPT-4o other attacks
    att = {}
    for at in sorted(df[(df.kind == "attack") & (df.pipeline == "gpt-4o-2024-05-13")].attack.unique()):
        b = build(df, ["gpt-4o-2024-05-13"], attack=at)
        if b.suite.nunique() < 4 or len(b) < 600:
            att[at] = {"n": int(len(b)), "note": "not full 629 (DoS attacks use one injection task)"}
            if len(b) == 0:
                continue
        att[at] = summarise(b, with_ranks=False)["gpt-4o-2024-05-13"]
    results["gpt4o_by_attack"] = att
    # per-suite breakdown for the 20 models (point estimates)
    ps = {}
    for s, g in a.groupby("suite"):
        gg = g.groupby("pipeline")
        ps[s] = {p: {"secure": int(x.secure.sum()),
                     "share_never_or_could_not": float((x.c_never.sum() + x.c_couldnot.sum()) / max(x.secure.sum(), 1)),
                     "share_never_saw": float(x.c_never.sum() / max(x.secure.sum(), 1))} for p, x in gg}
    results["per_suite"] = ps
    a.to_csv(OUT.replace(".json", "_cases.csv"), index=False)
    with open(OUT, "w") as f:
        json.dump(results, f, indent=1)
    m = results["main_v112_important_instructions_table20"]
    cols = ["published_asr", "secure", "c_untraced", "c_never", "c_couldnot", "c_sawcould", "share_never_saw",
            "share_could_not", "share_never_or_could_not", "share_never_or_could_not_or_untraced",
            "adjusted_asr_given_saw_and_could", "rank_published_asr", "rank_asr_given_saw_errors_not_counted",
            "rank_adjusted_asr_given_saw_and_could_errors_not_counted"]
    t = pd.DataFrame({p: {c: m[p][c] for c in cols} for p in TABLE20}).T.sort_values("published_asr")
    pd.set_option("display.width", 250)
    print(t.round(3).to_string())
    print(json.dumps(m["_distribution"], indent=1))
