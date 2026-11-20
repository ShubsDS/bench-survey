"""All pre-registered statistics (prereg.md) from results/runs_b*.csv. Seed 0. Writes results.json.

Run: ../lab-bench/data/.venv/bin/python -I scripts/analyze.py
"""
from __future__ import annotations

import json
import sys
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
AUD = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(AUD.parent / "lab-bench" / "scripts"))
from build import CUE, NONCUE  # noqa: E402
from common import wilson  # noqa: E402

GENE_ABSENT = ["PCR-gene-enzprimers-v1", "PCR-gene-gibshindprimers-v1", "PCR-gene-gibssmaprimers-v1"]
GENE_PRESENT = ["Prop-seq-gcpercent-v1", "ORF-seq-AAseq-v1", "PCR-seq-enzprimers-v1"]
PRIMER_PAIR = ["PCR-gene-enzprimers-v1", "PCR-seq-enzprimers-v1", "PCR-gene-gibshindprimers-v1",
               "PCR-gene-gibssmaprimers-v1", "PCR-len-primers-v1", "PCR-seq-primers-v1"]
HUMAN_SEQQA = 0.789  # mean of the paper's 15 subtask human accuracies (parent, results/published.json)
B = 2000


def r4(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 4)


def load() -> pd.DataFrame:
    fs = sorted((AUD / "results").glob("runs_b*.csv"))
    df = pd.concat([pd.read_csv(f).assign(batch=f.stem) for f in fs], ignore_index=True)
    df["correct"] = (df.bucket == "correct").astype(float)
    df["refuse"] = (df.bucket == "refuse").astype(float)
    # GC-percent: K is O by construction (prereg); expose its K rows as O too
    gk = df[(df.family == "Prop-seq-gcpercent-v1") & (df.arm == "K")].copy()
    gk["arm"] = "O"
    gk["batch"] = gk["batch"] + ":K_as_O"
    df = pd.concat([df, gk], ignore_index=True)
    return df.drop_duplicates(["id", "arm", "model"])


def boot_items(v, seed=0):
    rng = np.random.default_rng(seed)
    v = np.asarray(v, float)
    s = [v[rng.integers(0, len(v), len(v))].mean() for _ in range(B)]
    return [r4(np.percentile(s, 2.5)), r4(np.percentile(s, 97.5))]


def boot_clusters(v, g, seed=0):
    rng = np.random.default_rng(seed)
    v, g = np.asarray(v, float), np.asarray(g)
    u = np.unique(g)
    idx = {k: np.where(g == k)[0] for k in u}
    s = []
    for _ in range(B):
        pick = rng.choice(u, len(u))
        s.append(np.mean([v[idx[k]].mean() for k in pick]))  # equal weight per subtask
    return [r4(np.percentile(s, 2.5)), r4(np.percentile(s, 97.5))]


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(comb(n, i) for i in range(k + 1)) / 2 ** n * 2
    return min(1.0, p)


def holm(ps):
    order = np.argsort(ps)
    adj = [None] * len(ps)
    run = 0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = run
    return adj


def signflip(means):
    m = np.asarray(means, float)
    k = len(m)
    signs = np.array(np.meshgrid(*[[-1, 1]] * k)).reshape(k, -1).T
    null = np.abs((signs * m).mean(1))
    return r4(np.mean(null >= abs(m.mean()) - 1e-12))


def pairs(df, model, a="K", b="D", fams=CUE):
    x = df[(df.model == model) & df.family.isin(fams)]
    p = x[x.arm == a][["id", "family", "correct", "refuse"]].merge(
        x[x.arm == b][["id", "correct", "refuse"]], on="id", suffixes=("", "_b")).set_index("id")
    p["diff"] = p.correct - p.correct_b
    return p


def contrast(p, label):
    if len(p) == 0:
        return None
    out = {"label": label, "n_pairs": int(len(p)), "acc_a": r4(p.correct.mean()), "acc_b": r4(p.correct_b.mean()),
           "diff": r4(p["diff"].mean()), "ci_items": boot_items(p["diff"].values)}
    if p.family.nunique() > 1:
        out["ci_subtasks"] = boot_clusters(p["diff"].values, p.family.values)
        per = p.groupby("family")["diff"].mean()
        out["subtask_mean_diff_equal_weight"] = r4(per.mean())
        out["signflip_p_subtasks"] = signflip(per.values) if len(per) <= 8 else None
    out["refuse_a"] = r4(p.refuse.mean())
    out["refuse_b"] = r4(p.refuse_b.mean())
    out["refuse_diff_ci"] = boot_items((p.refuse - p.refuse_b).values)
    ans = p[(p.refuse == 0) & (p.refuse_b == 0)]
    out["diff_answered_both"] = r4(ans["diff"].mean()) if len(ans) else None
    out["n_answered_both"] = int(len(ans))
    return out


