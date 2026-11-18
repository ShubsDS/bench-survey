"""Validator's independent re-digitisation of the critic's Figure 2 (rubric-only panels).

Reads data/figs/critic_fig2.png. Written without reading the auditor's digitiser output.
Method: gridlines found by scanning for neutral grey rows/columns; markers segmented by hue
(HSV) rather than RGB thresholds; component centroid = bounding-box centre of the coloured
mask (robust to the white outline being eaten by a neighbour); merged blobs flagged by area.
Every value is READ FROM A CHART.
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent.parent
im = np.array(Image.open(HERE / "data/figs/critic_fig2.png").convert("RGB")).astype(float)
r, g, b = im[..., 0], im[..., 1], im[..., 2]
mx, mn = im.max(-1), im.min(-1)
sat = (mx - mn) / np.maximum(mx, 1)
hue = np.zeros_like(mx)
d = np.maximum(mx - mn, 1e-9)
hue = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
colour = sat > 0.45
cls = {"blue": colour & (hue > 195) & (hue < 230),
       "green": colour & (hue > 140) & (hue < 175),
       "orange": colour & ((hue < 30) | (hue > 345))}

def grid(x0, x1, y0, y1):
    grey = (np.abs(r - g) < 6) & (np.abs(g - b) < 6) & (r > 215) & (r < 240)
    sub = grey[y0:y1, x0:x1]
    cols = np.where(sub.sum(0) > 0.5 * (y1 - y0))[0] + x0
    groups = np.split(cols, np.where(np.diff(cols) > 2)[0] + 1)
    return [float(gg.mean()) for gg in groups]

PANELS = {"rubric_40_decided": (150, 1180, 700, 1345), "rubric_52_ties": (1250, 2250, 700, 1345)}
out = {}
for name, (x0, x1, y0, y1) in PANELS.items():
    xs = grid(x0, x1, 660, 1360)
    fx = np.polyfit(xs, [140, 150, 160, 170][: len(xs)], 1)
    # y: 80 -> 722, 20 -> 1322 (gridline rows found at 722, 822, 922, 1122, 1222, 1322)
    fy = np.polyfit([722.0, 1322.0], [80.0, 20.0], 1)
    ms = []
    for c, mask in cls.items():
        lab, n = ndimage.label(mask[y0:y1, x0:x1])
        for k in range(1, n + 1):
            yy, xx = np.nonzero(lab == k)
            if len(yy) < 60:
                continue
            cx = (xx.min() + xx.max()) / 2 + x0
            cy = (yy.min() + yy.max()) / 2 + y0
            ms.append({"cls": c, "eci": round(float(np.polyval(fx, cx)), 2),
                       "acc": round(float(np.polyval(fy, cy)), 2), "area": int(len(yy)),
                       "w": int(xx.max() - xx.min() + 1), "h": int(yy.max() - yy.min() + 1)})
    out[name] = {"xgrid_px": xs, "markers": sorted(ms, key=lambda m: m["eci"])}
(HERE / "validation/redigitised_raw.json").write_text(json.dumps(out, indent=1))
for n, v in out.items():
    print(n, [round(x) for x in v["xgrid_px"]])
    for m in v["markers"]:
        print("  ", m)
