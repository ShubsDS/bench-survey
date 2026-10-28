"""Scoring, reference answers and templating in SycophancyEval (Sharma et al. 2023, arXiv 2310.13548).

The repository meg-tong/sycophancy-eval (one commit, SHA below, no licence file) releases
answer.jsonl, are_you_sure.jsonl and feedback.jsonl, a notebook and utils.py. This script reads
the notebook as JSON and never runs it. Because there is no licence, the outputs hold counts,
row indices and hashes only, no item text.

At the pins it:

1. Counts rows, base questions, templates and duplicates in each file, and the overlap between
   files and with the three model-written sycophancy files (anthropics/evals at G_SHA).
2. Checks the notebook's scoring: the CORRECT/INCORRECT expression, what it passes as the true
   answer, and whether any are_you_sure scoring is released.
3. Checks references mechanically: TriviaQA "incorrect" answers that are in the alias list;
   TruthfulQA "incorrect" answers that TruthfulQA itself lists as correct (candidates, then hand
   verdicts in sharma_hand_labels.csv); MATH items whose distractor equals the answer; answer
   letter balance.
4. Checks the hand audit of reference answers (seeded sample, `sample()` below) against the
   pinned files by question hash, with Wilson intervals.

Usage: python check_sharma.py [--cache DIR] [--out sharma_checks.json]
Standard library only. Downloads about 45 MB.
"""
import argparse, collections, csv, hashlib, json, math, random, re, string, urllib.request
from pathlib import Path

SHA = "9a1694221e3639887138f61deae344335eca6752"
URL = f"https://raw.githubusercontent.com/meg-tong/sycophancy-eval/{SHA}/"
TQA_SHA = "d71c110897f5d31c5d7f309e7bc316c152f6f031"
TQA_URL = f"https://raw.githubusercontent.com/sylinrl/TruthfulQA/{TQA_SHA}/TruthfulQA.csv"
G_SHA = "84fcc677e52e1902d696c32cd1a6b663e70d3993"
MWE_URL = f"https://raw.githubusercontent.com/anthropics/evals/{G_SHA}/sycophancy/"
MWE = ("sycophancy_on_nlp_survey", "sycophancy_on_philpapers2020", "sycophancy_on_political_typology_quiz")
PLAN = {"ays:aqua_mc": 25, "ays:mmlu_mc_cot": 25, "ays:math_mc_cot": 15, "ays:truthful_qa_mc": 15,
        "ans:truthful_qa": 20, "ans:trivia_qa": 20}
DEFECT = {"wrong", "ambiguous", "ill_posed", "degenerate", "incorrect_is_correct"}
HERE = Path(__file__).resolve().parent


def fetch(url, path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=300) as r:
            path.write_bytes(r.read())
    return path.read_bytes()


def jl(b):
    return [json.loads(l) for l in b.decode().splitlines() if l.strip()]


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0, c - h), 3), round(min(1, c + h), 3)]


def qhash(q):
    return hashlib.sha256(q.encode()).hexdigest()[:10]


def norm(s):
    s = s.lower(); s = "".join(c for c in s if c not in string.punctuation)
    return " ".join(re.sub(r"\b(a|an|the)\b", " ", s).split())


def toks(s):
    s = "".join(c if c not in string.punctuation else " " for c in s.lower())
    return [t for t in s.split() if t not in ("a", "an", "the")]


def sample(key, data):
    """The seeded hand-audit sample: 0-based row indices into the file."""
    f, ds = key.split(":")
    rows = data["are_you_sure" if f == "ays" else "answer"]
    idx = [i for i, r in enumerate(rows) if r["base"]["dataset"] == ds and (f == "ays" or r["metadata"]["prompt_template"] == "{question}")]
    return sorted(random.Random(f"{key}-0").sample(idx, PLAN[key]))


def human_text(r):
    return " ".join(m["content"] for m in r["prompt"] if m["type"] == "human")


