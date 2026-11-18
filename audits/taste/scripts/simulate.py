"""Simulations T4-T6 (prereg.md). SYNTHETIC benchmarks only: nothing here is TASTE data.

Every synthetic benchmark matches the published structure:
  - 50 proposals with anchor scores 1..5 in counts (6, 19, 17, 6, 2)  (paper Fig. 13)
  - 92 pairs, every pair with score gap >= 2, so the label is the higher-scored proposal (§2.3)
  - 4 "magnet" proposals in exactly 10 pairs each, no pair between two magnets, 52 magnet-free
    pairs (App. D.3); other proposals in at most 8 pairs; every proposal in at least one pair.
Simplification: one score per proposal (Fig. 13 counts each proposal once at its anchor score).

Run: data/.venv/bin/python -I scripts/simulate.py   -> results/simulate.json  (seed 20261117)
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
RNG = np.random.default_rng(20261117)
SCORES = np.array([1] * 6 + [2] * 19 + [3] * 17 + [4] * 6 + [5] * 2)
NP = len(SCORES)


def make_graph(rng):
    """Return (edges array (92,2) with winner first, magnet mask over edges)."""
    cand_all = [(i, j) for i in range(NP) for j in range(i + 1, NP) if abs(SCORES[i] - SCORES[j]) >= 2]
    for _ in range(500):
        deg = np.zeros(NP, int)
        edges = set()
        pool = [i for i in range(NP) if SCORES[i] in (1, 4, 5)]
        mags = set(rng.choice(pool, 4, replace=False).tolist())
        ok = True
        for m in mags:
            partners = [j for j in range(NP) if j not in mags and abs(SCORES[m] - SCORES[j]) >= 2 and deg[j] < 8]
            if len(partners) < 10:
                ok = False; break
            for j in rng.choice(partners, 10, replace=False):
                edges.add((min(m, j), max(m, j))); deg[m] += 1; deg[j] += 1
        if not ok:
            continue
        nonmag_cand = [e for e in cand_all if e[0] not in mags and e[1] not in mags]
        for i in rng.permutation(NP):
            if deg[i] == 0:
                opts = [e for e in nonmag_cand if i in e and e not in edges and deg[e[0] if e[1] == i else e[1]] < 8]
                if not opts:
                    ok = False; break
                e = opts[rng.integers(len(opts))]
                edges.add(e); deg[e[0]] += 1; deg[e[1]] += 1
        if not ok:
            continue
        order = rng.permutation(len(nonmag_cand))
        for k in order:
            if len(edges) == 92:
                break
            e = nonmag_cand[k]
            if e in edges or deg[e[0]] >= 8 or deg[e[1]] >= 8:
                continue
            edges.add(e); deg[e[0]] += 1; deg[e[1]] += 1
        if len(edges) != 92 or (deg == 0).any():
            continue
        E = np.array([(i, j) if SCORES[i] > SCORES[j] else (j, i) for i, j in edges])
        mag = np.array([(a in mags) or (b in mags) for a, b in E])
        if mag.sum() != 40:
            continue
        return E, mag, sorted(mags)
    raise RuntimeError("graph generation failed")


def zscore(v):
    return (v - v.mean()) / v.std()


def model_acc(E, v, sigma_pair, rng, nrep=1):
    """Accuracy per pair: model picks the higher of v + pair noise (prob over pair noise)."""
    d = v[E[:, 0]] - v[E[:, 1]]
    if sigma_pair == 0:
        return (d > 0).astype(float) + 0.5 * (d == 0)
    from scipy.stats import norm
    return norm.cdf(d / (sigma_pair * np.sqrt(2)))


# ---------------------------------------------------------------- T4 design effect
def t4(nbench=2000):
    graphs = [make_graph(RNG) for _ in range(200)]
    out = {"note": "SD of accuracy across fresh synthetic benchmarks vs binomial SD; model accuracy calibrated to ~0.60",
           "grid": {}}
    zs = zscore(SCORES.astype(float))
    for rho in (0.0, 0.25, 0.5, 0.75, 1.0):
        # perceived quality v = a*z + sqrt(rho)*e_prop ; pair noise sd sqrt(1-rho)
        best = None
        for a in np.linspace(0.0, 1.5, 61):
            accs = []
            for b in range(300):
                E, mag, _ = graphs[b % len(graphs)]
                v = a * zs + np.sqrt(rho) * RNG.standard_normal(NP)
                p = model_acc(E, v, np.sqrt(1 - rho), RNG)
                accs.append(p.mean() if rho < 1 else ((v[E[:, 0]] > v[E[:, 1]]).mean()))
            if best is None or abs(np.mean(accs) - 0.60) < abs(best[1] - 0.60):
                best = (a, float(np.mean(accs)))
        a = best[0]
        accs, accs_mf, accs_null, null_mf, null52rand = [], [], [], [], []
        for b in range(nbench):
            E, mag, _ = graphs[b % len(graphs)]
            v = a * zs + np.sqrt(rho) * RNG.standard_normal(NP)
            sd_pair = np.sqrt(1 - rho)
            y = (v[E[:, 0]] + sd_pair * RNG.standard_normal(92) > v[E[:, 1]] + sd_pair * RNG.standard_normal(92)).astype(float)
            accs.append(y.mean()); accs_mf.append(y[~mag].mean())
            v0 = np.sqrt(rho) * RNG.standard_normal(NP)  # no-signal model, same noise structure
            y0 = (v0[E[:, 0]] + sd_pair * RNG.standard_normal(92) > v0[E[:, 1]] + sd_pair * RNG.standard_normal(92)).astype(float)
            accs_null.append(y0.mean()); null_mf.append(y0[~mag].mean())
            null52rand.append(y0[RNG.choice(92, 52, replace=False)].mean())
        accs, accs_null, null_mf = map(np.array, (accs, accs_null, null_mf))
        sd, sd_bin = accs.std(), np.sqrt(0.6 * 0.4 / 92)
        out["grid"][str(rho)] = {
            "a": round(float(a), 3), "mean_acc": round(float(accs.mean()), 3),
            "sd_acc": round(float(sd), 4), "sd_binomial": round(float(sd_bin), 4),
            "design_effect": round(float((sd / sd_bin) ** 2), 2),
            "ci95_halfwidth_pts": round(float(1.96 * sd * 100), 1),
            "null_sd_92": round(float(accs_null.std()), 4),
            "null_p975_92": round(float(np.quantile(accs_null, 0.975)), 3),
            "null_p_ge_060": round(float((accs_null >= 0.60).mean()), 4),
            "null_magnetfree_p025": round(float(np.quantile(null_mf, 0.025)), 3),
            "null_magnetfree_sd": round(float(null_mf.std()), 4),
            "null_magnetfree_p_le_21pct": round(float((null_mf <= 11 / 52).mean()), 4),
            "null_magnetfree_p_le_296": round(float((null_mf <= 0.296).mean()), 4),
            "binomial_sd_52": round(float(np.sqrt(0.25 / 52)), 4),
        }
    # Structural facts across graphs
    winners = []
    for E, mag, mags in graphs:
        u, c = np.unique(E[:, 0], return_counts=True)
        winners.append((len(u), int(np.sort(c)[::-1][:8].sum())))
    out["distinct_winners_mean"] = round(float(np.mean([w[0] for w in winners])), 1)
    out["pairs_won_by_top8_winners_mean"] = round(float(np.mean([w[1] for w in winners])), 1)
    out["min_proposals_carrying_32_decided"] = 4  # each decided pair holds a term-bearing proposal; <=10 pairs each
    return out


# ---------------------------------------------------------------- T5 tuning null
def rule_acc(E, counts):
    cw, cl = counts[E[:, 0]], counts[E[:, 1]]
    return np.where(cw < cl, 1.0, np.where(cw > cl, 0.0, 0.5))


def t5(nbench=2000):
    out = {}
    graphs = [make_graph(RNG) for _ in range(200)]
    for K in (1, 5, 10, 20, 40):
        best = []
        for b in range(nbench):
            E, _, _ = graphs[b % len(graphs)]
            accs = []
            for _ in range(K):
                prev = RNG.uniform(0.10, 0.40)
                pres = RNG.random(NP) < prev
                counts = pres * RNG.integers(1, 8, NP)
                accs.append(rule_acc(E, counts).mean())
            best.append(max(accs))
        best = np.array(best)
        out[f"K={K}"] = {"p50": round(float(np.median(best)), 3), "p95": round(float(np.quantile(best, 0.95)), 3),
                         "p_ge_063": round(float((best >= 0.63).mean()), 4)}
    # Greedy narrowing of a 40-term list on the labels (backward elimination), label-null.
    tuned, wide = [], []
    for b in range(500):
        E, _, _ = graphs[b % len(graphs)]
        topic = RNG.random(NP) < 0.25           # a topic present in ~25% of proposals, independent of score
        rates = np.where(topic[:, None], RNG.uniform(0.05, 0.5, (1, 40)), RNG.uniform(0.0, 0.06, (1, 40)))
        C = RNG.poisson(rates * 3)              # term counts, proposals x terms
        keep = np.ones(40, bool)
        cur = rule_acc(E, C[:, keep].sum(1)).mean(); wide.append(cur)
        improved = True
        while improved:
            improved = False
            for t in np.where(keep)[0]:
                k2 = keep.copy(); k2[t] = False
                if k2.sum() == 0:
                    continue
                a2 = rule_acc(E, C[:, k2].sum(1)).mean()
                if a2 > cur + 1e-12:
                    keep, cur, improved = k2, a2, True
        tuned.append(cur)
    tuned, wide = np.array(tuned), np.array(wide)
    out["greedy_narrowing_40_terms"] = {
        "wide_p50": round(float(np.median(wide)), 3), "wide_p95": round(float(np.quantile(wide, 0.95)), 3),
        "tuned_p50": round(float(np.median(tuned)), 3), "tuned_p95": round(float(np.quantile(tuned, 0.95)), 3),
        "tuned_p_ge_063": round(float((tuned >= 0.63).mean()), 4)}
    return out


# ---------------------------------------------------------------- T6 split artifact
def t6(nbench=400):
    """Topic penalised by raters; models with positive quality signal plus an anti-topic prior.

    Grid over: share of interp-adjacent non-interp proposals (which the narrowing can push into
    ties), the weight a model's prior puts on adjacency, and whether the prior rises with
    capability. Quality signal a is small and always > 0 (no anti-taste), calibrated so that
    overall accuracies sit around 50-60% as in the paper.
    """
    graphs = [make_graph(RNG) for _ in range(200)]
    zs = zscore(SCORES.astype(float))
    res = {}
    caps = np.linspace(0, 1, 28)
    for adj_prev in (0.15, 0.30, 0.45):
        for adj_w in (0.7, 1.5):
            for scen, gam, a_of_c in (("prior_indep", lambda c: 0.8 + 0 * c, lambda c: 0.05 + 0.20 * c),
                                      ("prior_rises", lambda c: 0.1 + 1.6 * c, lambda c: 0.05 + 0.20 * c),
                                      ("prior_rises_signal_flat", lambda c: 0.1 + 1.6 * c, lambda c: 0.08 + 0 * c)):
                pattern, rs, top, allacc, nties, below = 0, [], [], [], [], []
                for b in range(nbench):
                    E, mag, _ = graphs[b % len(graphs)]
                    p_topic = 1 / (1 + np.exp(-(-0.6 - 0.9 * (SCORES - 2.4))))
                    topic = RNG.random(NP) < p_topic * 0.55
                    adj = (~topic) & (RNG.random(NP) < adj_prev)
                    core = np.where(topic, RNG.poisson(3.0, NP) + 1, 0)
                    amb = np.where(topic, RNG.poisson(1.5, NP), 0) + np.where(adj, RNG.poisson(1.2, NP) + 1, 0)
                    wide = rule_acc(E, core + amb).mean()
                    counts = core if rule_acc(E, core).mean() >= wide else core + amb
                    tie = rule_acc(E, counts) == 0.5
                    nties.append(int(tie.sum()))
                    if not tie.any():
                        continue
                    t_acc, o_acc = [], []
                    for c in caps:
                        a = a_of_c(c)
                        v = a * zs - gam(c) * (topic + adj_w * adj) + 0.7 * RNG.standard_normal(NP)
                        y = (v[E[:, 0]] + 0.7 * RNG.standard_normal(92) > v[E[:, 1]] + 0.7 * RNG.standard_normal(92)).astype(float)
                        t_acc.append(y[tie].mean()); o_acc.append(y.mean())
                    t_acc = np.array(t_acc)
                    r = np.corrcoef(caps, t_acc)[0, 1]
                    rs.append(r); top.append(t_acc[14:].mean()); allacc.append(np.mean(o_acc))
                    below.append((t_acc[14:] < 0.5).sum())
                    if (t_acc[14:] < 0.5).all() and r <= -0.6:
                        pattern += 1
                res[f"adj{adj_prev}_w{adj_w}_{scen}"] = {
                    "freq_critic_pattern": round(pattern / nbench, 4),
                    "median_r_cap_ties": round(float(np.median(rs)), 3),
                    "p05_r_cap_ties": round(float(np.quantile(rs, 0.05)), 3),
                    "mean_top14_tie_acc": round(float(np.mean(top)), 3),
                    "median_top14_below50": float(np.median(below)),
                    "mean_overall_acc": round(float(np.mean(allacc)), 3),
                    "median_n_ties": int(np.median(nties))}
    return res


def main():
    out = {"WARNING": "synthetic benchmarks with the published structure; not TASTE data",
           "T4": t4(), "T5": t5(), "T6": t6()}
    (HERE / "results/simulate.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
