"""Validator, claims 3-4: human SeqQA lines by subset and scoring rule, and exposure bounds.

Own code, written without reading scripts/exposure.py. Human numbers are typed from the LAB-Bench
paper v3 (arXiv 2407.10362v3) Tables 2 (accuracy), 3 (precision) and 4 (coverage), pp. 23-25, human
column, full set (public + private, 50 per subtask; humans covered 64% of SeqQA items, Table 1).
Number of answer options k per subtask is read from the 2024-07-16 HF release (the items humans saw
were the 2024 generation).

Human forced-choice value = a + (1 - c) * q, q = accuracy of the unsure best guesses (App. E.4 did
not score them): q = 0 (paper, "unsure = wrong"), q = 1/k (chance credit, US/UK AISI rule), q = p
(guesses as good as sure answers; upper plausible value, parent validator).

Bounds for a published overall score s with cue share w:
  cue-free accuracy x satisfies s = w*c + (1-w)*x with c in [0, 1], so
  x in [ (s - w)/(1 - w) , min(1, s/(1 - w)) ]   (A = lower end: every cue item correct)
  B = s (cue items at the same accuracy as the rest).
Run: ../lab-bench/data/.venv/bin/python -I validation/v2_bounds.py
"""
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"

# subtask: (accuracy, precision, coverage) -- paper v3 Tables 2-4, human column
H = {
    "ORF-seq-AAid": (0.91, 0.91, 1.00),
    "ORF-seq-AAseq": (0.88, 0.88, 1.00),
    "ORF-seq-numlen": (0.31, 0.43, 0.72),
    "ORF-transeff": (0.38, 0.75, 0.50),
    "PCR-gene-enzprimers": (0.83, 0.88, 0.93),
    "PCR-gene-gibshindprimers": (0.71, 0.79, 0.90),
    "PCR-gene-gibssmaprimers": (0.73, 0.78, 0.94),
    "PCR-geneprimers-enz": (0.94, 0.98, 0.96),
    "PCR-len-primers": (0.90, 0.90, 1.00),
    "PCR-primers-len": (0.90, 0.90, 1.00),
    "PCR-seq-enzprimers": (0.81, 0.83, 0.98),
    "PCR-seq-primers": (1.00, 1.00, 1.00),
    "Prop-seq-gcpercent": (1.00, 1.00, 1.00),
    "RE-seq-lenfrags": (0.83, 0.86, 0.96),
    "RE-seq-numfrags": (0.71, 0.74, 0.96),
}
S6 = ["ORF-seq-AAseq", "PCR-gene-enzprimers", "PCR-seq-enzprimers", "PCR-gene-gibshindprimers",
      "PCR-gene-gibssmaprimers", "Prop-seq-gcpercent"]
S7 = S6 + ["RE-seq-numfrags"]
ALL = list(H)
F9 = [s for s in ALL if s not in S6]
F8 = [s for s in ALL if s not in S7]
# subtasks whose items were regenerated after the human baseline (2025-02 and/or 2025-09 releases)
REGEN = ["PCR-gene-enzprimers", "PCR-geneprimers-enz", "PCR-seq-enzprimers", "RE-seq-lenfrags", "RE-seq-numfrags"]


def ks():
    df = pd.read_parquet(DATA / "hfrev_7268767a" / "SeqQA" / "train-00000-of-00001.parquet")
    out = {}
    for r in df.itertuples():
        st = r.subtask.replace("-v1-public", "")
        out.setdefault(st, set()).add(1 + len(r.distractors))
    return {k: (min(v) if len(v) == 1 else sorted(v)) for k, v in out.items()}


def human(sub, K):
    vals = {"unsure_wrong": [], "chance_credit": [], "guess_at_precision": []}
    for s in sub:
        a, p, c = H[s]
        vals["unsure_wrong"].append(a)
        vals["chance_credit"].append(a + (1 - c) / K[s])
        vals["guess_at_precision"].append(a + (1 - c) * p)
    return {k: round(sum(v) / len(v), 4) for k, v in vals.items()}


