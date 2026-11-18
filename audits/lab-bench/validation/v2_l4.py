"""Validator re-analysis of claim 2 (L4 distractor edits), from the raw Haiku CSVs and the
edited options in data/edits.json. Written without reading scripts/analyze.py.

1. Same items? forced, edit and pedit rows are matched by id.
2. Accuracy per family and pooled; drop forced-edit; pick rates; with and without the two
   Gibson subtasks. Intervals: item bootstrap (2,000) and template (subtask) bootstrap.
3. Edit-vs-control on the 50 Gibson items: edit vs pedit, paired.
4. Surface properties of the key in original / edit / placebo options: is the key the unique
   longest or shortest option (total characters), its length rank, and whether the key is the
   unique outlier by summed Levenshtein distance (the validator's own centre rule).
Item text is written only to data/ (git-ignored) for the hand read.

Run: data/.venv/bin/python -I validation/v2_l4.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

A = Path(__file__).resolve().parent.parent
exec((A / "validation/v1_rule.py").read_text().split("if __name__")[0].replace("Path(__file__)", "Path(%r)" % str(A / "validation/v1_rule.py")))

b1 = pd.read_csv(A / "results/haiku_b1_l4.csv")
b7 = pd.read_csv(A / "results/haiku_b7_placebo_edit.csv")
E = json.loads((A / "data/edits.json").read_text())
seq = pq.read_table(A / "data/hf/SeqQA/train-00000-of-00001.parquet").to_pandas().set_index("id")

d = pd.concat([b1, b7])
d["correct"] = (d.bucket == "correct").astype(float)
d["fam"] = d.family.str.replace("SeqQA:", "").str.replace("-v1", "")
w = d.pivot_table(index=["id", "fam"], columns="cond", values="correct").reset_index()
w = w[w.id.isin(E)]
pk = d[d.cond == "edit"].set_index("id").picked_role
w["edit_pick_central"] = w.id.map(lambda i: float(pk.get(i) == "d0"))  # options[1] is central
w["edit_pick_other_d"] = w.id.map(lambda i: float(pk.get(i) in ("d1", "d2", "d3")))
GIB = ["PCR-gene-gibshindprimers", "PCR-gene-gibssmaprimers"]
rng = np.random.default_rng(0)


def ci(x, B=2000):
    x = np.asarray(x, float)
    bs = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(B)]
    return [round(float(np.quantile(bs, q)), 3) for q in (0.025, 0.975)]


def tmpl_ci(df, col, B=2000):
    fams = df.fam.unique()
    g = {f: df[df.fam == f][col].values for f in fams}
    bs = []
    for _ in range(B):
        pick = rng.choice(fams, len(fams))
        bs.append(np.concatenate([g[f] for f in pick]).mean())
    return [round(float(np.quantile(bs, q)), 3) for q in (0.025, 0.975)]


out = {"n_items_edit": int(w.edit.notna().sum()),
       "forced_and_edit_on_same_items": bool((w.forced.notna() & w.edit.notna()).sum() == w.edit.notna().sum())}
w["drop"] = w.forced - w.edit
fam = {}
for f, g in w.groupby("fam"):
    fam[f] = {"n": len(g), "forced": round(g.forced.mean(), 3), "edit": round(g.edit.mean(), 3),
              "drop": round(g["drop"].mean(), 3), "drop_ci_items": ci(g["drop"]),
              "pick_central": round(g.edit_pick_central.mean(), 3)}
    if g.pedit.notna().any():
        fam[f]["pedit"] = round(g.pedit.mean(), 3)
out["per_family"] = fam
for name, sub in [("pooled", w), ("without_gibson", w[~w.fam.isin(GIB)]), ("gibson_only", w[w.fam.isin(GIB)])]:
    out[name] = {"n": len(sub), "forced": round(sub.forced.mean(), 3), "edit": round(sub.edit.mean(), 3),
                 "drop": round(sub["drop"].mean(), 3), "drop_ci_items": ci(sub["drop"]),
                 "drop_ci_templates": tmpl_ci(sub, "drop"), "n_templates": int(sub.fam.nunique()),
                 "pick_central": round(sub.edit_pick_central.mean(), 3),
                 "pick_each_other_distractor": round(sub.edit_pick_other_d.mean() / 2, 3)}
g = w[w.fam.isin(GIB)].copy()
out["gibson_three_arms_same_items"] = bool(g[["forced", "edit", "pedit"]].notna().all(axis=None))
g["e_minus_p"] = g.pedit - g.edit
out["gibson_arms"] = {"n": len(g), "forced": round(g.forced.mean(), 3), "pedit": round(g.pedit.mean(), 3),
                      "edit": round(g.edit.mean(), 3),
                      "pedit_minus_edit": round(g.e_minus_p.mean(), 3), "pedit_minus_edit_ci": ci(g.e_minus_p),
                      "forced_minus_pedit": round((g.forced - g.pedit).mean(), 3),
                      "forced_minus_pedit_ci": ci(g.forced - g.pedit)}
pp = d[d.cond == "pedit"].picked_role.value_counts().to_dict()
out["pedit_picked_roles"] = {k: int(v) for k, v in pp.items()}
ep = d[(d.cond == "edit") & d.fam.isin(GIB)].picked_role.value_counts().to_dict()
out["gibson_edit_picked_roles"] = {k: int(v) for k, v in ep.items()}


def surf(opts):
    L = np.array([len(o) for o in opts])
    _, sc = scores(opts)
    return {"key_longest": float(L[0] == L.max() and (L == L.max()).sum() == 1),
            "key_shortest": float(L[0] == L.min() and (L == L.min()).sum() == 1),
            "key_len_rank_desc": int((L > L[0]).sum()) + 1,
            "key_unique_outlier": float(sc[0] == sc.max() and (sc == sc.max()).sum() == 1),
            "key_centre": float(sc[0] == sc.min() and (sc == sc.min()).sum() == 1)}


rows = []
for i, e in E.items():
    r = seq.loc[i]
    st = e["family"].replace("-v1", "")
    for arm, opts in [("orig", [r.ideal] + list(r.distractors)), ("edit", e["options"]),
                      ("placebo", e.get("placebo_options"))]:
        if opts is None:
            continue
        rows.append({"id": i, "fam": st, "arm": arm, **surf(opts)})
S = pd.DataFrame(rows)
out["key_surface"] = {f"{f}|{a}": {k: round(v, 3) for k, v in g2.drop(columns=["id", "fam", "arm"]).mean().items()}
                      for (f, a), g2 in S.groupby(["fam", "arm"])}

# compact structural dump for the hand read (git-ignored)
with open(A / "data/val_handread_edits.txt", "w") as fh:
    for i, e in E.items():
        if not e["family"].startswith("PCR"):
            continue
        r = seq.loc[i]
        fh.write(f"### {i} {e['family']} forced={w.set_index('id').forced.get(i)} edit={w.set_index('id').edit.get(i)} pedit={w.set_index('id').pedit.get(i)} pick={pk.get(i)}\nQ: {r.question}\nORIG\n")
        for j, o in enumerate([r.ideal] + list(r.distractors)):
            fh.write(f"  {'K' if j == 0 else 'd'} {o}\n")
        fh.write("EDIT\n")
        for j, o in enumerate(e["options"]):
            fh.write(f"  {['K', 'S*', 'WS', 'S2'][j]} {o}\n")
        if e.get("placebo_options"):
            fh.write("PLACEBO\n")
            for j, o in enumerate(e["placebo_options"]):
                fh.write(f"  {['K', 'S', 'W', 'K2'][j]} {o}\n")
json.dump(out, open(A / "validation/v2_l4.json", "w"), indent=1)
print(json.dumps(out, indent=1))
