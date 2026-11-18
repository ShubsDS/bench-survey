"""Digitise the critic's Figure 2 (accuracy vs ECI, four panels) by marker colour.

Reads data/figs/critic_fig2.png (sha256 e98a5f8d...). Every value produced here is READ FROM A
CHART, not from data: precision is about +-0.5 accuracy points and +-0.2 ECI. Axis calibration is
from gridlines found in the image (see the constants below; found by scanning for gridline pixels).

Output: results/critic_fig2_digitised.json with, per panel, a list of markers
{colour_class, eci, acc, area_px}.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent.parent
FIG = HERE / "data/figs/critic_fig2.png"

# Calibration (original pixel coordinates of the 2280x2660 image).
# x gridlines: 140 -> 1265, 150 -> 1527, 160 -> 1789, 170 -> 2051 in the right-hand panels.
# Left panels share the same y axis; their x gridlines are found the same way below.
# y gridlines (top panels): 80 -> 722, 70 -> 822, 60 -> 922, 50 -> 1021.5, 20 -> 1322.


def find_grid(im, x0, x1, y0, y1):
    sub = im[y0:y1, x0:x1]
    g = (abs(sub[:, :, 0] - sub[:, :, 1]) < 4) & (sub[:, :, 0] > 200) & (sub[:, :, 0] < 245)
    cols = g.sum(0)
    xs = [i + x0 for i, c in enumerate(cols) if c > 0.6 * (y1 - y0)]
    rows = g.sum(1)
    ys = [i + y0 for i, c in enumerate(rows) if c > 0.9 * (x1 - x0)]
    def centres(v):
        out, cur = [], []
        for p in v:
            if cur and p - cur[-1] > 2:
                out.append(sum(cur) / len(cur)); cur = []
            cur.append(p)
        if cur:
            out.append(sum(cur) / len(cur))
        return out
    return centres(xs), centres(ys)


def classify(px):
    r, g, b = px[..., 0], px[..., 1], px[..., 2]
    blue = (b > 170) & (r < 90) & (g > 90) & (g < 160)
    orange = (r > 200) & (g > 70) & (g < 130) & (b < 90)
    green = (g > 140) & (r < 80) & (b > 90) & (b < 150)
    return {"anthropic_blue": blue, "openai_orange": orange, "other_green": green}


def digitise(im, box, xticks, y80):
    x0, x1, y0, y1 = box
    xs, ys = find_grid(im, x0, x1, y0, y1)
    # x: linear fit of the four vertical gridlines (140..170). y: the shaded chance band adds
    # spurious grey rows, so y uses the fixed calibration y = 80 - (py - y80) / 10, checked
    # against the 80/70/50/20 gridlines (top panels 722/822/1021.5/1322; bottom 1730/1830/2030/2330).
    fx = np.polyfit(xs[: len(xticks)], xticks[: len(xs)], 1)
    fy = np.array([-0.1, 80 + y80 / 10.0])
    sub = im[y0:y1, x0:x1]
    out = []
    for cls, mask in classify(sub).items():
        lab, n = ndimage.label(mask)
        for k in range(1, n + 1):
            yy, xx = np.nonzero(lab == k)
            if len(yy) < 60:  # legend fragments, text and anti-aliasing
                continue
            cx, cy = xx.mean() + x0, yy.mean() + y0
            out.append({"class": cls, "eci": round(float(np.polyval(fx, cx)), 2),
                        "acc": round(float(np.polyval(fy, cy)), 1), "area_px": int(len(yy))})
    return sorted(out, key=lambda d: d["eci"]), xs, ys


def main():
    im = np.array(Image.open(FIG).convert("RGB")).astype(int)
    res = {}
    # Panels: (name, box x0,x1,y0,y1). Found by inspection of the image layout.
    panels = {
        "rubric_40_decided": (190, 1170, 700, 1345),
        "rubric_52_ties": (1255, 2240, 700, 1345),
        "past_40_decided": (190, 1170, 1700, 2350),
        "past_52_ties": (1255, 2240, 1700, 2350),
    }
    for name, box in panels.items():
        x0, x1, y0, y1 = box
        xs, ys = find_grid(im, x0, x1, y0, y1)
        # x ticks 140..170 by 10; y gridlines run 80 (top) .. 20 (bottom) by 10
        xt = [140 + 10 * i for i in range(len(xs))]
        y80 = 722 if name.startswith("rubric") else 1730
        markers, _, _ = digitise(im, box, xt, y80)
        res[name] = {"x_gridlines_px": xs, "y_gridlines_px": ys, "markers": markers}
    out = HERE / "results/critic_fig2_digitised.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(res, indent=1))
    for name, r in res.items():
        print(name, "gridx", [round(v) for v in r["x_gridlines_px"]], "gridy", [round(v) for v in r["y_gridlines_px"]])
        for m in r["markers"]:
            print("   ", m)


if __name__ == "__main__":
    sys.exit(main())
