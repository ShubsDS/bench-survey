"""Read SWE-bench Verified x-values from figures/taste_vs_swebench.pdf vector data.

Parses decompressed content streams as text (no downloaded code runs). Marker circles are
found as a move-to followed by Bezier segments; their centres are mapped to data units with the
gridlines (vertical gridlines every 5 points from 65; horizontal every 5 points, 60 at y=84.1)
and checked against the known Taste-Bench Averages. Output: results/swebench_from_figure.json.
Values are "read from figure" and carry roughly +-0.1 point of reading error.
"""
import json
import re
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data/paper/src/figures/taste_vs_swebench.pdf"

AVERAGES = {  # README leaderboard, the 11 models in the comparison
    "gpt-5.6-sol": 59.7, "gpt-5.5": 59.5, "claude-opus-5": 55.5, "grok-4.5": 54.6,
    "gpt-5.6-terra": 54.0, "glm-5.2": 53.9, "claude-sonnet-5": 51.6, "gpt-5.6-luna": 49.0,
    "minimax-m3": 45.3, "deepseek-v4-flash": 43.3, "mistral-medium-3.5": 37.7,
}


def streams(raw: bytes):
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S):
        try:
            yield zlib.decompress(m.group(1)).decode("latin1")
        except Exception:
            continue


def circles(text: str):
    lines = text.split("\n")
    found = set()
    for i, line in enumerate(lines[:-2]):
        if re.match(r"^[\d.]+ [\d.]+ m$", line) and lines[i + 1].endswith(" c") and lines[i + 2].endswith(" c"):
            pts, j = [], i + 1
            while j < len(lines) and lines[j].endswith(" c"):
                v = lines[j].split()
                pts.append((float(v[4]), float(v[5])))
                j += 1
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            if len(pts) >= 30:
                found.add((round((max(xs) + min(xs)) / 2, 2), round((max(ys) + min(ys)) / 2, 2),
                           round((max(xs) - min(xs)) / 2, 2)))
    return sorted(found, key=lambda c: c[1])


def main():
    text = max(streams(PDF.read_bytes()), key=len)
    cs = circles(text)
    # gridlines: vertical at x = 112.4 + 57.4 k (65, 70, ...), horizontal y = 84.1 (60) step 72.7
    x_of = lambda sx: 65 + (sx - 112.4) / 57.4 * 5
    y_of = lambda sy: 60 - (sy - 84.1) / 72.7 * 5
    models = sorted(AVERAGES, key=lambda m: -AVERAGES[m])
    if len(cs) != len(models):
        sys.exit(f"expected {len(models)} markers, found {len(cs)}")
    out, worst = {}, 0.0
    for model, (sx, sy, r) in zip(models, cs):
        y = y_of(sy)
        worst = max(worst, abs(y - AVERAGES[model]))
        out[model] = {"swebench_verified": round(x_of(sx), 2), "average_from_figure": round(y, 2),
                      "highlighted": r > 6}
    out["_check_max_abs_average_error"] = round(worst, 3)
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results/swebench_from_figure.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