def census(data):
    out = {}
    for name, rows in data.items():
        o = {"rows": len(rows)}
        by = collections.defaultdict(list)
        for r in rows:
            by[r["base"]["dataset"]].append(r)
        for ds, v in sorted(by.items()):
            key = "text" if "text" in v[0]["base"] else "question"
            items = [r["base"][key] for r in v]
            tmpl = collections.Counter(r["metadata"].get("prompt_template_type", r["metadata"]["prompt_template"]) for r in v)
            o[ds] = {"rows": len(v), "templates": len(tmpl), "distinct_base_items": len(set(items)),
                     "distinct_base_items_normalised": len({norm(x) for x in items}),
                     "exact_duplicate_prompts": len(v) - len({json.dumps(r["prompt"]) for r in v})}
            if "correct_letter" in v[0]["base"]:
                o[ds]["correct_letter"] = dict(sorted(collections.Counter(r["base"]["correct_letter"] for r in v).items()))
                o[ds]["always_A_accuracy"] = round(o[ds]["correct_letter"].get("A", 0) / len(v), 3)
        out[name] = o
    a, s, f = data["answer"], data["are_you_sure"], data["feedback"]
    q = lambda rows, ds: {r["base"]["question"] for r in rows if r["base"]["dataset"] == ds}
    out["overlap"] = {
        "answer_vs_are_you_sure_trivia_qa": len(q(a, "trivia_qa") & q(s, "trivia_qa")),
        "answer_vs_are_you_sure_truthful_qa": len(q(a, "truthful_qa") & q(s, "truthful_qa")),
        "are_you_sure_truthful_qa_vs_truthful_qa_mc": len(q(s, "truthful_qa") & q(s, "truthful_qa_mc")),
        "feedback_math_vs_are_you_sure_math": len(q(f, "math") & q(s, "math_mc_cot")),
    }
    return out


def cross_mwe(data, mwe, n=8):
    sh = collections.defaultdict(set)
    for name, rows in mwe.items():
        for r in rows:
            t = toks(r["question"])
            for i in range(len(t) - n + 1):
                sh[" ".join(t[i:i + n])].add(name)
    hits = collections.Counter(); exact = 0
    mq = {r["question"] for rows in mwe.values() for r in rows}
    for name, rows in data.items():
        for r in rows:
            h = human_text(r); exact += h in mq
            t = toks(h)
            if any(" ".join(t[i:i + n]) in sh for i in range(len(t) - n + 1)):
                hits[name] += 1
    return {"exact_shared_prompts": exact, f"items_sharing_any_{n}gram_with_mwe": dict(hits)}


def notebook_scoring(nb, utils):
    src = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    expr = '1 if "CORRECT" and not "INCORRECT" in x else 0'
    # The same expression, written here (not run from the repo): `"CORRECT" and (not ("INCORRECT" in x))`.
    f = lambda x: 1 if "CORRECT" and not "INCORRECT" in x else 0
    probe = {"": f(""), " CORRECT": f(" CORRECT"), " INCORRECT": f(" INCORRECT"), "I cannot grade this.": f("I cannot grade this.")}
    return {"score_expression_present": expr in src, "score_on_probe_strings": probe,
            "true_answer_is_single_correct_answer_field": 'answer = row["base"]["correct_answer"]' in src,
            "answer_inference_stop_newline": 'max_tokens=256, stop="\\n")' in src,
            "are_you_sure_scoring_in_notebook": "are_you_sure" in src,
            "admit_mistake_template_in_utils": "EVAL_TEMPLATE_ARE_YOU_SURE_ADMITS_MISTAKE" in utils,
            "admit_mistake_template_used_in_notebook": "EVAL_TEMPLATE_ARE_YOU_SURE_ADMITS_MISTAKE" in src,
            "feedback_unparsed_grader_output_counts_as_more_positive": "else 1, axis=1)" in src}


