"""Duplicates and give-aways in SAD (check 5).

Within each multiple-choice task and across tasks: exact repeats of the question (normalised),
exact repeats of question plus choice set, near-duplicates (3-shingle Jaccard >= 0.5 and >= 0.9 on
question plus choices), and items whose keyed choice (3+ words) appears verbatim in another item's
question while the distractor does not. For the stages tasks the item is the text, so overlap
between stages_full and stages_oversight is counted on text, with whether the two labels agree.
For facts_which_llm one model's 2nd-person batch stands for the question set (questions are the
same for every model). Self-recognition: how often one text recurs across a model's samples.

Usage: python -I check_duplicates.py --cache data --out duplicate_checks.json
"""
import argparse, json, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SHA, ensure, evalresults, load_evalresult, mcq_task, near_pairs, norm, which_llm

TASKS = ("facts_human_defaults", "facts_llms", "influence", "stages_full", "stages_oversight")


def full_text(it):
    return it["q"] + " || " + " | ".join(sorted(it["right"] + it["wrong"]))


def within(items):
    qn = Counter(norm(it["q"]) for it in items)
    fn = Counter(norm(it["q"]) + "||" + "|".join(sorted(map(norm, it["right"] + it["wrong"]))) for it in items)
    pairs = near_pairs([full_text(it) for it in items], 0.5)
    conflict = 0  # same question and choice set, different key
    keyed = defaultdict(set)
    for it in items:
        keyed[norm(it["q"]) + "||" + "|".join(sorted(map(norm, it["right"] + it["wrong"])))].add(norm(it["right"][0]))
    conflict = sum(len(v) > 1 for v in keyed.values())
    return {"items": len(items),
            "repeated_question_groups": sum(c > 1 for c in qn.values()),
            "items_in_repeated_question_groups": sum(c for c in qn.values() if c > 1),
            "repeated_question_and_choices_groups": sum(c > 1 for c in fn.values()),
            "items_in_repeated_question_and_choices": sum(c for c in fn.values() if c > 1),
            "same_question_and_choices_different_key": conflict,
            "near_pairs_j50": len(pairs), "near_pairs_j90": sum(j >= 0.9 for _, _, j in pairs),
            "items_in_a_near_pair_j50": len({i for p in pairs for i in p[:2]}),
            "example_ids_j90": [[items[i]["id"][:23], items[j]["id"][:23]] for i, j, x in pairs if x >= 0.9][:10]}


def giveaways(items, min_words=3):
    """Items whose keyed text occurs inside some other item's question, the distractor not."""
    qs = [" " + norm(it["q"]) + " " for it in items]
    hits = []
    for a, it in enumerate(items):
        r = norm(it["right"][0])
        if len(r.split()) < min_words:
            continue
        ws = [norm(w) for w in it["wrong"]]
        for b, q in enumerate(qs):
            if b != a and f" {r} " in q and not any(f" {w} " in q for w in ws if w):
                hits.append(it["id"][:23])
                break
    eligible = sum(len(norm(it["right"][0]).split()) >= min_words for it in items)
    return {"min_words": min_words, "eligible": eligible, "given_away": len(hits), "ids": hits[:20]}


