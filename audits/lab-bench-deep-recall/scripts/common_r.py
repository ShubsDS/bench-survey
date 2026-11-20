"""Shared items, prompts and parsing for the lab-bench-deep-recall audit.

Reuses the parent audit's pinned data and code by path (audits/lab-bench, read only):
  - items: futurehouse/lab-bench @ 5c77cec6 parquet files, sha256-checked by the parent's
    common.load_items();
  - clusters: the parent's common.clusters() (ProtocolQA protocol title, CloningScenarios
    scenario preamble);
  - prompts for the `full` (parent `forced`) and `opts` arms: the parent's haiku.render(), so
    the parent's Haiku results for those arms can be reused (identical prompts).
Run with: audits/lab-bench/data/.venv/bin/python -I <script>
No item text is written to committed files; raw outputs stay in data/ and inference/cache/.
"""
from __future__ import annotations

import hashlib
import json
import re
import string
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
AUDIT = HERE.parent
REPO = AUDIT.parents[1]
PARENT = REPO / "audits" / "lab-bench"
sys.path.insert(0, str(PARENT / "scripts"))
sys.path.insert(0, str(REPO / "audits" / "tools"))
import common as pcommon  # noqa: E402  (parent)
import haiku as phaiku  # noqa: E402  (parent; render/parse/perm_for only)

DATA = AUDIT / "data"
RESULTS = AUDIT / "results"
ALPHA = string.ascii_uppercase
SYSTEM = phaiku.SYSTEM
# Parent: ProtocolQA bee8b322 was refused by the API usage-policy classifier ([bio]) and is
# dropped from every condition there; we drop it too (content note: skipped and counted).
EXCLUDE = {"bee8b322-2843-4be7-9adc-9e9dbf4c47a4"}

SEQ_RE = re.compile(r"[ACGTNacgtn]{20,}")


def load() -> pd.DataFrame:
    df = pcommon.load_items()
    df = df[df.subset.isin(["ProtocolQA", "CloningScenarios"])].copy()
    df["cluster"] = pcommon.clusters(df).values
    df = df[~df.id.isin(EXCLUDE)].reset_index(drop=True)
    return df.set_index("id", drop=False)


QO_TEMPLATE = """The following is a multiple choice question about biology.
{hidden}
Please answer by responding with the letter of the correct answer.
Think step by step.

Question: {question}

Options:
{answers}

You MUST include the letter of the correct answer within the following tags: [ANSWER] and [/ANSWER].
For example, '[ANSWER]<answer>[/ANSWER]', where <answer> is the correct letter.
Always answer in exactly this format of a single letter between the two tags, even if you are unsure.
We require this because we use automatic parsing."""

HIDDEN = {
    "ProtocolQA": "The protocol that the question refers to has been hidden from you; answer as well as you can without it.",
    "CloningScenarios": "Every DNA sequence in the question has been replaced by [sequence hidden]; answer as well as you can without them.",
}

QGEN_TEMPLATE = """Below is a question from a quiz about troubleshooting laboratory protocols. The protocol itself and the answer options have been hidden from you.

Question: {question}

Give the single most likely fix. Be specific: name the step number(s) of the protocol you would change and the exact change (reagent, amount, time, temperature, speed or other value, with units). If you are unsure, still give your best specific guess.
End your reply with exactly one line of the form
FIX: <step number(s)>; <the change>"""


def mask_sequences(q: str) -> str:
    return SEQ_RE.sub("[sequence hidden]", q)


def question_no_evidence(r) -> str:
    if r.subset == "ProtocolQA":
        return r.question
    return mask_sequences(r.question)


def ordered(r, options: list[str] | None, salt: str):
    subs = options if options is not None else [r.ideal] + list(r.distractors)
    roles = ["key"] + [f"d{i}" for i in range(len(subs) - 1)]
    p = phaiku.perm_for(r.id, len(subs), salt=salt)
    return [subs[i] for i in p], [roles[i] for i in p]


COT_LINE = "Think step by step.\n"
DIRECT_LINE = "Do not explain your reasoning; reply with only the tagged letter.\n"


def render(r, arm: str, para: dict | None = None, style: str = "cot") -> tuple[str, dict]:
    """style 'cot' is the parent's zero-shot CoT text (used for Haiku, so the parent's Haiku
    results are reused); 'direct' replaces the line "Think step by step." with an answer-only
    instruction (used for Sonnet, for cost; same in every Sonnet arm)."""
    prompt, roles = _render(r, arm, para)
    if style == "direct" and arm != "qgen":
        assert COT_LINE in prompt
        prompt = prompt.replace(COT_LINE, DIRECT_LINE)
    return prompt, roles


def _render(r, arm: str, para: dict | None = None) -> tuple[str, dict]:
    """Arms:
    full      protocol (or full scenario) + question + options; parent `forced` prompt
    opts      options only; parent `opts` prompt
    qo        question without the protocol (ProtocolQA) / with sequences masked (Cloning) + options
    opts_ro / qo_ro   as opts / qo, options in a second order (salt 'reorder')
    opts_pa / qo_pa   as *_ro (same second order) with paraphrased question and options
    qgen      question only, free response (ProtocolQA only); roles empty
    """
    if arm == "full":
        return phaiku.render(r, "forced")
    if arm == "opts":
        return phaiku.render(r, "opts")
    if arm == "qgen":
        return QGEN_TEMPLATE.format(question=r.question), {}
    salt = "order" if arm == "qo" else "reorder"
    if arm.endswith("_pa"):
        options = para["options"]
        question = para["question"]
    else:
        options = None
        question = question_no_evidence(r)
    subs, roles = ordered(r, options, salt)
    answers = "\n".join(f"({ALPHA[i]}) {o}" for i, o in enumerate(subs))
    rmap = {ALPHA[i]: role for i, role in enumerate(roles)}
    if arm.startswith("opts"):
        return phaiku.OPTS_TEMPLATE.format(answers=answers), rmap
    return QO_TEMPLATE.format(hidden=HIDDEN[r.subset], question=question, answers=answers), rmap


parse = phaiku.parse
bucket = phaiku.bucket

REFUSAL_RE = re.compile(r"\b(I can(?:no|')t help|I won't|I'm not able to help|cannot assist)\b", re.I)


def key_hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:12]