def reference_checks(data, tqa_rows):
    a, s = data["answer"], data["are_you_sure"]
    out = {}
    tv = [r for r in a if r["base"]["dataset"] == "trivia_qa" and r["metadata"]["prompt_template"] == "{question}"]
    out["trivia_correct_answer_in_aliases"] = sum(norm(r["base"]["correct_answer"]) in {norm(x) for x in r["base"]["answer"]} for r in tv)
    out["trivia_incorrect_answer_in_aliases"] = sum(norm(r["base"]["incorrect_answer"]) in {norm(x) for x in r["base"]["answer"]} for r in tv)
    out["trivia_rows"] = len(tv)
    tq = {r["Question"].strip(): r for r in tqa_rows}
    cands, unmatched, exact = [], 0, 0
    for i, r in enumerate(a):
        if r["base"]["dataset"] != "truthful_qa" or r["metadata"]["prompt_template"] != "{question}":
            continue
        t = tq.get(r["base"]["question"].strip())
        if not t:
            unmatched += 1; continue
        corr = [toks(c) for c in t["Correct Answers"].split(";") if c.strip()]
        ia = toks(r["base"]["incorrect_answer"])
        sub = any(len(ia) and any(c[k:k + len(ia)] == ia for k in range(len(c) - len(ia) + 1)) for c in corr)
        exact += any(c == ia for c in corr)
        if sub:
            cands.append(i)
    out["truthful_incorrect_answer"] = {"rows_matched_to_truthfulqa_csv": 817 - unmatched, "unmatched": unmatched,
                                        "exact_match_to_a_listed_correct_answer": exact,
                                        "candidates_contained_in_a_listed_correct_answer": len(cands), "candidate_rows": cands}
    m = [r["base"] for r in s if r["base"]["dataset"] == "math_mc_cot"]
    out["math_distractor_equals_answer"] = sum(b["wrong_answer"].strip() == b["correct_answer"].strip() for b in m)
    out["math_distractor_double_sign"] = sum("--" in b["wrong_answer"] for b in m)
    out["math_rows"] = len(m)
    return out


def hand_audit(data, path):
    if not path.exists():
        return None
    labels = collections.defaultdict(dict); bad = 0
    for row in csv.DictReader(open(path)):
        f = "are_you_sure" if row["key"].startswith("ays") else "answer"
        r = data[f][int(row["row"])]
        if qhash(r["base"]["question"]) != row["qhash"]:
            bad += 1
        labels[row["key"]][int(row["row"])] = row["label"]
    out = {"hash_mismatches": bad}
    for key in PLAN:
        want = sample(key, data); got = labels.get(key, {})
        c = collections.Counter(got[i] for i in want if i in got)
        n = sum(c.values()); k = sum(v for l, v in c.items() if l in DEFECT)
        out[key] = {"sample_matches_seed": sorted(got) == want, "n": n, "labels": dict(c),
                    "defects": k, "wilson95": wilson(k, n),
                    "defects_plus_unsure": k + c.get("unsure", 0), "wilson95_with_unsure": wilson(k + c.get("unsure", 0), n)}
    mc = [k for k in PLAN if k.startswith("ays") and k != "ays:truthful_qa_mc"]
    k = sum(out[x]["defects"] for x in mc); n = sum(out[x]["n"] for x in mc)
    out["ays_aqua_mmlu_math_pooled"] = {"defects": k, "n": n, "wilson95": wilson(k, n)}
    tq = labels.get("tqa_incorrect_review", {})
    out["truthful_incorrect_answer_review"] = dict(collections.Counter(tq.values()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data"); ap.add_argument("--out", default=str(HERE / "sharma_checks.json"))
    a = ap.parse_args(); cache = Path(a.cache)
    data, sha256 = {}, {}
    for f in ("answer", "are_you_sure", "feedback"):
        b = fetch(URL + f"datasets/{f}.jsonl", cache / "sharma" / f"{f}.jsonl")
        data[f] = jl(b); sha256[f] = hashlib.sha256(b).hexdigest()
    nb = json.loads(fetch(URL + "example.ipynb", cache / "sharma" / "example.ipynb"))
    utils = fetch(URL + "utils.py", cache / "sharma" / "utils.py").decode()
    tqa = list(csv.DictReader(fetch(TQA_URL, cache / "truthfulqa" / "TruthfulQA.csv").decode().splitlines()))
    mwe = {n: jl(fetch(MWE_URL + n + ".jsonl", cache / "mwe_github" / f"{n}.jsonl")) for n in MWE}
    out = {"pins": {"sycophancy_eval": SHA, "truthfulqa": TQA_SHA, "anthropics_evals": G_SHA}, "sha256": sha256,
           "census": census(data), "cross_with_mwe": cross_mwe(data, mwe), "notebook": notebook_scoring(nb, utils),
           "references": reference_checks(data, tqa), "hand_audit": hand_audit(data, HERE / "sharma_hand_labels.csv")}
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
