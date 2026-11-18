"""Parse the paper's main table (Table tab:propensity-main, tabs/tab-propensiy-main.tex of arXiv 2511.20703v1
source, sha256 95d3ade1…) into published_numbers.json, and add the leaderboard values read on
2026-11-17 from labs.scale.com/leaderboard/propensitybench (typed in from the page; 14 models)."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import AUDIT, DATA

LEADERBOARD = {  # as displayed, "score ± error"
    "o3-2025-04-16": 10.50, "claude-sonnet-4-20250514": 12.20, "o4-mini-2025-04-16": 15.80, "Qwen2.5-32B": 22.90,
    "o3-mini-2025-01-31": 33.20, "gpt-5.2-2025-12-11": 34.35, "gpt-4o-2024-11-20": 46.10,
    "gemini-3-pro-preview": 52.85, "Llama-3.1-70B": 55.40, "Llama-3.1-8B": 66.50, "gemini-2.5-flash": 68.00,
    "Qwen3-8B": 75.20, "gemini-2.0-flash": 77.80, "gemini-2.5-pro": 79.00}


def main():
    tex = (DATA / "paper" / "x" / "propensity_eval" / "tabs" / "tab-propensiy-main.tex").read_text()
    live = "\n".join(l for l in tex.splitlines() if not l.lstrip().startswith("%"))
    body = live.split(r"\label{tab:propensity-main}", 1)[1].split(r"\end{tabular}", 1)[0]
    rows = {}
    for line in body.splitlines():
        if line.lstrip().startswith("%") or "&" not in line or "textbf{Model}" in line:
            continue
        cells = [re.sub(r"\\(lowerbnd|upperbnd)\{([^}]*)\}", r"\2", c).strip() for c in line.split("&")]
        name = cells[0]
        if not name or name.startswith("\\textbf") and "Average" not in name or name.startswith("&"):
            continue
        nums = [re.findall(r"[-+]?\d+\.\d+", c) for c in cells[1:]]
        flat = [float(x[0]) if x else None for x in nums]
        if len(flat) >= 10:
            rows[re.sub(r"\\textbf\{|\}", "", name)] = dict(zip(
                ["PP_zero", "PP_H", "PP_B", "dPP", "R_H", "R_B", "P_H", "P_B", "A_H", "A_B"], flat[:10]))
    out = {"source": "arXiv 2511.20703v1, Table tab:propensity-main", "table": rows, "leaderboard_2026_11_17": LEADERBOARD}
    (AUDIT / "published_numbers.json").write_text(json.dumps(out, indent=1) + "\n")
    for k, v in rows.items():
        print(k, v["PP_zero"], v["PP_H"], v["PP_B"], v["dPP"])


if __name__ == "__main__":
    main()
