"""Analysis 2 (prereg.md): LABBench2 format and grading, from the public GitHub harness and paper
reports at EdisonScientific/labbench2 @ 5eafca56 (the HF dataset is gated and was not accessed).

(i) For every report file (all tags, modes, models): number of cases and number whose question
    contains a lettered option list. (ii) Post hoc lead (seen before prereg): SeqQA2 per-type share of
    the most common expected output (a constant-answer ceiling), and for mutation_restriction, per
    model run in inject mode, accuracy split by whether the key is "None" and the rate of answering
    "None". Merges *_retry files over the original as the harness does (later cases replace earlier).
No item text is written out.

Run: ../lab-bench/data/.venv/bin/python -I scripts/lb2.py
"""
from __future__ import annotations

import collections
import glob
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
GH = HERE / "data" / "labbench2_gh"
COMMIT = "5eafca562b9f162ff6074197396858a363083936"
LETTERED = re.compile(r"(?m)^\s*\(?[A-H][\).:]\s+\S")
ANS = re.compile(r"<answer>(.*?)</answer>", re.S | re.I)


def load(f):
    return json.loads(Path(f).read_text())


def merged(base):
    """Original report patched by its _retry files, keyed by case id."""
    files = sorted(glob.glob(base.replace(".json", "*.json")), key=len)
    files = [f for f in files if re.fullmatch(re.escape(base[:-5]) + r"(_retry)*\.json", f)]
    cases = {}
    for f in files:
        for c in load(f)["cases"]:
            cases[c["id"]] = c
    return cases


def main():
    out = {"commit": COMMIT, "format": {}, "seqqa2_constant": {}, "mutation_restriction": {}}
    reps = sorted(glob.glob(str(GH / "assets/reports_paper/*/*/*.json")))
    out["n_report_files"] = len(reps)
    tot = collections.Counter()
    for f in reps:
        d = load(f)
        tag, mode = Path(f).parts[-3], Path(f).parts[-2]
        n = len(d["cases"])
        mc = sum(bool(LETTERED.search(c["question"])) for c in d["cases"])
        key = f"{tag}/{mode}"
        e = out["format"].setdefault(key, {"files": 0, "max_cases": 0, "cases_with_lettered_list": 0})
        e["files"] += 1
        e["max_cases"] = max(e["max_cases"], n)
        e["cases_with_lettered_list"] = max(e["cases_with_lettered_list"], mc)
        tot["cases"] += n
        tot["lettered"] += mc
    out["format_totals"] = dict(tot)
    # unique task ids across all reports, per tag
    ids = collections.defaultdict(set)
    for f in reps:
        for c in load(f)["cases"]:
            ids[c["tag"]].add(c["id"])
    out["unique_ids_per_tag"] = {k: len(v) for k, v in sorted(ids.items())}
    out["unique_ids_total"] = sum(len(v) for v in ids.values())

    # (ii) constant-answer ceiling per SeqQA2 type (inject mode, one report is enough: same tasks)
    ref = load(GH / "assets/reports_paper/seqqa2/inject/claude-opus-4-6.json")["cases"]
    by = collections.defaultdict(list)
    for c in ref:
        by[c["type"]].append((c["expected_output"] or "").strip())
    for t, v in sorted(by.items()):
        top, k = collections.Counter(v).most_common(1)[0]
        out["seqqa2_constant"][t] = {"n": len(v), "distinct_expected": len(set(v)), "modal_share": round(k / len(v), 4),
                                     "modal_is_None": top == "None",
                                     "modal_sha1": hashlib.sha1(top.encode()).hexdigest()[:10]}
    # mutation_restriction per model (inject mode)
    for f in sorted(glob.glob(str(GH / "assets/reports_paper/seqqa2/inject/*.json"))):
        if "_retry" in f:
            continue
        cases = [c for c in merged(f).values() if c["type"] == "mutation_restriction"]
        if not cases:
            continue
        none_key = [c for c in cases if (c["expected_output"] or "").strip().lower() == "none"]
        other = [c for c in cases if c not in none_key]

        def score(c):
            return float(c["scores"]["HybridEvaluator"]["value"])

        def said_none(c):
            m = ANS.findall(c["llm_answer"] or "")
            return bool(m) and m[-1].strip().lower() == "none"
        out["mutation_restriction"][Path(f).stem] = {
            "n": len(cases), "n_key_none": len(none_key),
            "acc": round(sum(map(score, cases)) / len(cases), 4),
            "acc_key_none": round(sum(map(score, none_key)) / max(1, len(none_key)), 4),
            "acc_key_enzyme": round(sum(map(score, other)) / max(1, len(other)), 4),
            "answered_none_rate": round(sum(map(said_none, cases)) / len(cases), 4),
            "constant_none_baseline": round(len(none_key) / len(cases), 4),
        }
    # whole-subset SeqQA2 means, per model run, inject mode (for context)
    out["seqqa2_inject_means"] = {Path(f).stem: round(sum(float(c["scores"]["HybridEvaluator"]["value"]) for c in merged(f).values()) / len(merged(f)), 4)
                                  for f in sorted(glob.glob(str(GH / "assets/reports_paper/seqqa2/inject/*.json"))) if "_retry" not in f}
    out["grading_dispatch"] = {
        "evals/evaluators.py:212": "cloning and seqqa2 -> RewardFunctionEvaluator (computed validators)",
        "evals/evaluators.py:131-175": "seqqa2: validator from registry by type, answer parsed by regex",
        "evals/evaluators.py:105": "cloning: cloning_reward against assembled ground truth",
        "evals/evaluators.py:218": "figqa2/tableqa2/suppqa2 -> LLM judge, exact-match prompt",
        "evals/evaluators.py:72-73": "LLM judge verdict 'unsure' scored 0.0",
        "src/labbench2/seqqa2/validate_mutation_restriction.py:119": "answer 'None' parsed as the empty set",
    }
    # lettered-list hits: which task ids (all false positives must be read by hand; ids only)
    hits = collections.Counter()
    for f in reps:
        for c in load(f)["cases"]:
            if LETTERED.search(c["question"]):
                hits[f'{c["tag"]}:{c["id"]}'] += 1
    out["lettered_hits_by_task"] = dict(hits)
    # refusal route: llm_answer == "[REFUSED]" per model file, seqqa2 inject and all SeqQA2 types
    ref_tab = {}
    for f in sorted(glob.glob(str(GH / "assets/reports_paper/seqqa2/inject/*.json"))):
        if "_retry" in f:
            continue
        cs = list(merged(f).values())
        r = [c for c in cs if (c["llm_answer"] or "").strip() == "[REFUSED]"]
        ref_tab[Path(f).stem] = {"n": len(cs), "refused": len(r), "refused_by_type": dict(collections.Counter(c["type"] for c in r))}
    out["seqqa2_inject_refusals"] = ref_tab
    print(json.dumps(ref_tab, indent=0))
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "lb2.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("n_report_files", "format_totals", "unique_ids_per_tag", "unique_ids_total")}, indent=1))
    print(json.dumps(out["seqqa2_constant"], indent=0)[:3000])
    print(json.dumps(out["mutation_restriction"], indent=1))
    print(out["seqqa2_inject_means"])


if __name__ == "__main__":
    main()
