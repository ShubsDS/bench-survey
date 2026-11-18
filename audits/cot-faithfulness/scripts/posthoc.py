"""Post hoc analyses (not pre-registered; labelled as such in the README). Writes
results/posthoc.json.

P1. Pair-specific polarity heterogeneity. Under the template-lean null N1t, the wrong answers of
    every pair in a template split between "wrong YES" (on the NO-keyed question) and "wrong NO"
    (on the YES-keyed question) in the same proportion. A pair-specific yes/no bias makes some
    pairs all-wrong-YES and others all-wrong-NO, inflating the dispersion of that split. A
    consistent wrong belief about the facts splits a pair's wrong answers evenly and lowers it.
    Statistic: Pearson dispersion of yN_j given W_j around the template share, over pairs with
    W_j >= 2, observed against 500 N1t simulations.
P2. Share of pairs the model does not reliably know (kappa_hat < 0.5) and the template lean among
    guesses, per model.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from analyse import fit_null, model_arrays, simulate  # noqa: E402
from iphr_core import MAIN_DF, PAPER_NAMES, build_pairs  # noqa: E402
from safe_load import load_df  # noqa: E402

SEED = 7


def dispersion(cY, cN, gcode, ng):
    W = cY[:, 1] + cN[:, 0]
    yN = cN[:, 0]
    m = W >= 2
    sw = np.bincount(gcode[m], W[m], ng)
    sy = np.bincount(gcode[m], yN[m], ng)
    share = np.where(sw > 0, sy / np.maximum(sw, 1), 0.5)[gcode]
    v = W * share * (1 - share)
    ok = m & (v > 0)
    return float(((yN[ok] - W[ok] * share[ok]) ** 2 / v[ok]).sum() / max(ok.sum(), 1)), int(ok.sum())


def main():
    rng = np.random.default_rng(SEED)
    P = build_pairs(load_df(MAIN_DF))
    groups = {g: i for i, g in enumerate(sorted(P.group.unique()))}
    ng = len(groups)
    out = {}
    for m, name in PAPER_NAMES.items():
        p = P[P.model_id == m].sort_values(["group", "pkey"]).reset_index(drop=True)
        cY, cN = model_arrays(p)
        gcode = p.group.map(groups).to_numpy()
        # use 10-response tables for the oversampled pairs (dispersion depends on n)
        os_ = (cY.sum(1) > 10) & (cN.sum(1) > 10)
        if os_.any():
            from analyse import subsample
            cY, cN = subsample(cY, 10, rng), subsample(cN, 10, rng)
        d_obs, n_used = dispersion(cY, cN, gcode, ng)
        pYq, pNq, lean = fit_null(cY, cN, gcode, ng)
        sims = []
        for _ in range(500):
            sY, sN = simulate(pYq, pNq, 10, rng)
            sims.append(dispersion(sY, sN, gcode, ng)[0])
        sims = np.array(sims)
        kY, kN = cY[:, 0] + cY[:, 1], cN[:, 0] + cN[:, 1]
        wr = cY[:, 1] / np.maximum(kY, 1) + cN[:, 0] / np.maximum(kN, 1)
        kap = 1 - np.clip(wr, 0, 1)
        out[name] = {"dispersion_obs": d_obs, "pairs_used": n_used,
                     "dispersion_null_mean": float(sims.mean()),
                     "dispersion_null_p97.5": float(np.percentile(sims, 97.5)),
                     "p_null_ge_obs": float((sims >= d_obs).mean()),
                     "share_pairs_kappa_lt_0.5": float((kap < 0.5).mean()),
                     "n_pairs_kappa_lt_0.5": int((kap < 0.5).sum())}
        print(name, {k: round(v, 3) if isinstance(v, float) else v for k, v in out[name].items()})
    Path("results/posthoc.json").write_text(json.dumps({"P1_P2": out}, indent=1))


if __name__ == "__main__":
    main()
