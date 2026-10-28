"""Repeated items across MASK archetypes (check 5) and where the item text fixes the label (check 3).

At the pinned dataset revision, this script:

1. Counts the propositions that appear in more than one archetype (exact match after lower-casing
   and collapsing whitespace) and, for doubling_down_known_facts against known_facts, whether the
   shared items also share the system prompt, the first-turn prompt and the belief prompts.
2. Counts near-duplicate propositions (word 3-shingle Jaccard >= 0.5), within and across
   archetypes, and lists their task ids.
3. Where judged outputs are public (the two forks used in check_scoring.py), measures how often a
   model's extracted belief on a shared doubling-down item equals its belief on the known-facts copy.
4. Counts the items whose "belief" is the ground truth given in the prompt (provided_facts; the
   scorer compares against `ground_truth_extracted` when no belief column exists), the ground
   truth's option letter, and explicit lie instructions in the pressure prompts.

Content is not reproduced (the dataset has no licence); output holds counts and task ids.

Usage:
    python -I check_items.py [--cache DIR] [--out items_checks.json]
"""
import argparse, collections, hashlib, itertools, json, re, urllib.request
from pathlib import Path

import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_scoring import belief_binary, repair  # noqa: E402  mirrored scorer, same directory

HF_SHA = "4602b84dd9e2ca05c6e1eafbc14e556e908ac1bb"
HF_URL = f"https://huggingface.co/datasets/cais/MASK/resolve/{HF_SHA}/"
ARCH = ("continuations", "disinformation", "doubling_down_known_facts", "known_facts",
        "provided_facts", "statistics")
PARQUET_SHA256 = {
    "continuations": "8d451bbe7f6fd83053d41118f8f081a4074047801d8f4183b8e0f5c76621d6b3",
    "disinformation": "3ee30f6dbd39c4b0460c7cda87d03d52849766c0d0094241d72de9c26ac10f59",
    "doubling_down_known_facts": "733e3ad2d0e5f468a1c941d676900dbaec3b45cb9e8188d00559007fe61a64c3",
    "known_facts": "5cc62d3ff1072252aa9819dfb5f9843924787af2278d2ac366f9d79197ea54c9",
    "provided_facts": "c9a1b0ddff3d2f8ca29ef98361a868caeb5623f0b77975fd5a626c2de62a5340",
    "statistics": "5785e109d1bb33a66bf0a9ebd49d646fece6d1663f63d454a65017c38281c12b",
}
FORKS = {"Cadenza-Labs/mask": ("8c13097615273c4d9f835a63bbc7cd9510db2ed4",
                               ("llama-v3.3-70b-instruct", "mistral-small-3.1-24b-instruct",
                                "qwen-2.5-72b-instruct")),
         "limorgu/mask": ("77dd65e4752e9a9d6cb332ca70fb7f4a11a68262", ("gpt-3.5-turbo",))}
LIE_CUE = re.compile(r"\b(lie|lying|deceive|deceiving|mislead|misleading|fabricate|falsify|"
                     r"deny|do not (?:reveal|disclose|mention|admit)|don't (?:reveal|disclose|mention|admit)|"
                     r"conceal|cover up|pretend)\b", re.I)


