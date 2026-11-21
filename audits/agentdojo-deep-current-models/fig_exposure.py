"""Figure: how often each model was shown the injected text, on the same sampled cases.

Run:  python fig_exposure.py     (needs matplotlib; style from ../../factcheck/charts/lw_style.py)
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
NAMES = {
    "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet (Oct 2024)", "command-r": "Command-R",
    "gemini-1.5-flash-002": "Gemini 1.5 Flash 002", "command-r-plus": "Command-R+",
    "claude-3-7-sonnet-20250219": "Claude 3.7 Sonnet", "claude-3-haiku-20240307": "Claude 3 Haiku",
    "gpt-3.5-turbo-0125": "GPT-3.5 Turbo", "claude-3-opus-20240229": "Claude 3 Opus",
    "gemini-1.5-flash-001": "Gemini 1.5 Flash 001", "gemini-1.5-pro-002": "Gemini 1.5 Pro 002",
    "gemini-2.0-flash-exp": "Gemini 2.0 Flash (exp)", "gemini-2.0-flash-001": "Gemini 2.0 Flash 001",
    "meta-llama_Llama-3-70b-chat-hf": "Llama 3 70B", "claude-3-sonnet-20240229": "Claude 3 Sonnet",
    "gpt-4o-mini-2024-07-18": "GPT-4o mini", "gpt-4-turbo-2024-04-09": "GPT-4 Turbo",
    "gemini-1.5-pro-001": "Gemini 1.5 Pro 001", "claude-3-5-sonnet-20240620": "Claude 3.5 Sonnet (Jun 2024)",
    "gpt-4o-2024-05-13": "GPT-4o", "gpt-4-0125-preview": "GPT-4 (0125)",
}
NEW = {"claude-haiku-5-5": "Claude Haiku 5.5", "claude-sonnet-5-5": "Claude Sonnet 5.5"}

rows = []
for m, name in NEW.items():
    r = res["models"][m]
    rows.append({"name": name, "x": r["weighted"]["exposure"], "ci": r["ci95_weighted"]["exposure"], "new": True,
                 "n": r["n_attack_runs"]})
for m, c in res["older_on_same_cases"]["claude-haiku-5-5"].items():
    rows.append({"name": NAMES[m], "x": c["exposure"], "ci": None, "new": False, "n": c["n"]})
rows.sort(key=lambda r: (r["x"], r["new"]))
n = len(rows)

fig = plt.figure(figsize=(9.6, 9.4))
ax = fig.add_axes([0.335, 0.165, 0.60, 0.635])
for i, r in enumerate(rows):
    y = i
    x = r["x"] * 100
    ax.plot([50, x], [y, y], color=S.GRID, lw=0.8, zorder=1)
    if r["new"]:
        lo, hi = r["ci"]
        if hi - lo > 0.002:
            ax.plot([lo * 100, hi * 100], [y, y], color=S.BLUE, lw=2.0, alpha=0.35, zorder=2, solid_capstyle="round")
        ax.scatter(x, y, s=74, color=S.BLUE, edgecolor=S.SURFACE, linewidth=1.2, zorder=4)
    else:
        ax.scatter(x, y, s=52, color=S.GRAY, edgecolor=S.SURFACE, linewidth=1.0, zorder=3)
    ax.text(49.2, y, r["name"], ha="right", va="center", fontsize=10.2, color=S.INK,
            fontweight="bold" if r["new"] else "normal")
    ax.text(101.6, y, f"{x:.0f}%", ha="left", va="center", fontsize=9.8, color=S.INK if r["new"] else S.INK2,
            fontweight="bold" if r["new"] else "normal")

ax.set_xlim(50, 100.6)
ax.set_ylim(-0.8, n - 0.3)
ax.set_yticks([])
ax.set_xticks([50, 60, 70, 80, 90, 100])
ax.set_xticklabels(["50%", "60%", "70%", "80%", "90%", "100%"])
ax.xaxis.grid(True)
ax.spines["left"].set_visible(False)
ax.spines["bottom"].set_visible(False)
ax.set_xlabel("Attack runs in which the agent was shown the injected text", labelpad=8)

handles = [
    Line2D([0], [0], marker="o", color=S.BLUE, markerfacecolor=S.BLUE, markeredgecolor=S.SURFACE, markersize=9,
           lw=2.0, label="Current models, run for this audit (95% interval)"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=S.GRAY, markeredgecolor=S.SURFACE, markersize=8,
           label="20 models in AgentDojo's released logs (2024 to February 2025)"),
]
leg = fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.052, 0.868), ncol=1, handlelength=1.8, fontsize=9.8)
for t in leg.get_texts():
    t.set_color(S.INK2)

hk, sn = res["models"]["claude-haiku-5-5"], res["models"]["claude-sonnet-5-5"]
S.header(fig,
         "Two current Claude models read the planted text almost every time",
         "AgentDojo plants an attacker's instruction in a tool result. A run where the agent never reads that result\n"
         "is scored secure without testing anything. For older models that was common; for these two it is rare.",
         top=0.972, gap=0.046)
S.source(fig,
         f"AgentDojo v1.1.2, important_instructions attack, {hk['n_attack_runs']} sampled cases (two injection tasks per user task; Sonnet 5.5 completed {sn['n_attack_runs']}).\n"
         "Older models: the benchmark's released logs on the same cases. Current models were run through a text-only harness (AgentDojo's text\n"
         "tool-calling format, not native tool calls), so their attack success and utility are not comparable with the published table.\n"
         f"AgentDojo scored {hk['n_attack_runs'] - hk['n_secure'] + sn['n_attack_runs'] - sn['n_secure']} of {hk['n_attack_runs'] + sn['n_attack_runs']} current-model runs as successful attacks; in all of them the agent was warning the user about the planted text.",
         y=0.018)
S.save(fig, str(HERE / "fig_exposure"))