def decide(c, k_acc):
    if c is None:
        return "no data"
    lo, hi = c["ci_items"]
    if c["diff"] >= 0.10 and lo > 0 and c.get("centre_pick", 0) > c.get("other_pick", 1):
        return "yes: relies on the cue"
    if hi < 0.10 and k_acc >= 0.70:
        return "held at ceiling (R)" if c["acc_a"] >= 0.95 and c["acc_b"] >= 0.95 else "no (R)"
    return "still cannot tell"


def picks(df, model, fams=CUE):
    x = df[(df.model == model) & (df.arm == "D") & df.family.isin(fams)]
    cen, oth, n = 0.0, 0.0, 0
    for _, r in x.iterrows():
        c = json.loads(r.d_centre) if isinstance(r.d_centre, str) and r.d_centre else []
        k = r.n_sub
        n += 1
        if r.bucket not in ("correct", "wrong"):
            continue
        pk = int(float(r.picked))
        if pk in c:
            cen += 1.0 / len(c) if len(c) > 1 else 1.0
        elif pk != 0:
            oth += 1.0 / max(k - 1 - len(c), 1)
    return {"n": n, "centre_pick": r4(cen / n) if n else None, "other_pick_mean": r4(oth / n) if n else None}


def pcr_roles(arms, i):
    """Index -> role (key, S, G, Wx) for a PCR item; Wx is W in O, W'+S body in D, W'+K body in K."""
    v = arms[i]
    pl = 30 if "gibs" in v["family"] else 6
    body = lambda o: tuple(x.strip()[pl:] for x in o.split(","))  # noqa: E731
    w = [j for j in range(4) if v["D"][j] != v["O"][j]][0]
    s_ = [j for j in range(1, 4) if j != w and body(v["D"][j]) == body(v["D"][w])][0]
    g_ = [j for j in range(1, 4) if j not in (w, s_)][0]
    return {0: "key", s_: "S", g_: "G", w: "Wx"}


def role_picks(df, arms, model):
    """Post hoc descriptive: which option each PCR answer picked, by arm."""
    x = df[(df.model == model) & df.family.str.startswith("PCR") & df.arm.isin(["O", "K", "D"])]
    out = {}
    for (f, a), g in x.groupby(["family", "arm"]):
        c = {"key": 0, "S": 0, "G": 0, "Wx": 0, "refuse": 0, "other": 0}
        for _, r in g.iterrows():
            if r.bucket == "refuse":
                c["refuse"] += 1
            elif r.bucket in ("correct", "wrong"):
                c[pcr_roles(arms, r.id)[int(float(r.picked))]] += 1
            else:
                c["other"] += 1
        out[f"{f}|{a}"] = {"n": int(len(g)), **c}
    return out


def arm_table(df):
    rows = []
    for (m, a, f), g in df.groupby(["model", "arm", "family"]):
        rows.append({"model": m, "arm": a, "family": f, "n": int(len(g)), "acc": r4(g.correct.mean()),
                     "wilson": [r4(x) for x in wilson(g.correct.sum(), len(g))],
                     "refuse": int(g.refuse.sum()), "unparsed": int((g.bucket == "unparsed").sum()),
                     "error": int((g.bucket == "error").sum()), "chance": r4((1 / g.n_sub).mean())})
    return rows


def pooled_arm(df, model, arm, fams):
    g = df[(df.model == model) & (df.arm == arm) & df.family.isin(fams)]
    if not len(g):
        return None
    return {"n": int(len(g)), "acc": r4(g.correct.mean()),
            "wilson": [r4(x) for x in wilson(g.correct.sum(), len(g))],
            "ci_subtasks": boot_clusters(g.correct.values, g.family.values) if g.family.nunique() > 1 else None,
            "refuse_rate": r4(g.refuse.mean()), "unparsed": int((g.bucket == "unparsed").sum()),
            "error": int((g.bucket == "error").sum()), "chance": r4((1 / g.n_sub).mean())}


