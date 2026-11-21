"""Figure: the length-only chance level of the board's default metric, by dataset.

Run:  python fig_chance.py            (needs matplotlib; style from ../../factcheck/charts/lw_style.py)
"""
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "factcheck" / "charts"))
import lw_style as S  # noqa: E402

S.apply()
res = json.load(open(HERE / "results.json"))
rows = [r for r in res["rows"] if "chance_level" in r]

NAMES = {
    "basharena": "BashArena",
    "linuxarena-paper-strategies": "LinuxArena, strategy attacks",
    "linuxarena-paper": "LinuxArena, paper attacks",
    "sleight": "SLEIGHT-Bench",
    "shade-arena": "SHADE-Arena",
    "research-arena": "ResearchArena",
    "monitoringbench": "MonitoringBench",
}
by = {}
for r in rows:
    by.setdefault(r["dataset"], []).append(r)


def key(ds):
    a = [r["chance_level"] for r in by[ds] if r["kind"] == "action"] or [r["chance_level"] for r in by[ds]]
    return sorted(a)[len(a) // 2]


order = sorted(by, key=key)
n = len(order)

fig = plt.figure(figsize=(9.6, 7.0))
ax = fig.add_axes([0.335, 0.235, 0.625, 0.495])
ax.axvspan(0.30, 0.5, color="#f4f3ef", zorder=0, lw=0)
ax.axvline(0.5, color=S.MUTED, lw=1.0, zorder=1)

for i, ds in enumerate(order):
    y = n - 1 - i
    act = [r for r in by[ds] if r["kind"] == "action"]
    trj = [r for r in by[ds] if r["kind"] == "trajectory"]
    both = bool(act) and bool(trj)
    for grp, dy, filled in ((act, 0.16 if both else 0.0, True), (trj, -0.16 if both else 0.0, False)):
        for r in grp:
            lo, hi = r["chance_ci"]
            excl = lo > 0.5 or hi < 0.5
            ax.plot([lo, hi], [y + dy, y + dy], color=S.BLUE if filled else S.MUTED, lw=1.2,
                    alpha=0.22 if excl else 0.12, zorder=2, solid_capstyle="round")
        for r in grp:
            if filled:
                ax.scatter(r["chance_level"], y + dy, s=44, color=S.BLUE, edgecolor=S.SURFACE, linewidth=1.0, zorder=4)
            else:
                ax.scatter(r["chance_level"], y + dy, s=40, facecolor=S.SURFACE, edgecolor=S.MUTED, linewidth=1.4, zorder=3)
    r0 = (act or trj)[0]
    ax.text(0.292, y + 0.13, NAMES[ds], ha="right", va="center", fontsize=10.6, color=S.INK)
    ax.text(0.292, y - 0.2, f"attack {r0['median_len_attack']:g} vs honest {r0['median_len_honest']:g} actions",
            ha="right", va="center", fontsize=8.8, color=S.MUTED)

ax.set_xlim(0.30, 0.66)
ax.set_ylim(-0.7, n - 0.1)
ax.set_yticks([])
ax.set_xticks([0.3, 0.4, 0.5, 0.6])
ax.xaxis.grid(True)
ax.spines["left"].set_visible(False)
ax.spines["bottom"].set_visible(False)
ax.set_xlabel("AUROC a monitor with no detection skill would get", labelpad=8)
ax.text(0.494, n - 0.42, "attacks shorter: no skill scores below 0.5", ha="right", va="bottom", fontsize=9, color=S.MUTED)
ax.text(0.506, n - 0.42, "attacks longer: above 0.5", ha="left", va="bottom", fontsize=9, color=S.MUTED)

handles = [
    Line2D([0], [0], marker="o", color=S.BLUE, markerfacecolor=S.BLUE, markeredgecolor=S.SURFACE, markersize=8,
           lw=1.6, alpha=1, label="Per-step monitor, scored by its peak over the run (95% CI)"),
    Line2D([0], [0], marker="o", color=S.MUTED, markerfacecolor=S.SURFACE, markeredgecolor=S.MUTED,
           markeredgewidth=1.4, markersize=7.5, lw=1.6, label="Whole-trajectory monitor, one score per run"),
]
leg = fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.052, 0.826), ncol=2, handlelength=1.8,
                 columnspacing=1.8, fontsize=9.8)
for t in leg.get_texts():
    t.set_color(S.INK2)

S.header(fig,
         "On a monitor leaderboard, chance is not always 0.5",
         "Each dot is one monitor on one dataset. It shows the AUROC the board would report if attack runs scored like honest\n"
         "runs of the same length. Where attack and honest runs differ in length, that baseline moves away from 0.5.",
         top=0.972, gap=0.052)
S.source(fig,
         f"Data: Redwood Control Leaderboard monitor board, snapshot of {res['generated_at'][:10]}, 84 monitor rows on 7 datasets. Baseline: honest runs reweighted to the attack\n"
         "runs’ length distribution (five bins) against honest runs as they are; intervals from 2,000 run-level resamples, which cannot be clustered by task. BashArena\n"
         "and MonitoringBench survive a second construction and an independent re-derivation; the LinuxArena shifts are leads. SLEIGHT-Bench is paired by design.\n"
         "The snapshot marks SHADE-Arena and SLEIGHT-Bench as private. Step-wise safety at a 1% audit budget moves by 0.03 or more for 4 of 38 rows.",
         y=0.018)
S.save(fig, str(HERE / "fig_chance_level"))
