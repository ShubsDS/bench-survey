"""Validator re-derivation of the human forced-choice range (claim 7).

Human accuracy a = correct-and-sure / N; coverage c = sure / N; precision p = a / c (App. E.4).
Under forced choice the human score is a + (1 - c) * q, where q is the accuracy of the best guesses
on the unsure items (App. E.3: unsure humans were asked for a best guess; it was not scored).
  q = 0       (every unsure guess wrong; below chance): lower bound
  q = 1/k     (unsure guesses at chance)
  q = p       (unsure guesses as good as sure answers)
  q = 1       upper bound
The validator's "plausible range" is q in [1/k, p]: the payout made a right guess worth more than a
wrong one (E.3), so guesses below chance are unlikely, and unsure items are unlikely to be easier
than sure ones. The paper's numbers are rounded to 2 decimals; each a and c is moved by +-0.005.
k: mean substantive options in the public items (refusal option excluded).
Run: data/.venv/bin/python -I validation/v5_human.py
"""
import itertools
import json
from pathlib import Path

import numpy as np

A = Path(__file__).resolve().parent.parent
P = json.load(open(A / "results/published.json"))["tables"]
seq = json.load(open(A / "results/published.json"))["seqqa_mean_of_15_subtasks"]



K = {"FigQA": 1 / 0.223, "ProtocolQA": 1 / 0.233, "CloningScenarios": 1 / 0.226, "SeqQA": 1 / 0.247}


def human(s):
    if s == "SeqQA":
        a, p, c = seq["accuracy"]["human"], seq["precision"]["human"], seq["coverage"]["human"]
    else:
        a, p, c = P["accuracy"][s]["human"], P["precision"][s]["human"], P["coverage"][s]["human"]
    out = {"accuracy": a, "precision": p, "coverage": c, "k": round(K[s], 2)}
    for name, q in [("q0", 0), ("q_chance", 1 / K[s]), ("q_precision", p), ("q1", 1)]:
        vals = [aa + (1 - cc) * q for aa, cc in itertools.product([a - .005, a, a + .005], [c - .005, c, c + .005])]
        out[name] = round(a + (1 - c) * q, 4)
        out[name + "_rounding"] = [round(min(vals), 4), round(max(vals), 4)]
    return out


def wilson(p, n, z=1.96):
    den = 1 + z * z / n
    cc = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(cc - h, 3), round(cc + h, 3)]


H = {s: human(s) for s in K}
claims = [
    ("Opus 4.6 card 2.19.1, FigQA with crop tool", "FigQA", 0.783, 181, "states 'surpasses expert humans, who scored 77%'; item set not stated"),
    ("Opus 4.8 card 8.12.3, FigQA no tools", "FigQA", 0.804, 181, "181 public questions stated; text makes no 'surpasses' claim, the figure shows the paper's human line"),
    ("Opus 4.5 card 7.2.4.4, ProtocolQA", "ProtocolQA", 0.907, 108, "'every evaluation except FigQA exceeded the human baseline'; item set, shots and human number not stated"),
    ("Opus 4.5 card 7.2.4.4, CloningScenarios", "CloningScenarios", 0.758, 33, "same sentence; 10-shot, item set not stated"),
    ("Opus 4.5 card 7.2.4.4, SeqQA", "SeqQA", 0.8517, 600, "same sentence; 10-shot; item set, subtask weighting and human SeqQA number not stated (the paper gives no pooled human SeqQA number)"),
    ("Justen 2025, CloningScenarios", "CloningScenarios", 0.61, 33, "abstract: 'match or exceed expert-level performance'; 33 public items per the auditor's reading, not re-read by the validator"),
]
rows = []
for name, s, score, n, note in claims:
    h = H[s]
    rows.append({"claim": name, "subset": s, "score": score, "n_assumed": n, "wilson": wilson(score, n),
                 "human_acc": h["accuracy"], "human_forced_plausible": [h["q_chance"], h["q_precision"]],
                 "human_forced_bounds": [h["q0"], h["q1"]],
                 "score_minus_chance_guess_human": round(score - h["q_chance"], 4),
                 "score_minus_precision_guess_human": round(score - h["q_precision"], 4),
                 "item_interval_contains_paper_human": bool(wilson(score, n)[0] <= h["accuracy"]),
                 "note": note})
res = {"human": H, "claims": rows}
json.dump(res, open(A / "validation/v5_human.json", "w"), indent=1)
print(json.dumps(res, indent=1))
