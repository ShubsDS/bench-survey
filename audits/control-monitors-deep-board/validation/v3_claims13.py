"""Claims 1 and 3: counts, ranges, bin sensitivity, overlap diagnostics, trajectory-subset checks."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from vlib import arrays, bin_weights, load, quantile_edges, wauc  # noqa: E402

H = Path(__file__).parent
core = json.loads((H / "v1_core.json").read_text())
nulls = {r["i"]: r for r in json.loads((H / "v2_nulls.json").read_text())}
d = load()
res = {}


def excl(c):
    return not (c[0] <= 0.5 <= c[1])


groups = {}
for r in core:
    if r["n_att"] < 10:
        continue
    groups.setdefault((r["dataset"], r["kind"]), []).append(r)
for (ds, k), rs in sorted(groups.items()):
    ch = [r["q5"]["chance"] for r in rs]
    g = dict(n=len(rs), chance_min=min(ch), chance_max=max(ch),
             n_ci_excl_05=sum(excl(r["q5"]["chance_ci"]) for r in rs),
             q10=[min(r["q10"]["chance"] for r in rs), max(r["q10"]["chance"] for r in rs)],
             q20=[min(r["q20"]["chance"] for r in rs), max(r["q20"]["chance"] for r in rs)],
             exact=[min(r["exact"]["chance"] for r in rs), max(r["exact"]["chance"] for r in rs)],
             max_abs_matched_q5_vs_exact=max(abs(r["q5"]["matched"] - r["exact"]["matched"]) for r in rs),
             max_abs_matched_q5_vs_q20=max(abs(r["q5"]["matched"] - r["q20"]["matched"]) for r in rs),
             ess_q5=[min(r["q5"]["ess"] for r in rs), max(r["q5"]["ess"] for r in rs)],
             ess_exact=[min(r["exact"]["ess"] for r in rs), max(r["exact"]["ess"] for r in rs)],
             maxw_share_q5=max(r["q5"]["maxw_share"] for r in rs),
             maxw_share_exact=max(r["exact"]["maxw_share"] for r in rs),
             dropped_exact=max(r["exact"]["dropped"] for r in rs),
             n_hon=rs[0]["n_hon"], n_att=[min(r["n_att"] for r in rs), max(r["n_att"] for r in rs)])
    nl = [nulls[r["i"]] for r in rs if r["i"] in nulls]
    if k == "action":
        g["resize_null"] = [min(x["resize_null"] for x in nl), max(x["resize_null"] for x in nl)]
        g["cut_only_null"] = [min(x["cut_only_null"] for x in nl), max(x["cut_only_null"] for x in nl)]
    sp = [x["spearman_honest_score_len"] for x in nl if not np.isnan(x["spearman_honest_score_len"])]
    g["spearman_honest"] = [min(sp), max(sp)] if sp else None
    g["n_spearman_ci_above0"] = sum(1 for x in nl if x["spearman_ci"][0] > 0)
    res[f"{ds}|{k}"] = g
    print(ds, k, json.dumps({kk: (np.round(v, 3).tolist() if isinstance(v, (list, float)) else v) for kk, v in g.items()}))

# Claim 3: trajectory rows on LinuxArena. Does the scored attack subset matter?
print("\nClaim 3 detail")
c3 = []
rows = d["rows"]
for i, r in enumerate(rows):
    if r["monitor_kind"] != "trajectory" or not r["dataset"].startswith("linuxarena"):
        continue
    A = arrays(r)
    sa, la, _ = A["attack"]
    sh, lh, _ = A["honest"]
    if len(sa) < 10:
        continue
    # all attacks of the same dataset (lengths from the matching action row)
    act = [x for x in rows if x["dataset"] == r["dataset"] and x["monitor_kind"] == "action"
           and x["monitor_variant"] == r["monitor_variant"]]
    la_all = np.array([s["n_actions"] for s in act[0]["score_samples"]["attack"]], float) if act else None
    w, _ = bin_weights(la, lh, quantile_edges(la, 5))
    ch_sub = wauc(sh, sh, w, None)
    if la_all is not None:
        w2, _ = bin_weights(la_all, lh, quantile_edges(la_all, 5))
        ch_all = wauc(sh, sh, w2, None)
    else:
        ch_all = np.nan
    # tie handling: break ties at random (mean over 200 jitters)
    rng = np.random.default_rng(i)
    jit = np.mean([wauc(sh + rng.uniform(0, 1e-6, len(sh)), sh + rng.uniform(0, 1e-6, len(sh)), w, None)
                   for _ in range(200)])
    nunique = len(np.unique(sh))
    rec = dict(i=i, dataset=r["dataset"], variant=r["monitor_variant"], n_att=len(sa),
               chance_scored_subset=ch_sub, chance_all_attack_lengths=ch_all, chance_random_ties=float(jit),
               n_unique_honest_scores=nunique,
               median_len_scored_att=float(np.median(la)),
               median_len_all_att=float(np.median(la_all)) if la_all is not None else None,
               median_len_hon=float(np.median(lh)),
               chance_ci=next(c["q5"]["chance_ci"] for c in core if c["i"] == i),
               spearman=nulls[i]["spearman_honest_score_len"], spearman_ci=nulls[i]["spearman_ci"])
    c3.append(rec)
    print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rec.items()}))
res["claim3_rows"] = c3
(H / "v3_claims13.json").write_text(json.dumps(res, default=float))
