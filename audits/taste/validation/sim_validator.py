"""Validator's own simulations for the TASTE audit. Written from scratch; the auditor's
simulate.py was not read before this file was written. SYNTHETIC BENCHMARKS, NOT TASTE DATA:
every number from this file is a property of the assumed mechanism, evidence level L1 (lead) at most.

Part A (design effect, attacks audit finding 7 / claim C1): how often a model with NO signal
reaches >= 60% on a 92-pair benchmark whose pairs share proposals, as a function of
  rho   = share of the model's noise that is per proposal (unmeasured), and
  graph = the assumed pair graph:
    G_fixed : proposal scores fixed (6,19,17,6,2), candidate pairs = random gap>=2 pairs,
              cap 10 per proposal keeping the largest gaps (my construction, not the auditor's);
    G_rater : as G_fixed, but each pair's label comes from its own anchor, whose score is the
              proposal's score plus rater noise (labels not fixed by proposal);
    G_flat  : 92 pairs over 50 proposals with near-uniform degree (3-4), no magnets.
Part B (split artifact, attacks finding 5): synthetic benchmarks with a real topic confound in
the labels, the "fewer terms" split, and 28 models placed at the real ECI values. Model
preference for proposal p:  a*q_p - lam_i*t_p + gam_i*s_p + noise, with
  q = quality that drives the human score, t = interp topic (term-bearing),
  s = an appeal shared by all models (an "LLM taste"), independent of q in the generated pool.
Scenarios:
  B1 topic reliance rising with capability (lam_i grows with ECI), gam = 0;
  B2 shared appeal reliance rising with capability (gam_i grows with ECI), no selection;
  B3 as B2, but the 50 proposals are the survivors of an LLM-grader selection on q + s from a
     larger pool (best-of-N proposal generation; paper App. A), which makes q and s negatively
     correlated among survivors (Berkson). No model has anti-taste in the generated pool.
  B4 topic reliance and shared-appeal reliance both rise with ECI (with and without selection).
Outcome: share of runs reproducing the critique's pattern on the tie pairs:
  "pattern" = all models with ECI > 158 below 50% AND r(ECI, tie accuracy) <= -0.6;
  also share with mean tie accuracy of those models <= 40%, and mean decided accuracy.
Seed 20261117.
"""
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent.parent
rng = np.random.default_rng(20261117)
SCORES = np.repeat([1, 2, 3, 4, 5], [6, 19, 17, 6, 2])
ECI28 = np.array([142.76, 151.88, 152.86, 156.35, 156.9, 157.5, 159.91, 164.21, 164.74, 167.09, 168.7, 173.5,
                  156.7, 160.78, 163.05, 160.19, 156.39, 163.82, 169.2, 168.63, 167.72,
                  153.04, 154.58, 154.92, 154.97, 155.35, 156.25, 158.6])
STRONG = ECI28 > 158
CZ = (ECI28 - ECI28.min()) / (ECI28.max() - ECI28.min())  # 0..1


def build_graph(scores, kind, n_cand=166):
    n = len(scores)
    if kind == "G_flat":
        pairs = set()
        while len(pairs) < 92:
            i, j = rng.choice(n, 2, replace=False)
            deg = np.bincount([x for p in pairs for x in p], minlength=n)
            if deg[i] < 4 and deg[j] < 4 and (min(i, j), max(i, j)) not in pairs:
                pairs.add((min(i, j), max(i, j)))
        pairs = list(pairs)
        lab_score = {p: (scores[p[0]] + rng.normal(0, 1e-3), scores[p[1]]) for p in pairs}
        out = []
        for i, j in pairs:  # labels: higher latent score wins (ties broken randomly)
            out.append((i, j) if scores[i] + rng.normal(0, 1e-3) > scores[j] else (j, i))
        return out
    cand = [(i, j) for i in range(n) for j in range(n) if scores[i] - scores[j] >= 2]
    pick = [cand[k] for k in rng.choice(len(cand), min(n_cand, len(cand)), replace=False)]
    pick.sort(key=lambda p: -(scores[p[0]] - scores[p[1]]) + rng.uniform(0, 0.1))
    deg = np.zeros(n, int); out = []
    for w, l in pick:
        if deg[w] < 10 and deg[l] < 10:
            out.append((w, l)); deg[w] += 1; deg[l] += 1
        if len(out) == 92:
            break
    return out


def part_a(n_graphs=200, n_noise=200):
    res = {}
    for kind in ("G_fixed", "G_rater", "G_flat"):
        for rho in (0.0, 0.1, 0.25, 0.5, 0.75, 1.0):
            accs = []
            for _ in range(n_graphs):
                g = build_graph(SCORES, kind)
                if kind == "G_rater":
                    # anchor-specific labels: winner per pair decided by score + rater noise (sd 0.7)
                    g = [(w, l) if (SCORES[w] - SCORES[l]) + rng.normal(0, 0.7 * np.sqrt(2)) > 0 else (l, w) for w, l in g]
                W = np.array([p[0] for p in g]); L = np.array([p[1] for p in g])
                u = rng.normal(0, np.sqrt(rho), (n_noise, 50))
                e = rng.normal(0, np.sqrt(1 - rho), (n_noise, len(g)))
                correct = (u[:, W] - u[:, L] + e) > 0
                accs.append(correct.mean(1))
            a = np.concatenate(accs)
            res[f"{kind}|rho={rho}"] = {"sd_pts": round(float(a.std() * 100), 2),
                                         "design_effect": round(float(a.var() / (0.25 / 92)), 2),
                                         "P_nosignal_ge_60": round(float(np.mean(a >= 0.6 - 1e-9)), 4),
                                         "P_nosignal_le_21pct_of52": None}
    return res