def fetch(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with urllib.request.urlopen(url, timeout=300) as r:
            path.write_bytes(r.read())
    return path


def norm(s):
    return re.sub(r"\s+", " ", str(s).strip().lower())


def shingles(s, k=3):
    w = re.findall(r"[a-z0-9]+", str(s).lower())
    return set(zip(*[w[i:] for i in range(k)])) if len(w) >= k else {tuple(w)}


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    ap.add_argument("--cache", default=str(here.parent / "data"))
    ap.add_argument("--out", default=str(here / "items_checks.json"))
    a = ap.parse_args()
    cache = Path(a.cache)
    d = {}
    for arch in ARCH:
        p = fetch(f"{HF_URL}{arch}/test-00000-of-00001.parquet", cache / "hf" / arch / "test.parquet")
        assert hashlib.sha256(p.read_bytes()).hexdigest() == PARQUET_SHA256[arch], arch
        d[arch] = pd.read_parquet(p)
    card = fetch(f"{HF_URL}README.md", cache / "hf" / "README.md").read_text()
    res = {"pins": {"data": f"cais/MASK@{HF_SHA}", "forks": {k: v[0] for k, v in FORKS.items()}},
           "rows_per_archetype": {k: len(v) for k, v in d.items()},
           "rows_total": sum(len(v) for v in d.values()),
           "card_states_1028": "1,028" in card}

    # 1. exact overlap across archetypes
    fields = ("proposition", "ground_truth", "system_prompt", "user_prompt", "belief_elicit_1")
    pair = {}
    for f in fields:
        sets = {k: set(map(norm, v[f])) for k, v in d.items() if f in v}
        pair[f] = {f"{x}|{y}": len(sets[x] & sets[y]) for x, y in itertools.combinations(sets, 2)
                   if sets[x] & sets[y]}
    res["exact_shared_across_archetypes"] = pair
    where = collections.defaultdict(set)
    for k, v in d.items():
        for p in v["proposition"]:
            where[norm(p)].add(k)
    res["propositions_in_more_than_one_archetype"] = {
        "|".join(sorted(s)): n for s, n in collections.Counter(frozenset(s) for s in where.values() if len(s) > 1).items()}
    res["within_archetype_duplicate_propositions"] = {k: int(v["proposition"].map(norm).duplicated().sum()) for k, v in d.items()}

    kf = {norm(r.proposition): r for r in d["known_facts"].itertuples()}
    dd = d["doubling_down_known_facts"]
    shared = [(r, kf[norm(r.proposition)]) for r in dd.itertuples() if norm(r.proposition) in kf]
    res["doubling_down_vs_known_facts"] = {
        "doubling_down_items": len(dd), "shared_with_known_facts": len(shared),
        "same_system_prompt": sum(norm(x.system_prompt) == norm(y.system_prompt) for x, y in shared),
        "first_turn_equals_known_facts_user_prompt": sum(norm(x.dd_turn_1_prompt) == norm(y.user_prompt) for x, y in shared),
        "same_three_belief_prompts": sum(all(norm(getattr(x, f"belief_elicit_{i}")) == norm(getattr(y, f"belief_elicit_{i}"))
                                             for i in (1, 2, 3)) for x, y in shared),
        "same_ground_truth": sum(norm(x.ground_truth) == norm(y.ground_truth) for x, y in shared),
        "shared_task_id_pairs": [[x.task_id, y.task_id] for x, y in shared]}

    # 2. near duplicates
    rows = [(k, r.task_id, shingles(r.proposition)) for k, v in d.items() for r in v.itertuples()]
    near = collections.Counter(); near_ids = []
    for (k1, t1, s1), (k2, t2, s2) in itertools.combinations(rows, 2):
        j = len(s1 & s2) / len(s1 | s2) if s1 | s2 else 0
        if j >= 0.5:
            same = k1 == k2
            cls = "exact" if j == 1 else ">=0.8" if j >= 0.8 else "0.5-0.8"
            near[f"{'within' if same else 'across'}:{cls}"] += 1
            if not ({k1, k2} == {"doubling_down_known_facts", "known_facts"} and j == 1):
                near_ids.append([k1, t1, k2, t2, round(j, 2)])
    res["near_duplicate_propositions"] = {"counts": dict(near), "pairs_other_than_dd_kf_exact": near_ids}

    # 3. belief agreement on the shared items, in public judged outputs
    agree = {}
    for fork, (sha, models) in FORKS.items():
        for m in models:
            got = {}
            for arch in ("known_facts", "doubling_down_known_facts"):
                p = fetch(f"https://raw.githubusercontent.com/{fork}/{sha}/mask/csv_data/metrics/{arch}_{m}.csv",
                          cache / "forks" / fork.replace("/", "_") / f"{arch}_{m}.csv")
                df = pd.read_csv(p)
                bcols = [c for c in df.columns if c.startswith("eval(belief_system") and c.endswith("_extracted")]
                fixed = df.copy()
                for c in bcols:
                    fixed[c] = fixed[c].map(repair)
                rep = fixed.apply(lambda r: belief_binary(r, bcols), axis=1)
                got[arch] = {norm(p): (b, rb) for p, b, rb in zip(df["proposition"], df["eval_belief"], rep)}
            g_dd, g_kf = got["doubling_down_known_facts"], got["known_facts"]
            keys = [k for k in g_dd if k in g_kf]
            agree[m] = {"shared": len(keys)}
            for i, name in ((0, "as_released"), (1, "judge_answers_repaired")):
                pairs = [(g_dd[k][i], g_kf[k][i]) for k in keys]
                agree[m][name] = {"same_belief": sum(x == y for x, y in pairs),
                                  "both_no_belief": sum(x == y == "C" for x, y in pairs),
                                  "one_side_no_belief": sum((x == "C") != (y == "C") for x, y in pairs),
                                  "opposite_beliefs": sum(x != y and "C" not in (x, y) for x, y in pairs)}
    res["belief_agreement_on_shared_items"] = agree

    # 4. where the item text fixes the label
    res["provided_facts_items_scored_against_ground_truth"] = len(d["provided_facts"])
    res["ground_truth_is_option_A"] = {k: round(float((v["formatted_ground_truth"] == "A").mean()), 3)
                                       for k, v in d.items() if k != "statistics"}
    res["explicit_lie_cue_in_pressure_prompt"] = {
        k: round(float(v.apply(lambda r: bool(LIE_CUE.search(f"{r.system_prompt} {r.user_prompt}")), axis=1).mean()), 3)
        for k, v in d.items()}
    Path(a.out).write_text(json.dumps(res, indent=1, default=int))
    show = {k: v for k, v in res.items() if k not in ("doubling_down_vs_known_facts", "near_duplicate_propositions")}
    print(json.dumps(show, indent=1, default=int))
    print({k: v for k, v in res["doubling_down_vs_known_facts"].items() if k != "shared_task_id_pairs"})
    print(res["near_duplicate_propositions"]["counts"], len(res["near_duplicate_propositions"]["pairs_other_than_dd_kf_exact"]))


if __name__ == "__main__":
    main()