def stratum_placebo(df, model, arm, seed=0):
    g = df[(df.model == model) & (df.arm == arm)]
    per = g.groupby("family").correct.mean()
    if not all(f in per for f in CUE + NONCUE):
        return {"missing": [f for f in CUE + NONCUE if f not in per]}
    obs = per[CUE].mean() - per[NONCUE].mean()
    rng = np.random.default_rng(seed)
    others = [f for f in CUE + NONCUE if f not in PRIMER_PAIR]
    vals = []
    for _ in range(1000):
        s = list(rng.choice(PRIMER_PAIR, 4, replace=False)) + list(rng.choice(others, 2, replace=False))
        rest = [f for f in CUE + NONCUE if f not in s]
        vals.append(per[s].mean() - per[rest].mean())
    vals = np.array(vals)
    return {"obs_cue_minus_noncue": r4(obs), "placebo_95": [r4(np.percentile(vals, 2.5)), r4(np.percentile(vals, 97.5))],
            "percentile": r4(np.mean(vals < obs) * 100), "n_items": int(len(g)),
            "per_subtask": {f: r4(v) for f, v in per.items()}}


def cue_free(df, model, seed=0):
    g = df[df.model == model]
    need = {f: g[(g.family == f) & (g.arm == "O")] for f in NONCUE}
    if any(len(v) == 0 for v in need.values()):
        nc = None
    else:
        nc = need
    variants = {"as_benchmark": "O", "cue_for_K": "K", "cue_against_D": "D"}
    out = {}
    per_cue = {}
    for f in CUE:
        per_cue[f] = {a: r4(g[(g.family == f) & (g.arm == a)].correct.mean()) if len(g[(g.family == f) & (g.arm == a)]) else None
                      for a in ["O", "K", "D", "I"]}
    out["per_cue_subtask"] = per_cue
    # shift (needs no non-cue data): (1/15) * sum over cue subtasks of (K - D)
    p = pairs(df, model)
    if len(p):
        per = p.groupby("family")["diff"].mean()
        out["shift_K_minus_D_over15"] = r4(per.reindex(CUE).fillna(0).sum() / 15)
        rng = np.random.default_rng(seed)
        bs = []
        for _ in range(B):
            tot = 0
            for f in CUE:
                v = p[p.family == f]["diff"].values
                if len(v):
                    tot += v[rng.integers(0, len(v), len(v))].mean()
            bs.append(tot / 15)
        out["shift_ci"] = [r4(np.percentile(bs, 2.5)), r4(np.percentile(bs, 97.5))]
    if nc is None:
        out["score"] = "not computed: no O data on all nine non-cue subtasks"
        return out
    out["noncue_O"] = {f: {"n": int(len(v)), "acc": r4(v.correct.mean())} for f, v in nc.items()}
    rng = np.random.default_rng(seed)
    for name, arm in list(variants.items()) + [("honest_GC_I_else_D", "ID")]:
        def subtask_vals(f, arm=arm):
            if arm == "ID":
                a = "I" if f == "Prop-seq-gcpercent-v1" else "D"
            else:
                a = arm
            if f in NONCUE:
                a = "O"
            return g[(g.family == f) & (g.arm == a)].correct.values
        vals = {f: subtask_vals(f) for f in CUE + NONCUE}
        if any(len(v) == 0 for v in vals.values()):
            out[name] = {"missing": [f for f, v in vals.items() if len(v) == 0]}
            continue
        point = np.mean([v.mean() for v in vals.values()])
        bs = [np.mean([v[rng.integers(0, len(v), len(v))].mean() for v in vals.values()]) for _ in range(B)]
        out[name] = {"score": r4(point), "ci_items_within_subtask": [r4(np.percentile(bs, 2.5)), r4(np.percentile(bs, 97.5))],
                     "minus_human_0.789": r4(point - HUMAN_SEQQA)}
    return out


