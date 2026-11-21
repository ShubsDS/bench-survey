"""Shared chart style: the clean research-post look common on LessWrong / Alignment Forum.

White surface, sans type, a takeaway headline with a plain subtitle, hairline grid,
direct labels, 95% intervals, and a source line. One accent hue plus gray wherever the
story is a single contrast.
"""
import matplotlib as mpl
import matplotlib.pyplot as plt

SURFACE = "#ffffff"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
GRAY = "#b9b8b1"      # de-emphasis fill
GRAY_LIGHT = "#dddcd5"
BLUE_LIGHT = "#9ec5f4"

FONT = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]


def apply():
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": FONT,
        "font.size": 11,
        "text.color": INK,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK2,
        "axes.labelsize": 10.5,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.facecolor": SURFACE,
        "axes.axisbelow": True,
        "axes.grid": False,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK2,
        "ytick.labelcolor": INK2,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "xtick.major.pad": 6,
        "ytick.major.pad": 6,
        "figure.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "legend.frameon": False,
        "legend.fontsize": 10,
        "svg.fonttype": "none",
    })


def header(fig, title, subtitle, left=0.06, top=0.965, title_size=16.5, sub_size=11.5, gap=0.052):
    """Takeaway headline + plain subtitle, left-aligned to the figure edge."""
    fig.text(left, top, title, ha="left", va="top", fontsize=title_size,
             fontweight="bold", color=INK, linespacing=1.15)
    n_title_lines = title.count("\n") + 1
    y = top - gap * n_title_lines - 0.012
    fig.text(left, y, subtitle, ha="left", va="top", fontsize=sub_size, color=INK2,
             linespacing=1.35)


def source(fig, text, left=0.06, y=0.022, size=8.6):
    fig.text(left, y, text, ha="left", va="bottom", fontsize=size, color=MUTED, linespacing=1.4)


def save(fig, stem):
    fig.savefig(f"{stem}.png", dpi=220)
    fig.savefig(f"{stem}.svg")
    plt.close(fig)