def gen_benchmark(scen, pi_topic=0.3, beta=1.0, sel_keep=1.0):
    pool = int(round(50 / sel_keep))
    q = rng.normal(0, 1, pool); s = rng.normal(0, 1, pool); t = (rng.uniform(size=pool) < pi_topic).astype(float)
    if sel_keep < 1:
        keep = np.argsort(-(q + s + rng.normal(0, 0.5, pool)))[:50]  # LLM grader: likes q and s
        q, s, t = q[keep], s[keep], t[keep]
    h = q - beta * t + rng.normal(0, 0.5, 50)  # human score with a real topic confound
    scores = np.empty(50, int); scores[np.argsort(h)] = SCORES
    g = build_graph(scores, "G_fixed")
    W = np.array([p[0] for p in g]); L = np.array([p[1] for p in g])
    tie = (t[W] == t[L]) & (t[W] == 0)  # both term-free (51 of the critic's 52 ties are)
    dec = t[W] != t[L]
    return q, s, t, W, L, tie, dec


def part_b(n_runs=400):
    """Grid over a (weight on true quality), lam (topic reliance), gam (shared-appeal reliance)
    and selection. Calibration targets from the critic/paper: mean decided accuracy ~57%, mean
    overall ~50%, pairwise agreement between models ~0.7-0.76 (critic)."""
    res = {}
    settings = []
    for a in (0.15, 0.3):
        for lam in (0.0, 1.0, 3.0):
            settings.append(("B1", dict(a=a, lam_max=lam, gam_max=0.0, sel=1.0)))
        for gam in (0.5, 1.0, 2.0):
            settings.append(("B2", dict(a=a, lam_max=1.0, gam_max=gam, sel=1.0)))
            for sel in (0.5, 0.2):
                settings.append(("B3", dict(a=a, lam_max=1.0, gam_max=gam, sel=sel)))
        for lam in (2.0, 4.0):  # B4: topic reliance AND shared-appeal reliance both rise with ECI
            for gam in (1.0, 2.0):
                for sel in (1.0, 0.2):
                    settings.append(("B4", dict(a=a, lam_max=lam, gam_max=gam, sel=sel)))
    for scen, p in settings:
        pat = low = pat2 = 0; rdec = []; rs = []; tie_strong = []; dec_mean = []; all_mean = []; agree = []
        for _ in range(n_runs):
            q, s, t, W, L, tie, dec = gen_benchmark(scen, sel_keep=p["sel"])
            lam = p["lam_max"] * CZ if scen in ("B1", "B4") else np.full(28, p["lam_max"])
            gam = p["gam_max"] * CZ
            base = p["a"] * (q[W] - q[L]); topic = -(t[W] - t[L]); shared = s[W] - s[L]
            noise = rng.normal(0, np.sqrt(2) * 0.5, (28, len(W)))
            d = base[None] + lam[:, None] * topic[None] + gam[:, None] * shared[None] + noise
            corr = (d > 0).astype(float)
            ta = corr[:, tie].mean(1) * 100; da = corr[:, dec].mean(1) * 100
            r = np.corrcoef(ECI28, ta)[0, 1] if ta.std() > 0 else 0.0
            rs.append(r); tie_strong.append(ta[STRONG].mean()); dec_mean.append(da.mean()); all_mean.append(corr.mean() * 100)
            cs = corr[STRONG][:, tie]
            agree.append(np.mean([(cs[i] == cs[j]).mean() for i in range(len(cs)) for j in range(i + 1, len(cs))]))
            pat += (np.all(ta[STRONG] < 50) and r <= -0.6)
            low += ta[STRONG].mean() <= 40
            rd = np.corrcoef(ECI28, da)[0, 1] if da.std() > 0 else 0.0
            rdec.append(rd)
            pat2 += (np.all(ta[STRONG] < 50) and r <= -0.6 and rd > 0)
        key = f"{scen}|" + ",".join(f"{k}={v}" for k, v in p.items())
        res[key] = {"P_pattern": round(pat / n_runs, 4), "P_pattern_and_decided_r_gt0": round(pat2 / n_runs, 4),
                    "median_r_decided": round(float(np.median(rdec)), 3), "P_strong_mean_tie_le40": round(low / n_runs, 4),
                    "median_r": round(float(np.median(rs)), 3), "P_r_le_-0.6": round(float(np.mean(np.array(rs) <= -0.6)), 4),
                    "median_strong_tie_acc": round(float(np.median(tie_strong)), 1),
                    "median_decided_acc": round(float(np.median(dec_mean)), 1),
                    "median_overall_acc": round(float(np.median(all_mean)), 1),
                    "median_strong_agreement_ties": round(float(np.median(agree)), 3)}
    return res


if __name__ == "__main__":
    out = {"part_a_design_effect": part_a(), "part_b_split_artifact": part_b()}
    (HERE / "validation/validation_sim.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