# (label, s, read error, w-era, human rule the document itself used, source, statement)
CLAIMS = [
    ("US/UK AISI: Sonnet 3.5 (new), Python tools", 0.86, 0.01, "2024", "chance_credit",
     "NIST joint report 2024-11, Fig. 4.2 p. 8 (read from figure); forced choice; 600 items stated (s3.1)",
     "slightly better than human experts on SeqQA"),
    ("US/UK AISI: o1, Python tools", 0.77, 0.02, "2024", "chance_credit",
     "NIST o1 report 2024-12, Fig. 10.1 (read from figure, value taken from audit inventory, not re-read)",
     "approaching the performance of human experts"),
    ("Claude 4 card: Opus 4, best of 0/5/10-shot", 0.79, 0.02, "2025", "unsure_wrong",
     "Claude 4 card Fig. 7.2.4.7.A p. 100 (read from figure; best of three shot settings)",
     "reaches or exceeds the human baseline"),
    ("Sonnet 4.5 card: Sonnet 4.5, 10-shot", 0.780, 0.0, "2025", "unsure_wrong",
     "Sonnet 4.5 card Fig. 9.2.4.4.A p. 133 (printed label); same in Opus 4.5 card Fig. 7.2.4.4.A",
     "reached or exceeded the human baseline in 3/4 evaluations"),
    ("Opus 4.5 card: Opus 4.1, 10-shot", 0.785, 0.0, "2025", "unsure_wrong",
     "Opus 4.5 card Fig. 7.2.4.4.A p. 126 (printed label)", "(figure only)"),
    ("Opus 4.5 card: Opus 4.5, 10-shot", 0.8517, 0.0, "2025", "unsure_wrong",
     "Opus 4.5 card s7.2.4.4 p. 126 (text); 0.8517 = 511/600", "every evaluation except FigQA exceeded the human baseline"),
    ("Concordia 2025-Q4: Gemini 3 Pro Preview", 0.87, 0.0, "2025", "unsure_wrong",
     "airiskmonitor.net 2025-Q4 (web text, re-read 2026-11-20)", "first instance of models surpassing human experts ... (87 vs 79)"),
    ("Concordia 2026-Q1: GPT-5.4", 0.875, 0.0, "2025", "unsure_wrong",
     "airiskmonitor.net 2026-Q1 (web text, re-read 2026-11-20)", "only the GPT and Gemini model families exceed the human expert baseline of 79"),
    ("Concordia 2026-Q2: GPT-5.5", 0.915, 0.0, "2025", "unsure_wrong",
     "airiskmonitor.net 2026-Q2 (web text, re-read 2026-11-20)", "11 models now exceed human-expert level"),
    ("Concordia 2026-Q3: GPT 6 Astra", 0.947, 0.0, "2025", "unsure_wrong",
     "airiskmonitor.net 2026-Q3 (web text, re-read 2026-11-20)", "21 models ... now exceed human-expert level"),
    ("Meta Muse Spark report: Muse Spark, tools, no abstention", 0.973, 0.0, "2025", None,
     "arXiv 2606.12429 p. 5 table, s2.1.1.1", "on par with or above that of other models (no numeric human comparison in text)"),
    ("Meta Muse Spark report: GPT-5.4, tools", 0.965, 0.0, "2025", None, "arXiv 2606.12429 p. 5", "(same)"),
    ("Meta Muse Spark report: Gemini 3.1 Pro, tools", 0.937, 0.0, "2025", None, "arXiv 2606.12429 p. 5", "(same)"),
]


def main():
    K = ks()
    hl = {name: human(sub, K) for name, sub in
          [("all15", ALL), ("S6", S6), ("F9", F9), ("S7_2024", S7), ("F8_2024", F8),
           ("F9_not_regenerated", [s for s in F9 if s not in REGEN]),
           ("F8_not_regenerated", [s for s in F8 if s not in REGEN])]}
    w = {"2024": 7 * 40 / 600, "2025": 6 * 40 / 600}
    Fh = {"2024": hl["F8_2024"], "2025": hl["F9"]}
    rows = []
    for lab, s, err, era, rule, src, stmt in CLAIMS:
        ww = w[era]
        A = (s - ww) / (1 - ww)
        up = min(1.0, s / (1 - ww))
        Aerr = err / (1 - ww)
        r = {"label": lab, "s": s, "read_error": err, "w": round(ww, 4), "source": src, "statement": stmt,
             "doc_rule": rule,
             "A_lower": round(A, 4), "A_range_with_read_error": [round(A - Aerr, 4), round(A + Aerr, 4)],
             "identified_range_cue_free": [round(A, 4), round(up, 4)], "B": s}
        for rr in ("unsure_wrong", "chance_credit", "guess_at_precision"):
            h = Fh[era][rr]
            r[f"human_cuefree_{rr}"] = h
            r[f"A_minus_h_{rr}"] = round(A - h, 4)
            r[f"B_minus_h_{rr}"] = round(s - h, 4)
        # like-for-like with the document's own rule
        if rule:
            h = Fh[era][rule]
            r["A_minus_h_doc_rule"] = round(A - h, 4)
            r["overall_minus_all15_doc_rule"] = round(s - hl["all15"][rule], 4)
        rows.append(r)
    out = {"k_per_subtask_2024": K, "human_lines": hl, "w": w, "claims": rows,
           "regenerated_after_human_baseline": REGEN}
    (HERE / "v2_bounds.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(hl, indent=1))
    for r in rows:
        print(f"{r['label'][:48]:48s} s={r['s']:.4f} w={r['w']:.3f} A={r['A_lower']:.3f} "
              f"A-h(uw/cc/pr)={r['A_minus_h_unsure_wrong']:+.3f}/{r['A_minus_h_chance_credit']:+.3f}/{r['A_minus_h_guess_at_precision']:+.3f} "
              f"B-h(uw/cc/pr)={r['B_minus_h_unsure_wrong']:+.3f}/{r['B_minus_h_chance_credit']:+.3f}/{r['B_minus_h_guess_at_precision']:+.3f} "
              f"Arange={r['A_range_with_read_error']}")


if __name__ == "__main__":
    main()
