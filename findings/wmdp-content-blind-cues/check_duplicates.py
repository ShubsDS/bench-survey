"""Duplicates and cross-item leakage in WMDP (check 5).

Dataset: cais/wmdp, revision 7125571f22f032c56415e7980f48d877dd830ff8.

WMDP ships one `test` split per subset, so there is no train/test boundary to leak across. What is
measured instead:

  exact_item                 identical normalised question and identical set of choices
  exact_question             identical normalised question (whatever the choices)
  near_item                  item-level 3-word-shingle Jaccard >= 0.5 over question + sorted
                             choices (hand-calibrated: 0.8 and above are reorderings or
                             one-token edits of each other)
  shared_choice_set          different questions offering the identical set of four choices
  answer_in_other_question   the keyed choice appears verbatim in some other item's question
                             while none of that item's distractors do, so the key is readable
                             from elsewhere in the same subset
  template_share             share of items from the four generated cyber templates, which
                             dominate the near-duplicate pairs

Pairs are reported as counts, plus every exact pair's ids. No item text is printed.

Usage: python check_duplicates.py [--cache data] [--out out/duplicate_checks.json]
"""
import argparse, collections, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SHA, SUBSETS, load_all, qhash
from dupcore import norm, pairs, item_text

TEMPLATES = ("I captured a network packet", "Which arguments will cause",
             "What number is returned when", "What is the output of the following")


def templated(r):
    return r["question"].startswith(TEMPLATES)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="out/duplicate_checks.json")
    ap.add_argument("--near", type=float, default=0.5)
    a = ap.parse_args()
    data = load_all(a.cache)
    rows = [r for s in SUBSETS for r in data[s]]
    res = {"dataset": "cais/wmdp", "revision": SHA, "splits": "one test split per subset",
           "near_duplicate_threshold": a.near, "rows": len(rows), "subsets": {}}

    # exact duplicates
    byq, byitem, bychoices = collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list)
    for r in rows:
        key_choices = tuple(sorted(norm(c) for c in r["choices"]))
        byq[norm(r["question"])].append(r)
        byitem[(norm(r["question"]), key_choices)].append(r)
        bychoices[key_choices].append(r)

    def group_ids(groups):
        return [[r["id"] for r in g] for g in groups.values() if len(g) > 1]

    res["exact_item_groups"] = group_ids(byitem)
    res["exact_question_groups"] = group_ids(byq)
    res["shared_choice_set_groups"] = sorted(
        ([r["id"] for r in g] for k, g in bychoices.items() if len(g) > 1 and
         len({norm(r["question"]) for r in g}) > 1 and not any(templated(r) for r in g)),
        key=len, reverse=True)
    res["exact_item_extra_copies"] = sum(len(g) - 1 for g in byitem.values() if len(g) > 1)
    res["exact_question_extra_copies"] = sum(len(g) - 1 for g in byq.values() if len(g) > 1)

    # near duplicates, within and across subsets
    P = pairs(rows, a.near)
    bands = collections.Counter()
    cross = collections.Counter()
    nontemplate = []
    for i, j, v, _ in P:
        b = "0.9-1.0" if v >= 0.9 else "0.8-0.9" if v >= 0.8 else "0.7-0.8" if v >= 0.7 else "0.5-0.7"
        bands[b] += 1
        cross[tuple(sorted((rows[i]["subset"], rows[j]["subset"])))] += 1
        if not (templated(rows[i]) or templated(rows[j])):
            nontemplate.append((rows[i]["id"], rows[j]["id"], round(v, 3)))
    res["near_item_pairs"] = sum(bands.values())
    res["near_item_pairs_by_band"] = dict(sorted(bands.items()))
    res["near_item_pairs_by_subset_pair"] = {f"{x}|{y}": n for (x, y), n in cross.items()}
    res["near_item_pairs_excluding_cyber_templates"] = sorted(nontemplate, key=lambda t: -t[2])

    for s in SUBSETS:
        sub = data[s]
        n = len(sub)
        tp = sum(templated(r) for r in sub)
        # the keyed choice readable from another item's question in the same subset
        qs = [norm(r["question"]) for r in sub]
        leak = {w: [] for w in (2, 3, 4)}
        for idx, r in enumerate(sub):
            k = norm(r["choices"][r["answer"]])
            nw = len(k.split())
            if nw < 2 or len(k) < 8:
                continue  # too short to be a distinctive string
            d = [norm(c) for i2, c in enumerate(r["choices"]) if i2 != r["answer"]]
            for j, q in enumerate(qs):
                if j == idx or k not in q:
                    continue
                if not any(x and x in q for x in d):
                    for w in leak:
                        if nw >= w:
                            leak[w].append((r["id"], sub[j]["id"]))
                    break
        res["subsets"][s] = {
            "rows": n, "templated_items": tp, "template_share": round(tp / n, 3),
            "exact_item_extra_copies": sum(len(g) - 1 for g in byitem.values()
                                           if len(g) > 1 and g[0]["subset"] == s),
            "answer_in_other_question_pairs": leak[3],
            "answer_in_other_question_rate_by_min_words":
                {str(w): round(len(v) / n, 4) for w, v in leak.items()},
            "question_sha12_of_exact_duplicates": sorted(
                {qhash(g[0]["question"]) for g in byitem.values() if len(g) > 1 and g[0]["subset"] == s}),
        }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "near_item_pairs_excluding_cyber_templates"}, indent=2)[:4000])


if __name__ == "__main__":
    main()
