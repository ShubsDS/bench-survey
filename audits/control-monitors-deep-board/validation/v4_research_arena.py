"""Claim 2: ResearchArena per-agent checks, pairing plausibility, detectable shift; SLEIGHT/SHADE power."""
import itertools
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from vlib import arrays, bin_weights, ci, load, quantile_edges, run_score, wauc  # noqa: E402

H = Path(__file__).parent
d = load()
core = json.loads((H / "v1_core.json").read_text())
ra = d["datasets"]["research-arena"]
att_order = [e["run_id"] for e in ra["attack_eval"]]
hon_order = [e["run_id"] for e in ra["honest_eval"]]
res = {}

# --- pairing plausibility: per-index counts and median lengths, permutation test on lengths
r_act = next(r for r in d["rows"] if r["dataset"] == "research-arena" and r["monitor_kind"] == "action")


def per_agent(row, c, order):
    out = []
    for rid in order:
        S = [s for s in row["score_samples"][c] if s["run_id"] == rid]
        out.append(S)
    return out


A8 = per_agent(r_act, "attack", att_order)
H8 = per_agent(r_act, "honest", hon_order)
na = np.array([len(x) for x in A8])
nh = np.array([len(x) for x in H8])
ma = np.array([np.median([s["n_actions"] for s in x]) for x in A8])
mh = np.array([np.median([s["n_actions"] for s in x]) for x in H8])


def score_pairing(p):
    # agreement of per-agent log median length and of run counts under pairing p (honest index p[k] with attack k)
    rho = np.corrcoef(np.log(ma), np.log(mh[list(p)]))[0, 1]
    cnt = np.corrcoef(na, nh[list(p)])[0, 1]
    return rho, cnt


obs = score_pairing(range(8))
perms = list(itertools.permutations(range(8)))
rhos = np.array([score_pairing(p)[0] for p in perms])
cnts = np.array([score_pairing(p)[1] for p in perms])
res["pairing"] = dict(n_attack=na.tolist(), n_honest=nh.tolist(), median_len_attack=ma.tolist(),
                      median_len_honest=mh.tolist(), corr_loglen_index_pairing=float(obs[0]),
                      corr_counts_index_pairing=float(obs[1]),
                      perm_p_len=float(np.mean(rhos >= obs[0] - 1e-12)),
                      perm_p_counts=float(np.mean(cnts >= obs[1] - 1e-12)),
                      perm_p_both=float(np.mean((rhos >= obs[0] - 1e-12) & (cnts >= obs[1] - 1e-12))))
print("pairing", res["pairing"])


