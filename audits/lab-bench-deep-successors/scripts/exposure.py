"""Analyses 3-4 (prereg.md): human SeqQA lines and arithmetic exposure bounds for published SeqQA scores.

Human numbers come from the parent's parse of the paper's Tables 2-4 (../lab-bench/results/published.json,
full set, unsure = wrong). Cue share w comes from results/versions.json: the share of public SeqQA items
in subtasks that carry the options-only cue in the HF revision current at the run date (600 items,
40 per subtask, so per-item and per-subtask weighting coincide). Item set and weighting are assumed
where the document does not state them (column 'assumed').

Reading A: cue subtasks all correct  -> non-cue accuracy = (s - w) / (1 - w).
Reading B: cue subtasks at the rest's accuracy -> non-cue accuracy = s.
These are bounds on arithmetic, not evidence that any model used the cue.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PUB = json.loads((HERE.parent / "lab-bench" / "results" / "published.json").read_text())
VER = json.loads((HERE / "results" / "versions.json").read_text())
S6 = ["ORF-seq-AAseq", "PCR-gene-enzprimers", "PCR-seq-enzprimers", "PCR-gene-gibshindprimers",
      "PCR-gene-gibssmaprimers", "Prop-seq-gcpercent"]
MEAN_K = {}  # mean options per subtask from the pin (for chance credit)

# (label, model, score, date of run/document, human line used, claim text, source, how the score was read)
CLAIMS = [
    ("US/UK AISI, Sonnet 3.5 (new), Python tools", "claude-3.5-sonnet-new", 0.86, "2024-11", 0.81,
     "\"slightly better than human experts on SeqQA\"; human = paper accuracy with chance credit for abstentions",
     "NIST joint report 2024-11-19, Fig. 4.2, p. 8", "read from a figure (by eye)"),
    ("US/UK AISI, o1, Python tools", "o1", 0.77, "2024-12", 0.81,
     "\"approaching the performance of human experts\"", "NIST joint report o1 2024-12, Fig. 10.1, p. 19",
     "read from a figure (by eye)"),
    ("Anthropic Claude 4 card, Opus 4 best k-shot", "claude-opus-4", 0.79, "2025-05", 0.79,
     "\"reaches or exceeds the human baseline\"", "Claude 4 system card §7.2.4.7, Fig. 7.2.4.7.A, p. 100",
     "read from a figure (by eye)"),
    ("Anthropic Opus 4.5 card, Opus 4.1", "claude-opus-4.1", 0.785, "2025-11", 0.79,
     "(figure only)", "Opus 4.5 card Fig. 7.2.4.4.A, p. 126", "bar label printed in figure"),
    ("Anthropic Opus 4.5 card, Sonnet 4.5", "claude-sonnet-4.5", 0.780, "2025-11", 0.79,
     "Sonnet 4.5 card: \"reached or exceeded the human baseline in 3/4 evaluations\"",
     "Opus 4.5 card Fig. 7.2.4.4.A, p. 126; Sonnet 4.5 card §9.2.4.4", "bar label printed in figure"),
    ("Anthropic Opus 4.5 card, Opus 4.5", "claude-opus-4.5", 0.8517, "2025-11", 0.79,
     "\"every evaluation except FigQA exceeded the human baseline\"", "Opus 4.5 card §7.2.4.4, p. 126", "text"),
    ("Anthropic Opus 4.1 addendum", "claude-opus-4.1", 0.71, "2025-08", None, "(no human comparison in text)",
     "Opus 4.1 addendum §6.3.1.2", "text"),
    ("Anthropic Haiku 4.5 card", "claude-haiku-4.5", 0.66, "2025-10", None, "(no human comparison in text)",
     "Haiku 4.5 card §6.2.3.1", "text"),
    ("Concordia AI 2025-Q4", "gemini-3-pro-preview", 0.87, "2025-12", 0.79,
     "\"first instance of models surpassing human experts in sequence understanding (87 vs 79)\"",
     "airiskmonitor.net report 2025-Q4", "text"),
    ("Concordia AI 2026-Q1", "gpt-5.4", 0.875, "2026-03", 0.79, "human expert baseline of 79",
     "airiskmonitor.net report 2026-Q1 (via delegated reading)", "text"),
    ("Concordia AI 2026-Q2", "gpt-5.5", 0.915, "2026-06", 0.79, "\"11 models now exceed human-expert level\"",
     "airiskmonitor.net report 2026-Q2 (via delegated reading)", "text"),
    ("Concordia AI 2026-Q3", "gpt-6-astra", 0.947, "2026-09", 0.79,
     "\"On LAB-Bench-SeqQA, 21 models (+11 this quarter) now exceed human-expert level\"",
     "airiskmonitor.net report 2026-Q3", "text"),
    ("Meta Muse Spark report, Python tools, no abstention", "muse-spark", 0.973, "2026-05", None,
     "expert baseline drawn in Fig. 3; value not mappable from the extracted figure",
     "arXiv 2606.12429 summary table p. 5, §2.1.1.1", "text"),
    ("Meta Muse Spark report", "gpt-5.4", 0.965, "2026-05", None, "(same)", "arXiv 2606.12429 p. 5", "text"),
    ("Meta Muse Spark report", "gemini-3.1-pro", 0.937, "2026-05", None, "(same)", "arXiv 2606.12429 p. 5", "text"),
]


def cue_share(date: str) -> tuple[float, list[str], str]:
    """Share of the 15 equal-size subtasks carrying the cue in the HF revision current at `date`."""
    order = sorted(((v["date"], k) for k, v in VER["sources"].items()))
    cur = order[0][1]
    for d, k in order:
        if d[:7] <= date:
            cur = k
    s = VER["sources"][cur]
    carrying = s["S_carrying_cue"] + s["F_carrying_cue"]
    return len(carrying) / s["n_subtasks"], carrying, cur


def main():
    acc = PUB["tables"]["accuracy"]
    cov = PUB["tables"]["coverage"]
    seq = {k.replace("SeqQA_", ""): v["human"] for k, v in acc.items() if k.startswith("SeqQA_")}
    seqc = {k.replace("SeqQA_", ""): v["human"] for k, v in cov.items() if k.startswith("SeqQA_")}
    kmean = {st: e["chance"] for st, e in VER["sources"]["hf@5c77cec6"]["subtasks"].items()}  # 1/k
    chance_credit = {st: seq[st] + (1 - seqc[st]) * kmean[st] for st in seq}
    F9 = [s for s in seq if s not in S6]

    def mean(d, keys):
        return round(sum(d[k] for k in keys) / len(keys), 4)
    human = {
        "all15_unsure_wrong": mean(seq, list(seq)), "S6_unsure_wrong": mean(seq, S6), "F9_unsure_wrong": mean(seq, F9),
        "all15_chance_credit": mean(chance_credit, list(seq)), "S6_chance_credit": mean(chance_credit, S6),
        "F9_chance_credit": mean(chance_credit, F9),
        "F8_unsure_wrong_2024_split": mean(seq, [s for s in F9 if s != "RE-seq-numfrags"]),
        "note": "paper Tables 2 and 4, full set (50 per subtask), mean over subtasks; chance credit = acc + (1-cov)/k, k from public items",
    }
    rows = []
    for label, model, s, date, line, claim, src, how in CLAIMS:
        w, carrying, rev = cue_share(date)
        a = (s - w) / (1 - w)
        hF = human["F9_unsure_wrong"] if len(carrying) == 6 else human["F8_unsure_wrong_2024_split"]
        rows.append({
            "label": label, "model": model, "score": s, "date": date, "human_line_used": line, "claim": claim,
            "source": src, "score_read_as": how, "revision_assumed": rev, "cue_subtasks": carrying,
            "cue_share_w": round(w, 4), "assumed": "600 public items, 40 per subtask, all 15 subtasks (not stated in the document)",
            "nonCue_readingA_all_cue_correct": round(a, 4), "nonCue_readingB_same_accuracy": s,
            "human_nonCue_unsure_wrong": hF,
            "A_minus_human_nonCue": round(a - hF, 4), "B_minus_human_nonCue": round(s - hF, 4),
            "score_minus_line": None if line is None else round(s - line, 4),
        })
    out = {"human_seqqa": human, "claims": rows}
    (HERE / "results" / "exposure.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(human, indent=1))
    for r in rows:
        print(f'{r["label"][:48]:48s} {r["model"]:22s} s={r["score"]:.3f} w={r["cue_share_w"]:.3f} A={r["nonCue_readingA_all_cue_correct"]:.3f} '
              f'hF={r["human_nonCue_unsure_wrong"]:.3f} A-h={r["A_minus_human_nonCue"]:+.3f} B-h={r["B_minus_human_nonCue"]:+.3f} line={r["human_line_used"]}')


if __name__ == "__main__":
    main()
