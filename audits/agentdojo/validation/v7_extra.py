"""Validator step 7: remaining checks on claims 3 and 6 from validation.json and the auditor's
results.json (read as data): row-level vs task-bootstrap interval widths, pairs separated by a
row-level z test, Spearman(utility, exposure) with Opus raw vs traced exposure, and the capability
trend computed directly from the paper's Table 3 numbers.

Run after v2_claims.py: ../data/.venv/bin/python -I v7_extra.py
Writes block 'extra' of validation.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.stats import spearmanr

from common_v import AUDIT, OUT_JSON, save

V = json.load(open(OUT_JSON))
pm = V["per_model"]
asr = np.array([r["S0"] for r in pm])
half_boot = np.array([(r["S0_ci"][1] - r["S0_ci"][0]) / 2 for r in pm])
half_row = 1.96 * np.sqrt(asr * (1 - asr) / 629)
ratio = half_boot / half_row
z_sep = 0
for a in range(len(pm)):
    for b in range(a + 1, len(pm)):
        se = np.sqrt(asr[a] * (1 - asr[a]) / 629 + asr[b] * (1 - asr[b]) / 629)
        z_sep += abs(asr[a] - asr[b]) / se > 1.96
U = np.array([r["U"] for r in pm])
E_traced = np.array([r["E"] for r in pm])
E_raw = E_traced.copy()
iop = [r["model"] for r in pm].index("claude-3-opus-20240229")
E_raw[iop] = E_traced[iop] * pm[iop]["n_traced"] / 629
# paper Table 3 (v3): benign utility and targeted ASR, read from data/paper/v3.html
T3 = {"Claude 3 Opus": (66.61, 11.29), "Claude 3 Sonnet": (53.10, 26.71), "Claude 3.5 Sonnet": (78.22, 33.86),
      "Command-R+": (25.44, 0.95), "Gemini 1.5 Flash": (36.09, 12.24), "Gemini 1.5 Pro": (45.63, 25.60),
      "GPT-3.5 Turbo": (33.86, 8.43), "GPT-4 Turbo": (63.43, 28.62), "GPT-4o": (69.00, 47.69), "Llama 3 70b": (34.50, 20.03)}
tu, ta = np.array([v[0] for v in T3.values()]), np.array([v[1] for v in T3.values()])
rng = np.random.default_rng(7)
rho = spearmanr(tu, ta).statistic
perm = np.array([spearmanr(rng.permutation(tu), ta).statistic for _ in range(10000)])
out = dict(
    interval_ratio=dict(median=round(float(np.median(ratio)), 2), min=round(float(ratio.min()), 2), max=round(float(ratio.max()), 2)),
    pairs_separated_row_level_z=int(z_sep),
    spearman_U_E_traced=round(float(spearmanr(U, E_traced).statistic), 3),
    spearman_U_E_raw_opus=round(float(spearmanr(U, E_raw).statistic), 3),
    paper_table3_trend=dict(spearman=round(float(rho), 3), perm_p=round(float((np.abs(perm) >= abs(rho) - 1e-12).mean()), 4), n=10),
)
save("extra", out)
print(json.dumps(out, indent=1))
for r in sorted(pm, key=lambda r: r["S0"]):
    print(f"{r['model']:32s} S0 {100*r['S0']:5.1f} E {100*r['E']:5.1f} S1 {100*r['S1']:5.1f} d {r['S1_minus_S0_pp']:6.2f} {r['S1_minus_S0_ci_pp']} "
          f"rank {r['rank_S0']:4.1f}->{r['rank_S1']:4.1f} {r['rank_change_S1_ci']}  S2 {100*r['S2']:5.1f} {r['S2_ci']} S3 {100*r['S3']:5.1f} able {r['A_share_able']}")
