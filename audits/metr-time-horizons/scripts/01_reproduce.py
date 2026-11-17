"""Step 6 precondition: reproduce METR's published TH1.1 horizons and 2023+ doubling time.

Published values: data/published/benchmark_results_1_1.yaml (metr.org/assets, sha256 in README).
Output: results/reproduce.json
"""
import sys

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import (PUB_BENCH, bootstrap_fits, doubling_ci, doubling_time, fit_agents, load_counts,
                    prepare, save, sota_agents)

N_BOOT = 1000
SEED = 42

df, dates = load_counts()
df = prepare(df)
pub = yaml.safe_load(PUB_BENCH.read_text())
pub_by_date = {}
for key, v in pub["results"].items():
    pub_by_date.setdefault(str(v["release_date"]), []).append((key, v["metrics"]))

fits = fit_agents(df)

# Match published entries to agents by release date and p50 (keys differ: alias vs model id).
rows = []
for agent, f in fits.iterrows():
    cands = pub_by_date.get(str(dates[agent].date()), [])
    key, m = min(cands, key=lambda km: abs(np.log(km[1]["p50_horizon_length"]["estimate"] / f.p50)))
    p = m["p50_horizon_length"]
    q = m["p80_horizon_length"]
    rows.append(dict(agent=agent, pub_key=key, date=str(dates[agent].date()), p50=f.p50, pub_p50=p["estimate"],
                     pub_p50_lo=p["ci_low"], pub_p50_hi=p["ci_high"], p80=f.p80, pub_p80=q["estimate"],
                     pub_sota=m["is_sota"], slope=f.slope))
rep = pd.DataFrame(rows).set_index("agent")
rep["ratio_p50"] = rep.p50 / rep.pub_p50
rep["ratio_p80"] = rep.p80 / rep.pub_p80

p50b, p80b, _ = bootstrap_fits(df, N_BOOT, SEED)
rep["p50_lo"] = p50b.quantile(0.025)
rep["p50_hi"] = p50b.quantile(0.975)
rep["p80_lo"] = p80b.quantile(0.025)
rep["p80_hi"] = p80b.quantile(0.975)

sota = sota_agents(fits.p50, dates)
dt = doubling_time(fits.p50, dates, sota)
lo, hi, dts = doubling_ci(p50b, dates, sota)

# Variant without the 16 h exclusion, for transparency.
sota_all = sota_agents(fits.p50, dates, max_p50=None)
dt_all = doubling_time(fits.p50, dates, sota_all)

pd.set_option("display.width", 220)
print(rep[["pub_key", "p50", "pub_p50", "ratio_p50", "p50_lo", "p50_hi", "pub_p50_lo", "pub_p50_hi", "p80",
           "pub_p80", "ratio_p80"]].round(3).to_string())
print("SOTA (2023+, <=16h):", sota)
print(f"doubling time 2023+: {dt:.1f} d [{lo:.1f}, {hi:.1f}] (published 128.744 [104.428, 158.012]); n_boot ok={len(dts)}")
print(f"without 16h exclusion: {dt_all:.1f} d, agents {sota_all}")

save("reproduce.json", dict(
    per_agent=rep.reset_index().to_dict(orient="records"),
    sota_2023=sota, doubling_2023=dict(point=dt, ci=[lo, hi], n_boot=len(dts),
                                       published=dict(point=128.744, ci=[104.428, 158.012])),
    doubling_2023_no16h_exclusion=dict(point=dt_all, agents=sota_all),
    max_abs_log_ratio_p50=float(np.abs(np.log(rep.ratio_p50)).max()),
    n_boot=N_BOOT, seed=SEED,
))