def ra_stats(row, agent_strat=False, B=2000, seed=0, cluster=False):
    kind = row["monitor_kind"]
    Aa = per_agent(row, "attack", att_order)
    Hh = per_agent(row, "honest", hon_order)

    def prep(groups):
        sc, ln, ag = [], [], []
        for g, S in enumerate(groups):
            for s in S:
                v = run_score(s, kind)
                if v is None:
                    continue
                sc.append(v); ln.append(s["n_actions"]); ag.append(g)
        return np.array(sc, float), np.array(ln, float), np.array(ag)

    sa, la, ga = prep(Aa)
    sh, lh, gh = prep(Hh)

    def stat(sa, la, ga, sh, lh, gh):
        if not agent_strat:
            w, keep = bin_weights(la, lh, quantile_edges(la, 5))
        else:
            # stratify by agent x within-agent length tercile (attack terciles); weights to attack shares
            w = np.zeros(len(sh)); keep = np.ones(len(sa), bool)
            tot_a = len(sa)
            for g in np.unique(ga):
                ia, ih = ga == g, gh == g
                if ih.sum() == 0:
                    keep[ia] = False
                    continue
                e = quantile_edges(la[ia], 3)
                wg, kg = bin_weights(la[ia], lh[ih], e)
                share = kg.sum() / tot_a
                w[ih] = wg / wg.sum() * share if wg.sum() > 0 else 0
                kk = keep[ia]; kk[~kg] = False; keep[ia] = kk
        return dict(raw=wauc(sa, sh), chance=wauc(sh, sh, w, None), matched=wauc(sa[keep], sh, None, w))

    pt = stat(sa, la, ga, sh, lh, gh)
    rng = np.random.default_rng(seed)
    bs = {k: [] for k in pt}
    for _ in range(B):
        if cluster:
            gs = rng.integers(0, 8, 8)
            ia = np.concatenate([np.where(ga == g)[0] for g in gs])
            ih = np.concatenate([np.where(gh == g)[0] for g in gs])
            # relabel agents so duplicates are separate strata
            ga_b = np.concatenate([np.full((ga == g).sum(), j) for j, g in enumerate(gs)])
            gh_b = np.concatenate([np.full((gh == g).sum(), j) for j, g in enumerate(gs)])
        else:
            ia = rng.integers(0, len(sa), len(sa)); ih = rng.integers(0, len(sh), len(sh))
            ga_b, gh_b = ga[ia], gh[ih]
        st = stat(sa[ia], la[ia], ga_b, sh[ih], lh[ih], gh_b)
        for k in st:
            bs[k].append(st[k])
    out = dict(point=pt, ci={k: ci(np.array(v)) for k, v in bs.items()},
               se={k: float(np.nanstd(v)) for k, v in bs.items()})
    # per agent and leave-one-agent-out
    per = []
    for g in range(8):
        ia, ih = ga == g, gh == g
        per.append(dict(agent_index=g, n_att=int(ia.sum()), n_hon=int(ih.sum()),
                        raw=wauc(sa[ia], sh[ih]),
                        len_auc=wauc(la[ia], lh[ih])))
    loo = []
    for g in range(8):
        ia, ih = ga != g, gh != g
        loo.append(stat(sa[ia], la[ia], ga[ia], sh[ih], lh[ih], gh[ih])["chance"])
    out["per_agent"] = per
    out["loo_chance_range"] = [float(min(loo)), float(max(loo))]
    out["len_auc_pooled"] = wauc(la, lh)
    return out


for row in [r for r in d["rows"] if r["dataset"] == "research-arena"]:
    k = row["monitor_kind"]
    res[k] = {
        "pooled_run_boot": ra_stats(row, False, seed=1),
        "pooled_cluster_boot": ra_stats(row, False, seed=2, cluster=True),
        "agent_stratified_run_boot": ra_stats(row, True, seed=3),
        "agent_stratified_cluster_boot": ra_stats(row, True, seed=4, cluster=True),
    }
    for kk, v in res[k].items():
        print(k, kk, {x: round(y, 3) for x, y in v["point"].items()},
              {x: [round(z, 3) for z in y] for x, y in v["ci"].items()}, "se chance %.3f" % v["se"]["chance"],
              "LOO", np.round(v["loo_chance_range"], 3))
    print(k, "per agent", [(p["agent_index"], p["n_att"], p["n_hon"], round(p["raw"], 2), round(p["len_auc"], 2))
                            for p in res[k]["pooled_run_boot"]["per_agent"]], "len auc pooled %.3f" % res[k]["pooled_run_boot"]["len_auc_pooled"])

# minimum detectable shift (two-sided 5%, 80% power) ~ 2.8 * SE of chance level, per new dataset
mde = {}
for ds in ("research-arena", "shade-arena", "sleight"):
    se = []
    for r in core:
        if r["dataset"] != ds:
            continue
        b = np.array(r["boot_q5"]["chance"])
        se.append(float(np.nanstd(b)))
    mde[ds] = dict(se_range=[min(se), max(se)], mde_range=[2.8 * min(se), 2.8 * max(se)])
res["mde_run_level"] = mde
print("MDE", mde)
(H / "v4_research_arena.json").write_text(json.dumps(res, default=float))
