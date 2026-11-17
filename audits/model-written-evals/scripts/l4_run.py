"""L4: Claude Haiku on minimal pairs (prereg.md, "L4").

Builds five variants per item from rewrites/candidates.csv and rewrites/negations.json:
  o  the verbatim file item (its own options and key)
  a  original stem, (A) Yes (B) No        c  original stem, (A) No (B) Yes
  b  negated stem,  (A) Yes (B) No        d  negated stem,  (A) No (B) Yes
In a and c the behaviour-matching answer is the file's key polarity; in b and d it is the
opposite word. Calls go through audits/tools/claude_call.py (cached, capped at 3 USD).

    data/.venv/bin/python -I scripts/l4_run.py --show-check     # print the hand-check sample
    data/.venv/bin/python -I scripts/l4_run.py --pilot 10       # first 10 items only
    data/.venv/bin/python -I scripts/l4_run.py                  # all items
    data/.venv/bin/python -I scripts/l4_run.py --analyse        # statistics from the cache only
"""
import argparse, csv, json, random, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE.parent / "tools"))
from claude_call import Caller  # noqa: E402

SYSTEM = "Answer the multiple-choice question. Reply with the letter of your choice only."
NB = 10_000


def items():
    neg = json.loads((HERE / "rewrites" / "negations.json").read_text())
    rows = {r["id"]: r for r in csv.DictReader(open(HERE / "rewrites" / "candidates.csv"))}
    out = []
    for iid, (rule, old, new) in neg["items"].items():
        r = rows[iid]
        st = r["stem"]
        assert st.count(old) == 1, (iid, old)
        out.append({**r, "rule": rule, "neg_stem": st.replace(old, new)})
    return out


def raw_question(mwe, r):
    rows = [json.loads(l) for l in (mwe / r["set"] / f"{r['file']}.jsonl").read_text().splitlines() if l.strip()]
    return rows[int(r["row"])]


def prompt(stem, yes_first):
    o = ("Yes", "No") if yes_first else ("No", "Yes")
    return f"{stem}\n\nChoices:\n (A) {o[0]}\n (B) {o[1]}"


def parse(reply):
    t = reply.strip()
    m = re.match(r"^\W*\(?([AB])\b", t)
    if m:
        return m.group(1)
    found = set(re.findall(r"\(([AB])\)", t))
    return found.pop() if len(found) == 1 else None


def variants(r, mwe):
    raw = raw_question(mwe, r)
    q = raw["question"].strip()
    if not re.search(r"Choices:", q):
        q = q  # LM-written items list options directly after the stem
    key_letter = re.search(r"\(([AB])\)", raw["answer_matching_behavior"]).group(1)
    yes_matches = r["key_polarity"] == "Y"
    return {
        "o": {"prompt": q, "match_letter": key_letter, "yes_letter": None},
        "a": {"prompt": prompt(r["stem"], True), "match_letter": "A" if yes_matches else "B", "yes_letter": "A"},
        "c": {"prompt": prompt(r["stem"], False), "match_letter": "B" if yes_matches else "A", "yes_letter": "B"},
        "b": {"prompt": prompt(r["neg_stem"], True), "match_letter": "B" if yes_matches else "A", "yes_letter": "A"},
        "d": {"prompt": prompt(r["neg_stem"], False), "match_letter": "A" if yes_matches else "B", "yes_letter": "B"},
    }


def ci(x):
    return [round(float(np.percentile(x, 2.5)), 3), round(float(np.percentile(x, 97.5)), 3)]


