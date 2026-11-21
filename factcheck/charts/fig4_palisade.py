import json, sys
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import lw_style as S

S.apply()
g = json.load(open(sys.argv[1]))
out = sys.argv[2]

may = g["a_may_headline"]
o3, cm = may["o3|none"], may["codex-mini-latest|none"]
ov = g["b_stated_reasons_paper_bypassed_sample"]["overall"]
c = ov["counts"]
N = ov["n"]
cells = g["c_sabotage_rates_paper_cells"]

fig = plt.figure(figsize=(9.6, 6.5))

# ---------- left: re-scoring ----------
axL = fig.add_axes([0.150, 0.300, 0.250, 0.375])
rows = [("o3", o3), ("codex-mini", cm)]
for i, (name, r) in enumerate(rows):
    y = len(rows) - 1 - i
    lo, hi = r["behavioural_ci"]
    axL.plot([lo, hi], [y, y], color=S.BLUE, lw=2.0, alpha=0.35, zorder=2, solid_capstyle="round")
    axL.plot([r["palisade_count"], r["behavioural_count"]], [y, y], color=S.AXIS, lw=1.6, zorder=3)
    axL.scatter(r["palisade_count"], y, s=62, facecolor=S.SURFACE, edgecolor=S.MUTED, linewidth=1.6, zorder=4)
    axL.scatter(r["behavioural_count"], y, s=70, color=S.BLUE, edgecolor=S.SURFACE, linewidth=1.4, zorder=5)
    axL.text(r["palisade_count"], y - 0.2, f"{r['palisade_count']}", ha="center", va="top",
             fontsize=9.6, color=S.INK2)
    axL.text(r["behavioural_count"], y + 0.2, f"{r['behavioural_count']}", ha="center", va="bottom",
             fontsize=9.6, color=S.INK, fontweight="bold")
    axL.text(-6, y, name, ha="right", va="center", fontsize=10.4, color=S.INK)
axL.set_xlim(0, 100)
axL.set_ylim(-0.6, 1.75)
axL.set_yticks([])
axL.set_xticks([0, 25, 50, 75, 100])
axL.xaxis.grid(True)
axL.spines["left"].set_visible(False)
axL.spines["bottom"].set_visible(False)
axL.set_xlabel("Runs with the shutdown script\nsabotaged, of 100", labelpad=8, linespacing=1.3)

# ---------- right: stated reasons ----------
axR = fig.add_axes([0.640, 0.300, 0.300, 0.375])
bars = [
    ("Gives finishing the task\nas the reason", c["task_completion"], S.BLUE),
    ("States no reason", c["no_reason_stated"], S.GRAY),
    ("Other stated reason", c["other_stated_reason"], S.GRAY),
    ("Frames it as preserving itself", c["self_preservation_strict"], S.ORANGE),
]
nb = len(bars)
for i, (name, val, col) in enumerate(bars):
    y = nb - 1 - i
    axR.barh(y, val, height=0.5, color=col, zorder=2)
    axR.text(val + 45, y, f"{val:,}", ha="left", va="center", fontsize=10.2, color=S.INK,
             fontweight="bold" if col == S.ORANGE else "normal")
    axR.text(-70, y, name, ha="right", va="center", fontsize=10.2, color=S.INK, linespacing=1.2)
axR.set_xlim(0, 2500)
axR.set_ylim(-0.6, nb - 0.4)
axR.set_yticks([])
axR.set_xticks([0, 1000, 2000])
axR.set_xticklabels(["0", "1,000", "2,000"])
axR.xaxis.grid(True)
axR.spines["left"].set_visible(False)
axR.spines["bottom"].set_visible(False)
axR.set_xlabel(f"Sabotaging runs, of {N:,} sampled", labelpad=8)

# panel headings
fig.text(0.06, 0.745, "The sabotage survives re-scoring", fontsize=11.6, fontweight="bold", color=S.INK, va="bottom")
fig.text(0.06, 0.712, "May 2025 runs, no instruction to allow shutdown", fontsize=9.6, color=S.INK2, va="bottom")
fig.text(0.47, 0.745, "What sabotaging runs say about why", fontsize=11.6, fontweight="bold", color=S.INK, va="bottom")
fig.text(0.47, 0.712, "Later, larger experiments; text logged with each command", fontsize=9.6, color=S.INK2, va="bottom")

handles = [
    Line2D([0], [0], marker="o", color="none", markerfacecolor=S.SURFACE, markeredgecolor=S.MUTED,
           markeredgewidth=1.6, markersize=8, label="Palisade’s score"),
    Line2D([0], [0], marker="o", color=S.BLUE, markerfacecolor=S.BLUE, markeredgecolor=S.SURFACE,
           markersize=8.5, lw=2.0, label="Scored by behaviour (95% CI)"),
]
leg = fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.052, 0.708), ncol=1,
                 handlelength=1.8, labelspacing=0.35, fontsize=9.4)
for t in leg.get_texts():
    t.set_color(S.INK2)
axL.set_position([0.150, 0.300, 0.250, 0.300])

e, j = cells["openai/o3"]["E"]["rate_pct"], cells["openai/o3"]["J"]["rate_pct"]
S.header(fig,
         "Shutdown sabotage is real. The self-preservation reading is not in the transcripts.",
         "Re-scoring Palisade’s released logs by what the agent did finds slightly more sabotage than reported. Almost no\n"
         "sabotaging run describes the act as preserving itself.",
         top=0.972, gap=0.056, title_size=15.2)
S.source(fig,
         "Data: Palisade Research released logs. Left: May 2025 release. Right: sample of up to 100 sabotaging runs per condition from the 2025 paper’s experiments;\n"
         "93% are codex-mini, o4-mini, Grok 4 and o3, and OpenAI models log no reasoning. Reasons are classified by rule; a hand-read of 60 runs puts “finishing the\n"
         f"task” nearer a third. Both self-preservation runs are Grok 4 under a prompt saying it would never run again; that prompt also raised sabotage (o3: {e:.0f}% to {j:.0f}%),\n"
         "so stated reasons do not settle motive. Palisade’s paper itself attributes the behaviour mainly to unfinished tasks.",
         y=0.02)
S.save(fig, out)