def rescore_distinct(unz):
    """Released plain-variant results of facts_human_defaults, rescored keeping one copy of each
    sample id (the first). Invalid answers get chance credit 0.5, as SAD's score does."""
    out = {}
    for p in evalresults(unz, "sad/facts/human_defaults", "facts_human_defaults--plain--"):
        model = p.name.split("--")[2]
        if " " in model:
            continue
        er = load_evalresult(p)
        srs = er["sample_results"]
        if len(srs) < 1000:
            continue
        def sc(r):
            return 0.5 if r.get("output_parsed") in (None, "[unparsable]") and not r.get("score") else float(r.get("score") or 0)
        seen, first, dup_scores = set(), [], []
        for r in srs:
            sid = r["sample"]["id"]
            (dup_scores if sid in seen else first).append(sc(r))
            seen.add(sid)
        allv = [sc(r) for r in srs]
        out[model] = {"scored": len(allv), "distinct_ids": len(first),
                      "score_all": round(sum(allv) / len(allv), 4),
                      "score_distinct": round(sum(first) / len(first), 4),
                      "score_on_second_copies": round(sum(dup_scores) / len(dup_scores), 4) if dup_scores else None}
    diffs = [v["score_all"] - v["score_distinct"] for v in out.values()]
    ms = list(out)
    flips = [(a, b) for i, a in enumerate(ms) for b in ms[i + 1:]
             if (out[a]["score_all"] - out[b]["score_all"]) * (out[a]["score_distinct"] - out[b]["score_distinct"]) < 0]
    return {"per_model": out, "max_abs_change": round(max(map(abs, diffs)), 4) if diffs else None,
            "model_pairs": len(ms) * (len(ms) - 1) // 2, "pairs_whose_order_flips": len(flips), "flipped_pairs": flips}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="duplicate_checks.json")
    a = ap.parse_args()
    unz, _ = ensure(a.cache)
    data = {t: mcq_task(unz, t) for t in TASKS}
    per_model, _ = which_llm(unz)
    data["facts_which_llm"] = per_model["gpt-4o"]
    res = {"repo": "LRudL/sad", "commit": SHA, "within_task": {}, "giveaways": {}, "cross_task": {}}
    for t, items in data.items():
        res["within_task"][t] = within(items)
        if not t.startswith("stages"):
            res["giveaways"][t] = giveaways(items)
    # facts_human_defaults by batch: the three batches are separate sub-sets of one task
    fh = data["facts_human_defaults"]
    res["within_task"]["facts_human_defaults_cross_batch"] = {}
    pairs = near_pairs([full_text(it) for it in fh], 0.5)
    res["within_task"]["facts_human_defaults_cross_batch"] = dict(Counter(
        "-".join(sorted((fh[i]["batch"], fh[j]["batch"]))) for i, j, _ in pairs))

    # across question tasks
    qtasks = ("facts_human_defaults", "facts_llms", "influence", "facts_which_llm")
    allq = [(t, it) for t in qtasks for it in data[t]]
    pairs = near_pairs([it["q"] for _, it in allq], 0.5)
    cross = Counter("-".join(sorted((allq[i][0], allq[j][0]))) for i, j, _ in pairs if allq[i][0] != allq[j][0])
    exact = Counter()
    seen = defaultdict(set)
    for t, it in allq:
        seen[norm(it["q"])].add(t)
    for q, ts in seen.items():
        if len(ts) > 1:
            exact["-".join(sorted(ts))] += 1
    res["cross_task"]["question_tasks_near_pairs_j50"] = dict(cross)
    res["cross_task"]["question_tasks_exact_question"] = dict(exact)
    res["cross_task"]["giveaway_across_question_tasks"] = giveaways([it for _, it in allq])

    # stages_full vs stages_oversight on text
    sf, so = data["stages_full"], data["stages_oversight"]
    fmap = defaultdict(list)
    for it in sf:
        fmap[norm(it["q"])].append(it["right"][0])
    ov = Counter()
    for it in so:
        for lab in fmap.get(norm(it["q"]), []):
            ov[f"{lab} -> oversight:{it['right'][0]}"] += 1
    texts = [it["q"] for it in sf] + [it["q"] for it in so]
    np_ = near_pairs(texts, 0.9)
    cross_np = [(i, j) for i, j, _ in np_ if (i < len(sf)) != (j < len(sf))]
    res["cross_task"]["stages_full_vs_oversight_exact_text"] = dict(ov)
    res["cross_task"]["stages_full_vs_oversight_near_j90"] = len(cross_np)

    # self-recognition: recurrence of one text across a model's samples (plain, who)
    sr = {}
    for p in evalresults(unz, "sad/self_recognition", "self_recognition_who--plain--"):
        model = p.name.split("--")[2]
        if " " in model:
            continue
        er = load_evalresult(p)
        c = Counter()
        for s in er["sample_results"]:
            v = s["sample"]["extra_template_vars"]
            c[norm(v["train_text_1"])] += 1
            c[norm(v["train_text_2"])] += 1
        sr[model] = {"samples": len(er["sample_results"]), "distinct_texts": len(c),
                     "texts_used_more_than_once": sum(x > 1 for x in c.values())}
    res["self_recognition_who_text_reuse"] = sr
    res["facts_human_defaults_rescored_on_distinct_ids"] = rescore_distinct(unz)
    Path(a.out).write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "self_recognition_who_text_reuse"}, indent=1))


if __name__ == "__main__":
    main()
