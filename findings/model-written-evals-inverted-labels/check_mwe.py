"""Label direction and content-blind baselines in Anthropic's advanced-AI-risk evals.

Perez et al., "Discovering Language Model Behaviors with Model-Written Evaluations"
(arXiv 2212.09251), release A/B questions for 15 behaviours, each in a crowdworker-written
(`human_generated_evals`) and an LM-written (`lm_generated_evals`) version. The README defines
`answer_matching_behavior` as "the answer that would be given by a language model exhibiting the
behavior being tested".

This script, at a pinned dataset revision:

1. Checks the direction of the key against hand labels (`hand_labels.csv`): for random samples of
   rows, which answer the key marks as matching, the one showing the behaviour or the one without
   it. Each row's question hash is checked against the pinned file.
2. Computes content-blind baselines for every file: the share of rows whose matching answer is
   "(A)", is "Yes" (among Yes/No rows), or is the shorter option; the score of the policies
   "always Yes" and "always the shorter option"; exact duplicate questions; rows keyed beyond (B).

Usage:
    python check_mwe.py [--cache DIR] [--out mwe_checks.json]
"""
import argparse, csv, hashlib, json, math, re, urllib.request
from pathlib import Path

SHA = "d533f626cc321c92175a58ee570aa3cdb87238d1"
URL = f"https://huggingface.co/datasets/Anthropic/model-written-evals/resolve/{SHA}/advanced-ai-risk/"
FILES = ("coordinate-itself", "coordinate-other-ais", "coordinate-other-versions", "corrigible-less-HHH",
         "corrigible-more-HHH", "corrigible-neutral-HHH", "myopic-reward", "one-box-tendency",
         "power-seeking-inclination", "self-awareness-general-ai", "self-awareness-good-text-model",
         "self-awareness-text-model", "self-awareness-training-architecture", "survival-instinct",
         "wealth-seeking-inclination")
SETS = ("human_generated_evals", "lm_generated_evals")
HERE = Path(__file__).resolve().parent


def load(kind, name, cache):
    path = cache / kind / f"{name}.jsonl"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(f"{URL}{kind}/{name}.jsonl", timeout=300) as r:
            path.write_bytes(r.read())
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def options(q):
    """{letter: text} for the lettered choices in a question."""
    parts = re.split(r"\n\s*\(([A-H])\)\s*", "\n" + q.split("Choices:")[-1] if "Choices:" in q else "\n" + q)
    return {parts[i]: parts[i + 1].strip().split("\n")[0].strip() for i in range(1, len(parts) - 1, 2)}


def key(r, field):
    v = r[field]
    v = v[0] if isinstance(v, list) else v
    m = re.search(r"\(([A-H])\)", v)
    return m.group(1) if m else None


def is_yes(t):
    return re.match(r"yes\b", t.strip().lower()) is not None


def is_no(t):
    return re.match(r"no\b", t.strip().lower()) is not None


def baselines(rows):
    n = len(rows)
    out = {"rows": n, "duplicate_questions": n - len({r["question"] for r in rows}),
           "keyed_beyond_B": sum(key(r, "answer_matching_behavior") not in ("A", "B") for r in rows),
           "match_is_A": round(sum(key(r, "answer_matching_behavior") == "A" for r in rows) / n, 3)}
    yn = yes = diff = shorter = 0
    always_yes = always_shorter = 0.0
    for r in rows:
        o = options(r["question"])
        m, nm = o.get(key(r, "answer_matching_behavior")), o.get(key(r, "answer_not_matching_behavior"))
        if m is None or nm is None:
            always_yes += .5; always_shorter += .5
            continue
        if (is_yes(m) and is_no(nm)) or (is_no(m) and is_yes(nm)):
            yn += 1; yes += is_yes(m); always_yes += is_yes(m)
        else:
            always_yes += .5
        if len(m) != len(nm):
            diff += 1; shorter += len(m) < len(nm); always_shorter += len(m) < len(nm)
        else:
            always_shorter += .5
    out.update({"yes_no_rows": yn, "match_is_yes": round(yes / yn, 3) if yn else None,
                "match_is_shorter": round(shorter / diff, 3) if diff else None,
                "score_always_yes": round(always_yes / n, 3), "score_always_shorter": round(always_shorter / n, 3)})
    return out


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    c = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    mid = (p + z * z / (2 * n)) / (1 + z * z / n)
    return [round(mid - c, 3), round(mid + c, 3)]


def direction(cache):
    out = {}
    with open(HERE / "hand_labels.csv", newline="") as f:
        for row in csv.DictReader(f):
            rows = load(row["set"], row["file"], cache)
            q = rows[int(row["row"])]["question"]
            if hashlib.sha256(q.encode()).hexdigest()[:12] != row["question_sha256_12"]:
                raise SystemExit(f"hand label does not match the pinned file: {row}")
            d = out.setdefault(f"{row['set']}/{row['file']}", {"labelled": 0, "safe": 0, "behaviour": 0, "unclear": 0})
            d["labelled"] += 1; d[row["key_marks"]] += 1
    for d in out.values():
        decided = d["safe"] + d["behaviour"]
        d["share_keyed_to_safe_answer"] = round(d["safe"] / decided, 3) if decided else None
        d["wilson_95"] = wilson(d["safe"], decided)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="mwe_checks.json")
    args = ap.parse_args()
    cache = Path(args.cache)
    result = {"pins": {"dataset": f"Anthropic/model-written-evals@{SHA}"},
              "direction_hand_labels": direction(cache),
              "baselines": {f"{k}/{n}": baselines(load(k, n, cache)) for k in SETS for n in FILES}}
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
