"""Analyses B-E of prereg.md on the Haiku runs (results/haiku_b*.csv) and the published numbers.
Writes results/haiku_analysis.json and results/human_baseline.json. Seed 0, 2,000 bootstrap
replicates; clusters from common.clusters().
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import AUDIT, RESULTS, cluster_boot, clusters, load_items, wilson  # noqa: E402

B = 2000


def load_runs() -> pd.DataFrame:
    fs = sorted(glob.glob(str(RESULTS / "haiku_b*.csv")))
    df = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
    bad = df.bucket.isin(["error", "budget", "dry"])
    if bad.any():
        print("WARNING: non-answers", df[bad].groupby(["cond", "bucket"]).size().to_dict())
    df = df.drop_duplicates(["id", "cond"], keep="last")
    df["correct"] = (df.bucket == "correct").astype(float)
    df["refuse"] = (df.bucket == "refuse").astype(float)
    df["unparsed"] = (df.bucket == "unparsed").astype(float)
    df["chance"] = 1.0 / df.n_sub
    return df


def rate(x: pd.Series, cl: pd.Series) -> dict:
    k, n = float(x.sum()), int(len(x))
    lo, hi = wilson(k, n)
    clo, chi = cluster_boot(x.values, cl.values, B) if n else (np.nan, np.nan)
    return {"n": n, "rate": round(k / n, 4) if n else None, "wilson": [round(lo, 4), round(hi, 4)],
            "cluster_ci": [round(clo, 4), round(chi, 4)], "clusters": int(cl.nunique())}


def summarise(g: pd.DataFrame) -> dict:
    out = {"accuracy": rate(g.correct, g.cluster), "chance": round(float(g.chance.mean()), 4),
           "refusal_rate": round(float(g.refuse.mean()), 4), "unparsed": int(g.unparsed.sum())}
    att = g[g.bucket != "refuse"]
    out["coverage"] = round(len(att) / len(g), 4) if len(g) else None
    out["precision"] = round(float(att.correct.mean()), 4) if len(att) else None
    return out


def paired_diff(a: pd.Series, b: pd.Series, seed: int = 0) -> dict:
    """mean(a - b) over aligned items with an item bootstrap."""
    d = (a - b).values
    rng = np.random.default_rng(seed)
    bs = [rng.choice(d, len(d)).mean() for _ in range(B)]
    return {"n": int(len(d)), "diff": round(float(d.mean()), 4),
            "ci": [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)]}


def main() -> None:
    items = load_items(check=False)
    items["cluster"] = clusters(items)
    cl = dict(zip(items.id, items.cluster))
    st = dict(zip(items.id, items.subtask))
    df = load_runs()
    df["cluster"] = df.id.map(cl)
    df["subtask"] = df.id.map(st)
    res = {"calls": {c: int(n) for c, n in df.groupby("cond").size().items()},
           "bucket_counts": {f"{c}|{s}": g.bucket.value_counts().to_dict()
                             for (c, s), g in df.groupby(["cond", "subset"])}}

    # ---- B: L4 edits
    edits = json.loads((AUDIT / "data" / "edits.json").read_text())
    ids = sorted(edits)
    f = df[(df.cond == "forced") & df.id.isin(ids)].set_index("id")
    e = df[(df.cond == "edit") & df.id.isin(ids)].set_index("id")
    common = sorted(set(f.index) & set(e.index))
    B_out = {"pooled": paired_diff(f.loc[common, "correct"], e.loc[common, "correct"]),
             "forced_acc": round(float(f.loc[common, "correct"].mean()), 4),
             "edit_acc": round(float(e.loc[common, "correct"].mean()), 4)}
    ee = e.loc[common]
    central = (ee.picked_role == "d0").mean()
    # mean pick rate per non-central distractor: picks of d1.. over the number of such slots
    others = ee.picked_role.isin(["d1", "d2", "d3", "d4", "d5"]).sum() / (ee.n_sub - 2).sum()
    B_out["edit_pick_central"] = round(float(central), 4)
    B_out["edit_pick_other_distractor_mean"] = round(float(others), 4)
    fam = {}
    for fm in sorted({edits[i]["family"] for i in common}):
        ii = [i for i in common if edits[i]["family"] == fm]
        d = paired_diff(f.loc[ii, "correct"], e.loc[ii, "correct"])
        rng = np.random.default_rng(1)
        dd = (f.loc[ii, "correct"] - e.loc[ii, "correct"]).values
        bs = [rng.choice(dd, len(dd)).mean() for _ in range(B)]
        d["ci_bonferroni6"] = [round(float(np.percentile(bs, 100 * 0.025 / 6)), 4),
                               round(float(np.percentile(bs, 100 - 100 * 0.025 / 6)), 4)]
        d["forced_acc"] = round(float(f.loc[ii, "correct"].mean()), 4)
        d["edit_acc"] = round(float(e.loc[ii, "correct"].mean()), 4)
        d["edit_pick_central"] = round(float((e.loc[ii, "picked_role"] == "d0").mean()), 4)
        fam[fm] = d
    B_out["per_family"] = fam
    # typicality: forced accuracy of edited items vs non-edited items of the same families
    fams = {edits[i]["family"] for i in ids}
    nonedit = df[(df.cond == "forced") & df.subtask.isin([x.replace("-v1", "") + "-v1" for x in fams]) & ~df.id.isin(ids)]
    B_out["forced_nonedited_same_families"] = {"n": int(len(nonedit)),
                                               "acc": round(float(nonedit.correct.mean()), 4) if len(nonedit) else None}
    dl = B_out["pooled"]
    B_out["verdict"] = ("uses shortcut" if dl["diff"] >= 0.10 and dl["ci"][0] > 0 and central > others
                        else "does not" if dl["ci"][0] <= 0 <= dl["ci"][1] and dl["ci"][1] < 0.10 else "inconclusive")
    res["B_edit"] = B_out

    # ---- C: blind and options-only
    C = {}
    for cond in ("blind", "blindf", "opts", "last"):
        for s, g in df[df.cond == cond].groupby("subset"):
            C[f"{cond}|{s}"] = summarise(g)
    res["C_blind_opts"] = C

    # ---- D: abstention, std vs forced on the same items (and blind vs blindf, blind vs last)
    D = {}
    for a, b, label in (("std", "forced", "std_vs_forced"), ("blind", "blindf", "blind_vs_blindf")):
        for s in sorted(df.subset.unique()):
            A = df[(df.cond == a) & (df.subset == s)].set_index("id")
            Bf = df[(df.cond == b) & (df.subset == s)].set_index("id")
            ii = sorted(set(A.index) & set(Bf.index))
            if not ii:
                continue
            A, Bf = A.loc[ii], Bf.loc[ii]
            entry = {"std": summarise(A.reset_index()), "forced": summarise(Bf.reset_index()),
                     "acc_forced_minus_std": paired_diff(Bf.correct, A.correct)}
            ref = A.refuse == 1
            entry["n_refusals"] = int(ref.sum())
            entry["refused_items_correct_when_forced"] = round(float(Bf.correct[ref].mean()), 4) if ref.any() else None
            entry["refused_items_chance"] = round(float(Bf.chance[ref].mean()), 4) if ref.any() else None
            entry["precision_std_minus_acc_forced"] = round(
                (entry["std"]["precision"] or 0) - entry["forced"]["accuracy"]["rate"], 4)
            if s == "SeqQA":
                entry["by_subtask"] = {t: {"std_acc": round(float(A.correct[A.subtask == t].mean()), 3),
                                           "forced_acc": round(float(Bf.correct[Bf.subtask == t].mean()), 3),
                                           "std_ref": round(float(A.refuse[A.subtask == t].mean()), 3)}
                                       for t in sorted(A.subtask.unique())}
            D[f"{label}|{s}"] = entry
    A = df[(df.cond == "blind") & (df.subset == "FigQA")].set_index("id")
    L = df[(df.cond == "last") & (df.subset == "FigQA")].set_index("id")
    ii = sorted(set(A.index) & set(L.index))
    if ii:
        D["refusal_position|FigQA"] = {"refusal_random_pos": round(float(A.loc[ii].refuse.mean()), 4),
                                       "refusal_last": round(float(L.loc[ii].refuse.mean()), 4),
                                       "last_minus_random": paired_diff(L.loc[ii].refuse, A.loc[ii].refuse),
                                       "acc_random_pos": round(float(A.loc[ii].correct.mean()), 4),
                                       "acc_last": round(float(L.loc[ii].correct.mean()), 4)}
    res["D_abstention"] = D

    # ---- design effects from Haiku per-item outcomes (for analysis E)
    deff = {}
    for (cond, s), g in df.groupby(["cond", "subset"]):
        if g.cluster.nunique() < len(g):
            p = g.correct.mean()
            var_iid = p * (1 - p) / len(g)
            lo, hi = cluster_boot(g.correct.values, g.cluster.values, B)
            var_cl = ((hi - lo) / (2 * 1.96)) ** 2
            deff[f"{cond}|{s}"] = {"n": int(len(g)), "clusters": int(g.cluster.nunique()),
                                   "deff": round(var_cl / var_iid, 3) if var_iid > 0 else None}
    res["design_effects"] = deff
    (RESULTS / "haiku_analysis.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({k: res[k] for k in ("calls", "B_edit")}, indent=1, default=float))


if __name__ == "__main__":
    main()
