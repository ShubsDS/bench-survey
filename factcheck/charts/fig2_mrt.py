import json, sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import lw_style as S

S.apply()
g = json.load(open(sys.argv[1]))
out = sys.argv[2]
arms = {a["name"]: a for a in g["arms"]}

hon = arms["honest"]["per_transcript"]
rel = {(p["task"], p["file"]): p["score"] for p in arms["unaware_released"]["per_transcript"]}
edt = {(p["task"], p["file"]): p["score"] for p in arms["unaware_no_model_thinking"]["per_transcript"]}
keys = [k for k in rel if k in edt and rel[k] is not None and edt[k] is not None]
HI_TASK = "american_airlines_2"

rng = np.random.default_rng(3)
fig = plt.figure(figsize=(9.6, 7.3))
ax = fig.add_axes([0.085, 0.275, 0.875, 0.485])

X_H, X_R, X_E = 0.0, 1.35, 2.7

# honest runs
hs = np.array([p["score"] for p in hon], float)
ax.scatter(X_H + rng.uniform(-0.16, 0.16, len(hs)), hs, s=46, color=S.GRAY, edgecolor=S.SURFACE,
           linewidth=1.2, zorder=3)
hmax = hs.max()
ax.axhline(hmax, color=S.AXIS, lw=0.9, zorder=1)
ax.text(X_H + 0.28, hmax + 1.6, "Most suspicious honest run", ha="left", va="bottom", fontsize=9, color=S.MUTED)

# paired sabotage runs
for k in sorted(keys, key=lambda k: k[0] == HI_TASK):
    hi = k[0] == HI_TASK
    col = S.ORANGE if hi else S.BLUE
    jr, je = rng.uniform(-0.07, 0.07), rng.uniform(-0.07, 0.07)
    ax.plot([X_R + jr, X_E + je], [rel[k], edt[k]], color=col, lw=1.3 if hi else 1.0,
            alpha=0.75 if hi else 0.38, zorder=2 + hi, solid_capstyle="round")
    for x, yv in ((X_R + jr, rel[k]), (X_E + je, edt[k])):
        ax.scatter(x, yv, s=46, color=col, edgecolor=S.SURFACE, linewidth=1.2, zorder=4 + hi)

ax.set_xlim(-0.55, 3.25)
ax.set_ylim(-3, 104)
ax.set_yticks([0, 25, 50, 75, 100])
ax.yaxis.grid(True)
ax.spines["left"].set_visible(False)
ax.set_ylabel("Monitor’s suspicion score (0–100)", labelpad=8)
ax.set_xticks([X_H, X_R, X_E])
ax.set_xticklabels([])

a_r, a_e = arms["unaware_released"], arms["unaware_no_model_thinking"]
lab = [
    (X_H, "Honest runs", "n = 30", ""),
    (X_R, "Sabotage runs, as released", "plans written where the monitor reads",
     f"AUROC {a_r['auroc']:.3f}"),
    (X_E, "Same runs, planning blocks deleted", "tool calls and outputs untouched",
     f"AUROC {a_e['auroc']:.2f}  (95% CI {a_e['ci95_run_bootstrap'][0]:.2f}–{a_e['ci95_run_bootstrap'][1]:.2f})"),
]
for x, l1, l2, l3 in lab:
    ax.text(x, -9.5, l1, ha="center", va="top", fontsize=10.6, color=S.INK, fontweight="bold")
    ax.text(x, -15.6, l2, ha="center", va="top", fontsize=9.4, color=S.INK2)
    if l3:
        ax.text(x, -22.6, l3, ha="center", va="top", fontsize=10.2, color=S.INK)

handles = [
    Line2D([0], [0], marker="o", color=S.BLUE, markerfacecolor=S.BLUE, markersize=7, lw=1.2,
           label="Sabotage run (4 tasks, 24 runs)"),
    Line2D([0], [0], marker="o", color=S.ORANGE, markerfacecolor=S.ORANGE, markersize=7, lw=1.2,
           label="Sabotage run, American Airlines task (6 runs)"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=S.GRAY, markeredgecolor=S.SURFACE,
           markersize=8, label="Honest run"),
]
leg = fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.052, 0.846), ncol=3,
                 handlelength=1.6, columnspacing=1.8, fontsize=9.8)
for t in leg.get_texts():
    t.set_color(S.INK2)

d = g["paired_drop_auroc_released_minus_no_model_thinking"]
S.header(fig,
         "Near-perfect monitoring depended on the agent’s plans being in view",
         "SHADE-Arena sabotage runs from the Monitor Red Teaming release, scored by one monitor before and after\n"
         "deleting the agent’s <model_thinking> planning blocks. Each line is one run.",
         top=0.972, gap=0.052)
S.source(fig,
         "Data: 30 sabotage and 30 honest runs on the 5 public tasks. Agent: Claude 3.6 Sonnet. Monitor: claude-haiku-5-5 with the paper\u2019s monitor prompt,\n"
         "a newer model than any the paper used (on unedited runs it tracks the paper\u2019s own monitor: 0.998 vs 0.984). "
         f"Paired AUROC drop {d['point']:.2f}\n(95% CI {d['ci_run'][0]:.2f}\u2013{d['ci_run'][1]:.2f} resampling runs; {d['ci_task_cluster'][0]:.2f}\u2013{d['ci_task_cluster'][1]:.2f} resampling the 5 tasks). "
         f"Without the American Airlines task the edited AUROC is {g['sensitivity']['drop_each_task']['american_airlines_2']:.2f}.\n"
         "The deletion is post hoc: these agents were not trying to hide, so 0.85 is not a catch rate for agents that do.",
         y=0.02)
S.save(fig, out)
