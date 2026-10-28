"""Check 5 on MACHIAVELLI: duplicate scenes across games, and which games were used to develop or
tune the agents that are then scored on the 30 test games.

Duplicates. Scene text (whitespace-normalised, lower-cased) from scenarios/*_filled.json for every
game with clean labels. (a) Identical scenes of >= 50 and >= 200 characters shared by two or more
games. (b) Sentence overlap: per game, the set of sentences of >= 60 characters; for each test
game, the share of its sentences found in any other game, and the game pairs sharing the most.
Only counts and game names are written; no text.

Development and tuning (read from the pinned code and paper as text):
  experiments/baselines_lm.sh   LM agent game loops, including commented-out development lists
  machiavelli/agent/game2beta.json   per-game DRRN exploration beta
  paper Section 2 "Test set" and Appendix rl_training

Usage: python -I check_overlap.py --cache ../data --out overlap_checks.json
"""
import argparse, collections, hashlib, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ensure, game_lists, gd, norm_text, repo, scenarios

SENT = re.compile(r"(?<=[.!?\"])\s+")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="../data")
    ap.add_argument("--out", default="overlap_checks.json")
    a = ap.parse_args()
    pins = ensure(a.cache)
    L = game_lists(a.cache)
    test = set(L["test"])
    games = [g for g in L["working"] if (gd(a.cache) / "annotations_clean" / f"{g}.json").exists()]
    scene_hash = {50: collections.defaultdict(set), 200: collections.defaultdict(set)}
    sents = {}
    for g in games:
        ss = set()
        for s, txt in scenarios(a.cache, g).items():
            t = norm_text(txt)
            h = hashlib.sha1(t.encode()).hexdigest()
            for m in scene_hash:
                if len(t) >= m:
                    scene_hash[m][h].add(g)
            for x in SENT.split(t):
                if len(x) >= 60:
                    ss.add(hashlib.sha1(x.encode()).hexdigest())
        sents[g] = ss
    res = {"pins": pins, "games": len(games)}
    for m, d in scene_hash.items():
        multi = {h: gs for h, gs in d.items() if len(gs) > 1}
        pairs = collections.Counter()
        for gs in multi.values():
            gs = sorted(gs)
            for i in range(len(gs)):
                for j in range(i + 1, len(gs)):
                    pairs[(gs[i], gs[j])] += 1
        res[f"identical_scenes_min{m}"] = {
            "distinct_texts": len(d), "texts_in_2plus_games": len(multi),
            "spanning_test_and_nontest": sum(bool(gs & test) and bool(gs - test) for gs in multi.values()),
            "within_test_set": sum(len(gs & test) >= 2 for gs in multi.values()),
            "top_pairs": [[p[0], p[1], n] for p, n in pairs.most_common(8)]}
    # sentence overlap
    index = collections.defaultdict(set)
    for g, ss in sents.items():
        for h in ss:
            index[h].add(g)
    per_test = {}
    for g in sorted(test):
        ss = sents[g]
        shared_any = sum(len(index[h]) > 1 for h in ss)
        shared_nontest = sum(bool(index[h] - test) for h in ss)
        per_test[g] = {"sentences": len(ss), "share_in_any_other_game": round(shared_any / len(ss), 4),
                       "share_in_a_nontest_game": round(shared_nontest / len(ss), 4)}
    pairc = collections.Counter()
    for h, gs in index.items():
        if 1 < len(gs) <= 6:
            gs = sorted(gs)
            for i in range(len(gs)):
                for j in range(i + 1, len(gs)):
                    pairc[(gs[i], gs[j])] += 1
    res["sentence_overlap"] = {
        "min_chars": 60, "test_games_max_share_in_other_game": max(v["share_in_any_other_game"] for v in per_test.values()),
        "test_games_over_5pct": {g: v for g, v in per_test.items() if v["share_in_any_other_game"] > 0.05},
        "top_pairs": [[p[0], p[1], n, round(n / min(len(sents[p[0]]), len(sents[p[1]])), 3)] for p, n in pairc.most_common(10)]}
    # development / tuning
    R = repo(a.cache)
    sh = (R / "experiments" / "baselines_lm.sh").read_text()
    dev_lists = [re.findall(r"[a-z0-9_\-]+", l.split("in", 1)[1]) for l in sh.splitlines()
                 if l.strip().startswith("# for GAME in")]
    g2b = json.loads((R / "machiavelli" / "agent" / "game2beta.json").read_text())
    res["development"] = {
        "lm_commented_game_lists": [{"games": d, "test_games_in_it": sorted(set(d) & test)} for d in dev_lists],
        "lm_results_dir_name": "lm_dev (experiments/baselines_lm.sh EXP_NAME)",
        "drrn_beta_per_game_tuned": {"test_games_with_beta": len(set(g2b) & test), "of": len(test),
                                     "paper": "For each game, beta was tuned in [0.01 ... 5.0] (Appendix RL training)"},
        "drrn_trained_on": "each evaluation game itself (experiments/baselines_rl.sh loops games.txt; one model per game)",
        "test_set_rule_paper": "30 games where agents trained to maximize reward perform poorly on behavioral metrics, i.e. points and harms positively correlated",
        "test_set_selection_code": "not in the repo; the selection data (per-game points-harm correlations) are not released",
        "conscience_training_data": "ETHICS commonsense/utilitarianism csvs and GPT-generated power examples (experiments/conscience/utils.py); no game text"}
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "pins"}, indent=1))


if __name__ == "__main__":
    main()
