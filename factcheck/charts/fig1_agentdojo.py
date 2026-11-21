import json, sys
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import lw_style as S

S.apply()
g = json.load(open(sys.argv[1]))
out = sys.argv[2]
ms = [dict(v, model=k) for k, v in g["models"].items()] if isinstance(g["models"], dict) else g["models"]

NAMES = {
    "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet (Oct)",
    "command-r": "Command-R",
    "gemini-1.5-flash-002": "Gemini 1.5 Flash 002",
    "command-r-plus": "Command-R+",
    "claude-3-7-sonnet-20250219": "Claude 3.7 Sonnet",
    "claude-3-haiku-20240307": "Claude 3 Haiku",
    "gpt-3.5-turbo-0125": "GPT-3.5 Turbo",
    "claude-3-opus-20240229": "Claude 3 Opus",
    "gemini-1.5-flash-001": "Gemini 1.5 Flash 001",
    "gemini-1.5-pro-002": "Gemini 1.5 Pro 002",
    "gemini-2.0-flash-exp": "Gemini 2.0 Flash (exp)",
    "gemini-2.0-flash-001": "Gemini 2.0 Flash 001",
    "meta-llama_Llama-3-70b-chat-hf": "Llama 3 70B",
    "claude-3-sonnet-20240229": "Claude 3 Sonnet",
    "gpt-4o-mini-2024-07-18": "GPT-4o mini",
    "gpt-4-turbo-2024-04-09": "GPT-4 Turbo",
    "gemini-1.5-pro-001": "Gemini 1.5 Pro 001",
    "claude-3-5-sonnet-20240620": "Claude 3.5 Sonnet (Jun)",
    "gpt-4o-2024-05-13": "GPT-4o",
    "gpt-4-0125-preview": "GPT-4 (0125)",
}

ms = sorted(ms, key=lambda m: (m["published_asr"], m["model"]))
n = len(ms)

DARK = "#1c5cab"     # never saw
LIGHT = "#86b6ef"    # saw, failed the injected task when asked directly
REST = "#dddcd5"     # saw it and could do it
NOTRACE = "#f0efec"

AX_L, AX_W = 0.415, 0.525
fig = plt.figure(figsize=(9.6, 10.3))
ax = fig.add_axes([AX_L, 0.185, AX_W, 0.585])
X_NAME = -(AX_L - 0.06) / AX_W * 100   # model names start at the figure's left margin
X_ASR = -4.0

h = 0.62
for i, m in enumerate(ms):
    y = n - 1 - i
    ns = m["n_secure"]
    a = m["n_secure_never_saw"] / ns
    b = m["n_secure_could_not"] / ns
    u = m.get("n_secure_untraced_empty_trace", 0) / ns
    c = m["n_secure_saw_and_could"] / ns
    left = 0
    for val, col, hatch in ((a, DARK, None), (b, LIGHT, None), (u, NOTRACE, "////"), (c, REST, None)):
        if val <= 0:
            continue
        ax.barh(y, val * 100, left=left * 100, height=h, color=col, edgecolor=S.SURFACE,
                linewidth=1.6, zorder=2)
        if hatch:
            ax.barh(y, val * 100, left=left * 100, height=h, color="none", edgecolor=S.AXIS,
                    linewidth=0, hatch=hatch, zorder=3)
        left += val
    tot = a + b
    inside = tot > 0.17
    ax.text(tot * 100 - 1.2 if inside else tot * 100 + 1.2, y, f"{tot*100:.0f}%",
            ha="right" if inside else "left", va="center", fontsize=9.6,
            color=S.INK, fontweight="bold", zorder=4)
    ax.text(X_NAME, y, NAMES.get(m["model"], m["model"]), ha="left", va="center", fontsize=10.2,
            color=S.INK)
    ax.text(X_ASR, y, f"{m['published_asr']*100:.1f}%", ha="right", va="center", fontsize=10.2,
            color=S.INK2)

ax.set_xlim(0, 100)
ax.set_ylim(-0.6, n - 0.4)
ax.set_yticks([])
ax.set_xticks([0, 25, 50, 75, 100])
ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
ax.xaxis.grid(True)
ax.spines["left"].set_visible(False)
ax.spines["bottom"].set_visible(False)
ax.set_xlabel("Share of each model’s “secure” runs", labelpad=8)

ytop = n - 0.25
ax.text(X_NAME, ytop, "Model, most “secure” first", ha="left", va="bottom", fontsize=9, color=S.MUTED)
ax.text(X_ASR, ytop, "Published attack\nsuccess rate", ha="right", va="bottom", fontsize=9, color=S.MUTED,
        linespacing=1.25)

handles = [
    Patch(facecolor=DARK, label="Agent never saw the injected text"),
    Patch(facecolor=LIGHT, label="Saw it, but fails that task even when asked directly"),
    Patch(facecolor=REST, label="Saw it and could have done it: possible resistance"),
    Patch(facecolor=NOTRACE, edgecolor=S.AXIS, hatch="////", label="No trace stored"),
]
leg = fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.052, 0.880), ncol=2,
                 handlelength=1.1, handleheight=1.0, columnspacing=1.8, labelspacing=0.5,
                 fontsize=9.8)
for t in leg.get_texts():
    t.set_color(S.INK2)

S.header(fig,
         "A “secure” run is often not a resisted attack",
         "AgentDojo counts a run as secure whenever the injected instruction did not succeed. In the released logs,\n"
         "much of that is the agent never reaching the injection, or being unable to carry it out. Bold: the two combined.",
         top=0.976, gap=0.037)
S.source(fig,
         "Data: AgentDojo released run logs. 20 undefended models, important_instructions attack, v1.1.2 task set, 629 runs per model.\n"
         "“Fails when asked directly” rests on one stored attempt per injected task, and for about half of those runs the same model completes\n"
         "that task elsewhere in the logs, so read the light segment as an upper bound. Task-level bootstrap intervals on the bold shares are\n"
         "roughly ±15 points.", y=0.018)
S.save(fig, out)