def main():
    df = load()
    bc = json.loads((AUD / "build_check.json").read_text())["items"]
    arms = json.loads((AUD / "data" / "arms.json").read_text())
    res = {"calls": {}, "arms": arm_table(df), "models": {}}
    raw = pd.concat([pd.read_csv(f) for f in sorted((AUD / "results").glob("runs_*.csv"))])
    res["calls"] = {m: {"n": int(len(g)), "cost_usd": r4(g.cost_usd.sum()), "mean_cost": r4(g.cost_usd.mean()),
                        "mean_thinking_tokens": r4(g.thinking_tokens.mean())} for m, g in raw.groupby("model")}
    res["parse_routes"] = raw.parse.value_counts().to_dict()
    for m in sorted(df.model.unique()):
        R = {}
        kacc = pooled_arm(df, m, "K", CUE)
        for name, fams in [("all_cue", CUE), ("gene_absent", GENE_ABSENT), ("gene_present", GENE_PRESENT)]:
            c = contrast(pairs(df, m, "K", "D", fams), f"K - D, {name}")
            if c:
                pk = picks(df, m, fams)
                c["centre_pick"], c["other_pick"] = pk["centre_pick"], pk["other_pick_mean"]
                c["decision"] = decide(c, c["acc_a"])
            R[f"K_minus_D_{name}"] = c
        # per subtask
        per = {}
        ps = []
        for f in CUE:
            p = pairs(df, m, "K", "D", [f])
            if not len(p):
                continue
            b_ = int(((p.correct == 1) & (p.correct_b == 0)).sum())
            c_ = int(((p.correct == 0) & (p.correct_b == 1)).sum())
            pv = mcnemar(b_, c_)
            ps.append(pv)
            per[f] = {"n": int(len(p)), "K": r4(p.correct.mean()), "D": r4(p.correct_b.mean()),
                      "diff": r4(p["diff"].mean()), "ci_items": boot_items(p["diff"].values),
                      "K_only": b_, "D_only": c_, "mcnemar_p": r4(pv), **picks(df, m, [f])}
        for f, a in zip(per, holm(ps)):
            per[f]["holm_p"] = r4(a)
        R["per_subtask"] = per
        # robustness: drop each subtask
        R["drop_one"] = {f: contrast(pairs(df, m, "K", "D", [x for x in CUE if x != f]), f"drop {f}")["diff"]
                         for f in per}
        # robustness: D centre agreed by both rules or not
        p = pairs(df, m, "K", "D", CUE)
        agree = p.index.map(lambda i: bc[i]["centres"]["D"]["rule1"] == bc[i]["centres"]["D"]["rule2"]
                            if "rule2" in bc[i]["centres"]["D"] and not bc[i]["family"].startswith("Prop") else None)
        p = p.assign(agree=list(agree))
        R["centre_rules_agree"] = {str(k): {"n": int(len(g)), "diff": r4(g["diff"].mean())}
                                   for k, g in p.groupby(p.agree.astype(str))}
        R["O_minus_K"] = contrast(pairs(df, m, "O", "K", [f for f in CUE if not f.startswith("Prop")]), "O - K (rebuild check)")
        R["O_minus_D"] = contrast(pairs(df, m, "O", "D", CUE), "O - D")
        R["I_minus_D_gc"] = contrast(pairs(df, m, "I", "D", ["Prop-seq-gcpercent-v1"]), "I - D, GC")
        R["K_minus_I_gc"] = contrast(pairs(df, m, "K", "I", ["Prop-seq-gcpercent-v1"]), "K(=O) - I, GC")
        R["N_cue"] = pooled_arm(df, m, "N", CUE)
        R["N_noncue"] = pooled_arm(df, m, "N", NONCUE)
        R["O_noncue"] = pooled_arm(df, m, "O", NONCUE)
        for a in ["K", "D", "O", "I"]:
            R[f"{a}_cue"] = pooled_arm(df, m, a, CUE)
        R["stratum_O"] = stratum_placebo(df, m, "O")
        R["stratum_N"] = stratum_placebo(df, m, "N")
        R["cue_free"] = cue_free(df, m)
        R["pcr_role_picks_posthoc"] = role_picks(df, arms, m)
        res["models"][m] = R
    (AUD / "results.json").write_text(json.dumps(res, indent=1))
    for m, R in res["models"].items():
        print("=====", m)
        for k in ["K_minus_D_all_cue", "K_minus_D_gene_absent", "K_minus_D_gene_present"]:
            c = R[k]
            if c:
                print(k, {x: c[x] for x in ["n_pairs", "acc_a", "acc_b", "diff", "ci_items", "ci_subtasks", "centre_pick", "other_pick", "refuse_a", "refuse_b", "decision"] if x in c})
        for f, v in R["per_subtask"].items():
            print("  ", f, v)
        for k in ["N_cue", "N_noncue", "O_noncue", "O_minus_K", "O_minus_D", "I_minus_D_gc", "K_minus_I_gc", "stratum_O", "stratum_N"]:
            print(k, R[k] if not isinstance(R[k], dict) else {x: y for x, y in R[k].items() if x != "per_subtask"})
        print("cue_free", json.dumps(R["cue_free"]))


if __name__ == "__main__":
    main()
