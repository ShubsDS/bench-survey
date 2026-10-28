"""Cybench check 6: how answers are scored, and what a guess from the answer format earns.

Static only. Reads the 31 task metadata files committed at the pinned Cybench commit (the 9
GlacierCTF tasks have no metadata in the repository) and the scorer code of both harnesses.

Measures:
  1. Scorer lines: the original agent compares the text after "Answer:" to the subtask answer with
     `==` (after strip); the inspect_evals port uses inspect_ai `includes()` (case-folded substring).
  2. How much of each answer its answer_format shows (non-* characters), and how many answers the
     format leaves at most 9 characters to fill.
  3. Two guessers that never look at the task files beyond the directory listing the harness
     already prints in the prompt:
       - mask majority: answer with the most common answer among other tasks' subtasks that have
         the identical answer_format (leave one task out);
       - file-name guess: when the question asks for a file and the mask matches the name of a
         file in the agent's directory (from init_script.sh), answer with that name (credit 1/k
         for k matching names).
     Scored as the paper's subtask performance (fraction of subtasks correct, macro-averaged over
     tasks), with the final flag subtask counted as wrong.
  4. Whether earlier subtask answers, which the harness prints after a failed subtask ("here is
     the answer"), contain the final flag in pieces.
  5. Characters of the final flag shown by its answer_format, which the unguided prompt includes.

Flag strings are compared but never written to the output.

Usage:
  python -I check_scoring.py --cache ../data [--leakage leakage_checks.json] [--out scoring_checks.json]
"""
import argparse, collections, json, re, subprocess
from pathlib import Path

CYBENCH_SHA = "ca483c6443f17a20ba7d6bac3d274859a1721e51"
INSPECT_SHA = "e0d554e5deb7cdcbe8b481c225315f2d2600b4a1"
INSPECT_AI_SHA = "848975e870b189806109947e4f7b0246757ed6ee"
PUBLISHED_SUBTASK_PERF = {  # Cybench paper (arXiv 2408.08926v4) Table 2, single attempt, macro over 40 tasks
    "OpenAI o1-preview": 0.468, "Claude 3.5 Sonnet": 0.439, "Gemini 1.5 Pro": 0.117, "Llama 3 70b Chat": 0.082}
SCORER_LINES = {
    "cybench/agent/agent.py": ["if iteration_result.execution_output.stdout == subtask.answer",
                               'answer = re.search(r"ANSWER:\\s(.*)?", response_text, re.DOTALL | re.IGNORECASE)',
                               "f\"we will begin the next subtask.\\n\\nAnswer: {subtask.answer}\""],
    "cybench/run_task.py": ['answer_format=self.metadata["subtasks"][-1]["answer_format"],'],
    "inspect_evals/src/inspect_evals/cybench/cybench.py": ["scorer=includes(),", "attempts=3,"],
}
FILE_Q = re.compile(r"\b(file|executable|binary)\b", re.I)


def masked(fmt):
    return sum(c == "*" for c in fmt)


def mask_ok(fmt, ans):
    return len(fmt) == len(ans) and all(f == "*" or f == a for f, a in zip(fmt, ans))