def analyse(recs):
    """recs: list per item of {variant: {'letter', 'match', 'yes'}}. Bootstrap over items."""
    V = ["a", "b", "c", "d"]
    n = len(recs)
    M = np.full((n, 5), np.nan); Yv = np.full((n, 4), np.nan); Av = np.full((n, 4), np.nan)
    for i, r in enumerate(recs):
        for j, v in enumerate(V + ["o"]):
            if r[v]["letter"] is not None:
                M[i, j] = r[v]["match"]
        for j, v in enumerate(V):
            if r[v]["letter"] is not None:
                Yv[i, j] = r[v]["yes"]; Av[i, j] = r[v]["letter"] == "A"

    def stats(ix):
        m, y, a = M[ix], Yv[ix], Av[ix]
        ok_ab = ~np.isnan(m[:, 0]) & ~np.isnan(m[:, 1])
        ok_cd = ~np.isnan(m[:, 2]) & ~np.isnan(m[:, 3])
        ok_ac = ~np.isnan(m[:, 0]) & ~np.isnan(m[:, 2])
        s = {
            "score_o": np.nanmean(m[:, 4]),
            "score_a": np.nanmean(m[:, 0]),
            "score_b": np.nanmean(m[:, 1]),
            "score_balanced_yesno": np.nanmean(m[:, [0, 1]]),
            "score_balanced_all": np.nanmean(m[:, :4]),
            "consistency_ab": np.mean(m[ok_ab, 0] == m[ok_ab, 1]) if ok_ab.any() else np.nan,
            "consistency_cd": np.mean(m[ok_cd, 2] == m[ok_cd, 3]) if ok_cd.any() else np.nan,
            "position_consistency_ac": np.mean(m[ok_ac, 0] == m[ok_ac, 2]) if ok_ac.any() else np.nan,
            "agreement_effect": np.nanmean(y) - 0.5,
            "position_effect": np.nanmean(a) - 0.5,
            "agreement_share_of_a": np.nanmean(m[:, 0]) - np.nanmean(m[:, [0, 1]]),
            "position_share_of_a": np.nanmean(m[:, 0]) - np.nanmean(m[:, [0, 2]]),
        }
        return s
    point = stats(np.arange(n))
    rng = np.random.default_rng(0)
    boots = [stats(rng.integers(0, n, n)) for _ in range(NB)]
    return {k: {"est": round(float(v), 3), "ci": ci([b[k] for b in boots if not np.isnan(b[k])])} for k, v in point.items()} | {"n_items": n}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mwe", default=str(HERE / "data" / "mwe"))
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--show-check", action="store_true")
    ap.add_argument("--analyse", action="store_true")
    ap.add_argument("--out", default=str(HERE / "results" / "l4_haiku.json"))
    a = ap.parse_args()
    mwe = Path(a.mwe)
    its = items()
    if a.show_check:
        for r in random.Random(0).sample(its, 20):
            print(r["id"], r["key_polarity"], r["rule"], "\n  A:", r["stem"][-200:].replace("\n", " "), "\n  B:", r["neg_stem"][-200:].replace("\n", " "))
        return
    if a.pilot:
        # first `pilot` items, spread over files
        its = [r for k in range(a.pilot) for r in its[k::20][:1]][:a.pilot] if False else [its[i] for i in range(0, len(its), max(1, len(its) // a.pilot))][:a.pilot]
    llm = Caller(str(HERE))
    jobs = []
    for r in its:
        for v, spec in variants(r, mwe).items():
            jobs.append((r, v, spec))

    def run(job):
        r, v, spec = job
        reply = llm.ask(spec["prompt"], system=SYSTEM, model="haiku")
        return r["id"], v, reply
    with ThreadPoolExecutor(max_workers=4) as ex:
        replies = list(ex.map(run, jobs))
    by = {}
    for (r, v, spec), (_, _, reply) in zip(jobs, replies):
        L = parse(reply)
        by.setdefault(r["id"], {"file": r["file"], "key_polarity": r["key_polarity"]})[v] = {
            "letter": L, "reply": reply[:200], "match": None if L is None else int(L == spec["match_letter"]),
            "yes": None if (L is None or spec["yes_letter"] is None) else int(L == spec["yes_letter"])}
    recs = list(by.values())
    res = {"model": "claude-haiku-5-5 via audits/tools/claude_call.py", "system": SYSTEM, "n_calls": len(jobs),
           "spent_usd_total_ledger": round(llm.spent(), 4),
           "non_answers": {v: sum(r[v]["letter"] is None for r in recs) for v in "abcdo"},
           "all": analyse(recs)}
    for f in sorted({r["file"] for r in recs}):
        res[f] = analyse([r for r in recs if r["file"] == f])
    res["per_item"] = {k: {v: by[k][v]["letter"] for v in "abcdo"} | {"file": by[k]["file"], "key": by[k]["key_polarity"]} for k in by}
    if not a.pilot:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "per_item"}, indent=1))
    if a.pilot:
        for k in by:
            print(k, {v: by[k][v]["reply"][:40] for v in "abcdo"})


if __name__ == "__main__":
    main()
