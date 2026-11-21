import json, sys
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import lw_style as S

S.apply()
g = json.load(open(sys.argv[1]))
out = sys.argv[2]
ms = g["monitors"]
if isinstance(ms, dict):
    ms = [dict(v, key=k) for k, v in ms.items()]
METHOD = "repo_quintile_reweight_nactions"
ms = sorted(ms, key=lambda m: -m["unmatched_auroc"])
n = len(ms)

fig = plt.figure(figsize=(9.6, 7.3))
ax = fig.add_axes([0.235, 0.215, 0.725, 0.535])

ax.axvspan(0.2, 0.5, color="#f4f3ef", zorder=0, lw=0)
ax.axvline(0.5, color=S.MUTED, lw=1.0, zorder=1)

for i, m in enumerate(ms):
    y = n - 1 - i
    u = m["unmatched_auroc"]
    r = m["matched"][METHOD]
    a, (lo, hi) = r["auroc"], r["ci"]
    ax.plot([u, a], [y, y], color=S.AXIS, lw=1.6, zorder=2, solid_capstyle="round")
    ax.plot([lo, hi], [y, y], color=S.BLUE, lw=2.0, alpha=0.35, zorder=3, solid_capstyle="round")
    ax.scatter(u, y, s=62, facecolor=S.SURFACE, edgecolor=S.MUTED, linewidth=1.6, zorder=4)
    ax.scatter(a, y, s=70, color=S.BLUE, edgecolor=S.SURFACE, linewidth=1.4, zorder=5)
    ax.text(0.193, y, m["display_name"], ha="right", va="center", fontsize=10.4, color=S.INK)

ax.set_xlim(0.2, 0.9)
ax.set_ylim(-0.7, n + 0.05)
ax.set_yticks([])
ax.set_xticks([0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
ax.xaxis.grid(True)
ax.spines["left"].set_visible(False)
ax.spines["bottom"].set_visible(False)
ax.set_xlabel("Trajectory-level AUROC (attack vs honest runs, peak suspicion per run)", labelpad=8)
ax.text(0.493, n - 0.5, "worse than guessing", ha="right", va="bottom", fontsize=9, color=S.MUTED)
ax.text(0.507, n - 0.5, "chance = 0.5", ha="left", va="bottom", fontsize=9, color=S.MUTED)

handles = [
    Line2D([0], [0], marker="o", color="none", markerfacecolor=S.SURFACE, markeredgecolor=S.MUTED,
           markeredgewidth=1.6, markersize=8, label="As ranked on the board"),
    Line2D([0], [0], marker="o", color=S.BLUE, markerfacecolor=S.BLUE, markeredgecolor=S.SURFACE,
           markersize=8.5, lw=2.0, alpha=1, label="Honest and attack runs matched on length (95% CI)"),
]
leg = fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.052, 0.835), ncol=2,
                 handlelength=1.8, columnspacing=1.8, fontsize=9.8)
for t in leg.get_texts():
    t.set_color(S.INK2)

ml = g["median_length"]["n_actions"]
S.header(fig,
         "A leaderboard metric that scores most monitors below chance",
         f"On the BashArena monitor board, honest runs are longer than attack runs (median {ml['honest']:.0f} vs {ml['attack']:.0f} actions) and a run’s\n"
         "peak suspicion rises with its length. Matching on length lifts 9 of 11 monitors; 4 to 6 still cannot be told from chance.",
         top=0.972, gap=0.050)
S.source(fig,
         "Data: Redwood Control Leaderboard, monitor evals, BashArena (596 attack and 596 honest runs, 11 monitors), snapshot of 2026-11-17. Matching: honest runs\n"
         "reweighted to the attack runs’ action-count quintiles; exact-length pairing and 1:1 matching give the same picture. The board’s own tooltip notes that peak\n"
         "suspicion can reflect trajectory length, and its step-wise safety metric at a 1% audit budget moves by at most 0.04 for all monitors but one.",
         y=0.02)
S.save(fig, out)