def covered(flag, pieces, k=4):
    """Fraction of flag characters inside some substring (length >= k) shared with an earlier answer."""
    cov = [False] * len(flag)
    for p in pieces:
        for i in range(len(flag)):
            for j in range(len(flag), i + k - 1, -1):
                if flag[i:j] in p:
                    for t in range(i, j):
                        cov[t] = True
                    break
    return sum(cov) / len(flag) if flag else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="../data")
    ap.add_argument("--leakage", default="leakage_checks.json", help="output of check_leakage.py (agent file lists)")
    ap.add_argument("--out", default="scoring_checks.json")
    a = ap.parse_args()
    cache = Path(a.cache).resolve()
    cb = cache / "cybench"
    head = subprocess.run(["git", "-C", str(cb), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    assert head == CYBENCH_SHA, "run check_leakage.py first; it fetches the pinned repositories"

    lines_found = {}
    for f, needles in SCORER_LINES.items():
        txt = (cache / f).read_text()
        lines_found[f] = {n: n in txt for n in needles}
    ia = cache / "inspect_ai_src" / "_match.py"
    if not ia.exists():
        import urllib.request
        ia.parent.mkdir(parents=True, exist_ok=True)
        ia.write_bytes(urllib.request.urlopen(
            f"https://raw.githubusercontent.com/UKGovernmentBEIS/inspect_ai/{INSPECT_AI_SHA}/src/inspect_ai/scorer/_match.py", timeout=60).read())
    iat = ia.read_text()
    lines_found["inspect_ai/scorer/_match.py"] = {n: n in iat for n in
        ["def includes(ignore_case: bool = True) -> Scorer:", "return value, target in value"]}

    leak = json.loads(Path(a.leakage).read_text())
    agent_files = {r["task"]: r.get("agent_files", []) for r in leak["original_tasks"] if r["present"]}

    tasks = [l.strip() for l in (cb / "task_list.txt").read_text().splitlines() if l.strip()]
    subs = []  # (task, idx, is_final, question, answer, fmt)
    for t in tasks:
        p = cb / t / "metadata" / "metadata.json"
        if not p.exists():
            continue
        m = json.loads(p.read_text())
        for i, s in enumerate(m["subtasks"]):
            subs.append({"task": t, "i": i, "final": i == len(m["subtasks"]) - 1, "q": s["question"],
                         "a": s["answer"].strip(), "fmt": s["answer_format"]})
    tasks_present = sorted({s["task"] for s in subs})

    # 2. format disclosure
    for s in subs:
        s["fmt_matches_answer"] = mask_ok(s["fmt"], s["a"])
        s["shown_chars"] = len(s["fmt"]) - masked(s["fmt"])
        s["shown_frac"] = s["shown_chars"] / max(1, len(s["a"]))
    nonfinal = [s for s in subs if not s["final"]]

    # 3a. mask majority, leave one task out
    by_fmt = collections.defaultdict(list)
    for s in nonfinal:
        by_fmt[s["fmt"]].append(s)
    for s in nonfinal:
        others = collections.Counter(o["a"] for o in by_fmt[s["fmt"]] if o["task"] != s["task"])
        s["mask_majority_guess_correct"] = bool(others) and others.most_common(1)[0][0] == s["a"]
    # 3b. file-name guess from the agent's directory listing
    for s in nonfinal:
        names = sorted({Path(x.split("!")[-1]).name for x in agent_files.get(s["task"], [])}
                       | {Path(x).name.rsplit(".zip", 1)[0] for x in agent_files.get(s["task"], []) if "!" not in x})
        cands = [n for n in names if mask_ok(s["fmt"], n)] if FILE_Q.search(s["q"]) else []
        s["file_guess_credit"] = (1 / len(cands)) if s["a"] in cands else 0.0
        s["file_guess_candidates"] = len(cands)
    for s in subs:
        if s["final"]:
            s["mask_majority_guess_correct"] = False; s["file_guess_credit"] = 0.0

    def macro(key):
        per = collections.defaultdict(list)
        for s in subs:
            v = s[key]
            per[s["task"]].append(float(v))
        return sum(sum(v) / len(v) for v in per.values()) / len(per)

    for s in subs:
        s["combined"] = max(float(s["mask_majority_guess_correct"]), s["file_guess_credit"])

    # 4. flag pieces in earlier answers (printed by the harness after a failed subtask)
    pieces = {}
    for t in tasks_present:
        ts = [s for s in subs if s["task"] == t]
        flag = ts[-1]["a"]
        prev = [s["a"] for s in ts[:-1]]
        c = covered(flag, prev)
        pieces[t] = {"flag_chars_covered_by_earlier_answers": round(c, 3),
                     "earlier_subtasks_containing_flag_text": [s["i"] + 1 for s in ts[:-1] if len(s["a"]) >= 4 and s["a"] in flag]}

    # 5. final flag formats
    final_fmt = {}
    for s in subs:
        if s["final"]:
            inner_f = s["fmt"][s["fmt"].find("{") + 1:-1] if "{" in s["fmt"] else s["fmt"]
            final_fmt[s["task"]] = {"format_matches_flag": s["fmt_matches_answer"], "flag_len": len(s["a"]),
                                    "shown_chars_inside_braces": sum(c != "*" for c in inner_f),
                                    "inside_braces_len": len(inner_f)}

    case_risky = [s for s in nonfinal if any(c.isupper() for c in s["a"]) and any(c.islower() for c in s["a"])
                  and not re.search(r"capital", s["q"], re.I)]
    summary = {
        "scorer_lines_present": lines_found,
        "tasks_with_metadata": len(tasks_present),
        "subtasks_total": len(subs), "subtasks_nonfinal": len(nonfinal),
        "tasks_with_only_the_flag_subtask": sum(1 for t in tasks_present if sum(s["task"] == t for s in subs) == 1),
        "format_does_not_match_answer": [(s["task"].split("/")[-1], s["i"] + 1) for s in subs if not s["fmt_matches_answer"]],
        "nonfinal_mask_length_le_3": sum(masked(s["fmt"]) <= 3 for s in nonfinal),
        "nonfinal_single_char_mask": sum(masked(s["fmt"]) == 1 for s in nonfinal),
        "nonfinal_format_shows_ge_half_of_answer": sum(s["shown_frac"] >= 0.5 for s in nonfinal),
        "nonfinal_mask_majority_correct": sum(s["mask_majority_guess_correct"] for s in nonfinal),
        "nonfinal_file_guess_credit": round(sum(s["file_guess_credit"] for s in nonfinal), 2),
        "nonfinal_combined_credit": round(sum(s["combined"] for s in nonfinal), 2),
        "baseline_subtask_performance_macro": {"mask_majority": round(macro("mask_majority_guess_correct"), 3),
                                               "file_guess": round(macro("file_guess_credit"), 3),
                                               "combined": round(macro("combined"), 3)},
        "published_subtask_performance_macro_40_tasks": PUBLISHED_SUBTASK_PERF,
        "tasks_where_earlier_answers_cover_flag_ge_0.9": [t for t, v in pieces.items() if v["flag_chars_covered_by_earlier_answers"] >= 0.9],
        "tasks_where_earlier_answers_cover_flag_gt_0": {t.split("/")[-1]: v["flag_chars_covered_by_earlier_answers"] for t, v in pieces.items() if v["flag_chars_covered_by_earlier_answers"] > 0},
        "final_flag_format_shown_chars_inside_braces_total": sum(v["shown_chars_inside_braces"] for v in final_fmt.values()),
        "final_flag_formats_with_shown_chars_inside_braces": {t.split("/")[-1]: f'{v["shown_chars_inside_braces"]}/{v["inside_braces_len"]}' for t, v in final_fmt.items() if v["shown_chars_inside_braces"]},
        "nonfinal_mixed_case_answers_without_case_instruction": len(case_risky),
    }
    flags = {s["task"]: s["a"] for s in subs if s["final"]}
    for s in subs:  # earlier answers that are pieces of the flag are redacted like the flag itself
        s["redact"] = s["final"] or (len(s["a"]) >= 4 and s["a"] in flags[s["task"]])
    rows = [{k: v for k, v in s.items() if not (s["redact"] and k == "a")} for s in subs]
    for r in rows:
        if r["final"]:
            r.pop("fmt", None)  # the final format is derived from the flag; kept only as counts above
        else:
            r["q"] = r["q"][:160]
            if r["redact"]:
                r.pop("fmt", None)
    out = {"pins": {"cybench": CYBENCH_SHA, "inspect_evals": INSPECT_SHA, "inspect_ai": INSPECT_AI_SHA},
           "summary": summary, "flag_pieces": pieces, "final_flag_formats": final_fmt, "subtasks": rows,
           "mask_majority_hits": [(s["task"].split("/")[-1], s["i"] + 1, s["fmt"], "<redacted>" if s["redact"] else s["a"]) for s in nonfinal if s["mask_majority_guess_correct"]],
           "file_guess_hits": [(s["task"].split("/")[-1], s["i"] + 1, s["fmt"], "<redacted>" if s["redact"] else s["a"], s["file_guess_candidates"]) for s in nonfinal if s["file_guess_credit"]]}
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(summary, indent=1))
    print("mask-majority hits:", out["mask_majority_hits"])
    print("file-guess hits:", out["file_guess_hits"])


if __name__ == "__main__":
    main()
