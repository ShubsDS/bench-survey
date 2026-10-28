"""Keys that cannot be right, and structurally ambiguous items, in WMDP (check 6).

Dataset: cais/wmdp, revision 7125571f22f032c56415e7980f48d877dd830ff8.

Every flag below is decided from the item's own structure, so it needs no restatement of the
item's content and no domain judgement:

  mismatched_choices        two items share an identical question but their choice sets are
                            disjoint, so at least one item's choices belong to a different
                            question and its key cannot be verified against what is asked
  conflicting_key           items with identical question and identical choice set whose keyed
                            choice text differs
  repeated_choice           an item offers the same choice string twice; flagged separately for
                            whether the repeated string is the keyed one (then two positions are
                            equally correct and the grader accepts one)
  numeric_tie               all four choices are numeric and two are numerically equal
  two_meta_options          two or more "all/none of the above"-type choices in one item, which
                            can make more than one answer defensible
  key_is_none_of_the_above   the key is a "none of the above"-type choice (reported as a count
                            only; not itself an error)

A seeded hand sample per subset is not part of this script. Reading bio and chem items closely
enough to second-guess their keys means restating hazardous detail, which this audit does not do;
the limitation is recorded in the README rather than worked around.

Usage: python check_keys.py [--cache data] [--out out/key_checks.json]
"""
import argparse, collections, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SHA, SUBSETS, load_all, wilson
from dupcore import norm

META = re.compile(r"^(all|none|both|neither)\s+of\s+(the\s+|these|those)?\s*(above|these|those|them)\b"
                  r"|^(all|none)\s+of\s+the\s+(answers|options|choices)\b", re.I)
NONE = re.compile(r"^(none|neither)\b", re.I)


def is_num(c):
    c = c.strip()
    try:
        return int(c, 0) if re.fullmatch(r"-?(0[xX][0-9a-fA-F]+|\d+)", c) else float(c)
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="out/key_checks.json")
    a = ap.parse_args()
    data = load_all(a.cache)
    rows = [r for s in SUBSETS for r in data[s]]

    res = {"dataset": "cais/wmdp", "revision": SHA, "rows": len(rows),
           "method": "structural flags only; no hand re-keying of bio or chem items",
           "flags": {}, "per_subset": {}}

    byq = collections.defaultdict(list)
    for r in rows:
        byq[norm(r["question"])].append(r)

    mismatched, conflicting = [], []
    for q, g in byq.items():
        if len(g) < 2:
            continue
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                A = {norm(c) for c in g[i]["choices"]}
                B = {norm(c) for c in g[j]["choices"]}
                if not A & B:
                    mismatched.append({"ids": [g[i]["id"], g[j]["id"]], "shared_choices": 0})
                elif A == B and norm(g[i]["choices"][g[i]["answer"]]) != norm(g[j]["choices"][g[j]["answer"]]):
                    conflicting.append({"ids": [g[i]["id"], g[j]["id"]]})

    repeated_key, repeated_other, numeric_tie, two_meta, key_none = [], [], [], [], []
    for r in rows:
        cs = [norm(c) for c in r["choices"]]
        dupes = {c for c in cs if cs.count(c) > 1}
        if dupes:
            (repeated_key if cs[r["answer"]] in dupes else repeated_other).append(r["id"])
        v = [is_num(c) for c in r["choices"]]
        if all(x is not None for x in v) and len(set(v)) < 4:
            numeric_tie.append(r["id"])
        if sum(bool(META.match(c.strip())) for c in r["choices"]) > 1:
            two_meta.append(r["id"])
        if NONE.match(r["choices"][r["answer"]].strip()) and META.match(r["choices"][r["answer"]].strip()):
            key_none.append(r["id"])

    res["flags"] = {
        "mismatched_choices": mismatched,
        "conflicting_key": conflicting,
        "repeated_choice_includes_key": repeated_key,
        "repeated_choice_not_key": repeated_other,
        "numeric_tie": numeric_tie,
        "two_meta_options": two_meta,
        "key_is_none_of_the_above": key_none,
    }
    for s in SUBSETS:
        n = len(data[s])
        ids = {r["id"] for r in data[s]}
        counts = {k: sum(1 for x in v if (x in ids if isinstance(x, str) else x["ids"][0] in ids))
                  for k, v in res["flags"].items()}
        flagged = sum(counts[k] for k in ("mismatched_choices", "conflicting_key",
                                          "repeated_choice_includes_key", "numeric_tie"))
        res["per_subset"][s] = {"rows": n, "counts": counts,
                                "items_with_a_key_defect": flagged,
                                "rate": round(flagged / n, 4),
                                "wilson_95": wilson(flagged, n)}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps({"flag_counts": {k: len(v) for k, v in res["flags"].items()},
                      "per_subset": res["per_subset"], "flags": res["flags"]}, indent=2))


if __name__ == "__main__":
    main()
