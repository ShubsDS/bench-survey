"""Reproduce the ControlArena apps join bug: zero-padded source ids never match APPS ids.

ControlArena's build (control_arena/settings/apps/dataset/upload_dataset.py) keys the backdoors in
TylordTheGreat/apps-backdoors-04-02-25 by str(problem_id) and looks each codeparrot/apps problem
up by str(problem_id). The source pads ids to four characters ('0001'); APPS does not ('1'), so
only ids of 1,000 or more can join. This script downloads the three inputs at pinned revisions and
reports what the join drops, what the published dataset shows, and whether the dropped backdoors
belong to the problems they would have joined (token overlap with that problem's human
solutions). It reads code as text and never runs it.

Usage:
    python check_join.py [--cache DIR] [--out join_result.json]
"""
import argparse, collections, json, random, re, statistics, urllib.request
from pathlib import Path

import pandas as pd

CONTROL_ARENA = "ae0b6fa78ace5a097536eb3464ab5a089740b53e"
BUILD = ("https://raw.githubusercontent.com/UKGovernmentBEIS/control-arena/"
         f"{CONTROL_ARENA}/control_arena/settings/apps/dataset/upload_dataset.py")
SOURCE = ("https://huggingface.co/datasets/TylordTheGreat/apps-backdoors-04-02-25/resolve/"
          "22ca28e1e0fbc65c5de58a45e7f7023dee9aba2f/backdoor_dataset.json")
PUBLISHED = [("https://huggingface.co/datasets/RoganInglis/apps-control-arena/resolve/"
              f"29db28f76042952d56add8671f798280b200744d/data/train-0000{i}-of-00003.parquet")
             for i in range(3)]


def fetch(url, cache):
    path = cache / url.rsplit("/", 1)[1]
    if not path.exists():
        with urllib.request.urlopen(url, timeout=300) as r:
            path.write_bytes(r.read())
    return path


def tokens(code):
    return set(re.findall(r"[A-Za-z_]\w+|\d+|\S", code))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="join_result.json")
    args = ap.parse_args()
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)

    # 1. The build keys both sides by str(problem_id).
    build = fetch(BUILD, cache).read_text()
    keyed = [ln.strip() for ln in build.splitlines()
             if "str(problem_id)" in ln and ("backdoors[" in ln or ".get(" in ln)]

    # 2. The join as the build does it.
    rows = json.loads(fetch(SOURCE, cache).read_text())
    rows = [r for r in rows if r.get("problem_id") and r.get("code") and r.get("backdoor_input")]
    src = collections.defaultdict(list)
    for r in rows:
        src[str(r["problem_id"])].append(r)
    df = pd.concat([pd.read_parquet(fetch(u, cache)) for u in PUBLISHED])
    df.index = df.problem_id.astype(str)
    apps_ids = set(df.index)
    lost = sorted(k for k in src if k not in apps_ids)
    kept = sorted(k for k in src if k in apps_ids)
    lost_apps = [str(int(k)) for k in lost]

    # 3. Do the dropped backdoors belong to the problems they would have joined? Compare each
    # problem's first backdoor with its own human solutions and with a random problem's.
    random.seed(0)
    sols = {k: [tokens(s["code"]) for s in list(v)[:20]] for k, v in df.solutions.items()}
    pool = [k for k in df.index if int(k) < 3000 and sols[k]]
    sim = lambda b, k: max((len(b & s) / len(b | s) for s in sols[k]), default=0.0)
    belong = {}
    for name, ids in (("dropped", lost), ("joined", kept)):
        own_wins, own, rnd = 0, [], []
        for k in ids:
            target = str(int(k))
            if not sols[target]:
                continue
            b = tokens(src[k][0]["code"])
            a, c = sim(b, target), sim(b, random.choice(pool))
            own.append(a); rnd.append(c); own_wins += a > c
        belong[name] = {"n": len(own), "closer_to_own_problem": own_wins,
                        "median_jaccard_own": round(statistics.median(own), 3),
                        "median_jaccard_random": round(statistics.median(rnd), 3)}

    pid = df.problem_id.astype(int)
    flagged = df.has_apps_backdoor.astype(bool)
    result = {
        "pins": {"control_arena": CONTROL_ARENA, "source": SOURCE, "published": PUBLISHED},
        "build_lines_keying_by_str_problem_id": keyed,
        "source_id_lengths": dict(collections.Counter(len(k) for k in src)),
        "source_problems": len(src), "source_backdoors": len(rows),
        "problems_dropped": len(lost), "backdoors_dropped": sum(len(src[k]) for k in lost),
        "dropped_all_below_1000": all(int(k) < 1000 for k in lost),
        "dropped_would_match_after_int": sum(str(int(k)) in apps_ids for k in lost),
        "dropped_difficulty": dict(collections.Counter(df.loc[lost_apps, "difficulty"])),
        "dropped_with_other_backdoor": int(df.loc[lost_apps, "has_backdoor"].astype(bool).sum()),
        "published_has_apps_backdoor": int(flagged.sum()),
        "published_has_apps_backdoor_min_id": int(pid[flagged].min()),
        "token_overlap_check": belong,
    }
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
