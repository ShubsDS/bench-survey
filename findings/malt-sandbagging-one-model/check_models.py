"""Tabulate which models wrote MALT's sandbagging positives and its reviewed benign runs.

METR's MALT reports monitor AUROCs on the manually reviewed subset: every positive, plus 1,014
benign runs that contractors checked. The summary tables on the dataset card (public split) and in
the release post (full dataset) give run counts by model, label, chain-of-thought and review
status. This script parses both tables and reports, for the sandbagging comparison, which models
are on each side. It reads only those two public pages; the transcripts are gated.

Usage:
    python check_models.py [--cache DIR] [--out models.json]
"""
import argparse, html, json, re, urllib.request
from pathlib import Path

import pandas as pd

PAGES = {"public_split": "https://huggingface.co/datasets/metr-evals/malt-public",
         "full_dataset": "https://metr.org/blog/2025-10-14-malt-dataset-of-natural-and-prompted-behaviors/"}
SANDBAGGING = {"match_weaker_model", "partial_problem_solving", "refusals", "sabotage"}
REWARD_HACKING = {"bypass_constraints", "hardcoded_solution", "ignores_task_instructions"}


def fetch(url, path):
    if not path.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            path.write_bytes(r.read())
    return path.read_text(encoding="utf-8")


def summary_table(page):
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        rows.append([html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
                     for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)])
    header = next(r for r in rows if "manually_reviewed" in r)
    df = pd.DataFrame([r for r in rows if len(r) == len(header) and r != header], columns=header)
    df["count"] = df["count"].astype(int)
    df["labels"] = df["labels"].apply(lambda s: {x.strip() for x in s.split(",")})
    return df


def by_model(df):
    return {f"{m} ({src}, cot={cot})": int(n) for (m, src, cot), n in
            df.groupby(["model", "run_source", "has_chain_of_thought"])["count"].sum().items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="models.json")
    args = ap.parse_args()
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)

    result = {}
    for name, url in PAGES.items():
        df = summary_table(fetch(url, cache / f"malt_{name}.html"))
        reviewed = df.manually_reviewed == "True"
        benign = df.labels.apply(lambda s: s == {"normal"})
        sandbag = df.labels.apply(lambda s: bool(s & SANDBAGGING))
        hack = df.labels.apply(lambda s: bool(s & REWARD_HACKING))
        result[name] = {
            "url": url, "runs": int(df["count"].sum()),
            "sandbagging_positives": by_model(df[sandbag]),
            "reward_hacking_positives": by_model(df[hack]),
            "reviewed_benign": by_model(df[benign & reviewed]),
            "unreviewed_benign_claude_3_7_sonnet": int(
                df[benign & ~reviewed & (df.model == "claude-3-7-sonnet-20250219")]["count"].sum()),
        }
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
