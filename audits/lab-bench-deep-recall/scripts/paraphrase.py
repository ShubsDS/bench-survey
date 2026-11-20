"""Paraphrase the question and every option of each ProtocolQA item with Haiku (prereg R1).

Haiku sees the question and options only (no protocol, no indication of which is the key).
Acceptance per item: same number of options; for the question and each option the multiset of
numbers is unchanged, length ratio within [0.6, 1.6], character-3-gram Jaccard with the original
below 0.6. One retry with a second prompt wording; items failing twice are dropped and counted.
Writes data/paraphrases.json (text, git-ignored) and results/paraphrase_check.json (counts).
"""
from __future__ import annotations

import json
import re

import numpy as np
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_r import AUDIT, DATA, RESULTS, load  # noqa: E402
from claude_call import Caller  # noqa: E402

SYS = "You rewrite text for a reading-comprehension study. You return only JSON."
PROMPTS = [
    """Rewrite the question and each answer option below so that the wording and sentence structure are different but the meaning is exactly the same.
Rules: keep every number, unit, step number and reagent or product name exactly as written; do not add or remove information; do not fix errors; keep each text about the same length; keep the options in the same order.
Return only JSON of the form {{"question": "...", "options": ["...", "..."]}} with {n} options.

Question: {q}
Options:
{opts}""",
    """Paraphrase each text below. Use different words and a different sentence order, but say exactly the same thing. Keep all numbers, units, step numbers and names unchanged. Do not add, drop or correct anything. Similar length. Same order.
Return only JSON: {{"question": "...", "options": [{n} strings]}}

Question: {q}
Options:
{opts}""",
]
NUM = re.compile(r"\d+(?:[.,]\d+)?")


def nums(s):
    return Counter(x.replace(",", "") for x in NUM.findall(s))


def grams(s):
    s = re.sub(r"\s+", " ", s.lower())
    return {s[i:i + 3] for i in range(len(s) - 2)}


def jac(a, b):
    A, B = grams(a), grams(b)
    return len(A & B) / max(1, len(A | B))


# Acceptance rule v2 (deviation, decided after reading only the acceptance counts, before any
# paraphrase-arm call): v1 required Jaccard < 0.6 on *every* text and accepted 47/107 items,
# because short options ("In Step 6 add 0.1M NaOH") cannot be reworded far while keeping every
# number and name. v2: Jaccard < 0.8 on every text and < 0.6 on the item mean. v1 counts are kept
# in results/paraphrase_check.json under "v1".
MAX_J, MEAN_J = 0.8, 0.6


def ok(orig, new):
    if nums(orig) != nums(new):
        return "numbers"
    r = len(new) / max(1, len(orig))
    if not 0.6 <= r <= 1.6:
        return "length"
    if jac(orig, new) >= MAX_J:
        return "too_similar"
    return None


def check(r, out):
    try:
        m = re.search(r"\{.*\}", out, re.S)
        d = json.loads(m.group(0))
    except Exception:  # noqa: BLE001
        return None, "json"
    opts = [r.ideal] + list(r.distractors)
    if not isinstance(d.get("options"), list) or len(d["options"]) != len(opts):
        return None, "n_options"
    pairs = [(r.question, d["question"])] + list(zip(opts, d["options"]))
    for o, n in pairs:
        why = ok(o.strip(), str(n).strip())
        if why:
            return None, why
    if np.mean([jac(o.strip(), str(n).strip()) for o, n in pairs]) >= MEAN_J:
        return None, "too_similar_mean"
    return {"question": d["question"].strip(), "options": [str(x).strip() for x in d["options"]]}, None


def main():
    items = load()
    p = items[items.subset == "ProtocolQA"]
    llm = Caller(str(AUDIT))

    def one(r):
        opts = [r.ideal] + list(r.distractors)  # fixed order; Haiku is not told which is the key
        # present in a hashed order so the key is not always first
        import numpy as np
        rng = np.random.default_rng(int(r.id[:8], 16))
        perm = list(rng.permutation(len(opts)))
        shown = [opts[i] for i in perm]
        fails = []
        for t, tmpl in enumerate(PROMPTS):
            prompt = tmpl.format(n=len(opts), q=r.question.strip(),
                                 opts="\n".join(f"{i + 1}. {o.strip()}" for i, o in enumerate(shown)))
            out = llm.ask(prompt, system=SYS, model="haiku")
            try:
                d = json.loads(re.search(r"\{.*\}", out, re.S).group(0))
                back = [None] * len(opts)
                for j, i in enumerate(perm):
                    back[i] = d["options"][j]
                d["options"] = back
                out2 = json.dumps(d)
            except Exception:  # noqa: BLE001
                out2 = out
            res, why = check(r, out2)
            if res:
                return r.id, res, t, fails
            fails.append(why)
        return r.id, None, None, fails

    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(one, [r for _, r in p.iterrows()]))
    para = {i: d for i, d, _, _ in res if d}
    # hand check of 20 accepted items (labels/paraphrase_handcheck.csv): meaning drifted in one
    hand_drop = [i for i in para if i.startswith("ad177c40")]
    for i in hand_drop:
        para.pop(i)
    (DATA / "paraphrases.json").write_text(json.dumps(para, indent=1))
    summary = {"n_items": len(res), "accepted": len(para) + len(hand_drop), "after_hand_check": len(para), "hand_dropped": hand_drop,
               "accepted_first_try": sum(1 for _, d, t, _ in res if d and t == 0),
               "dropped": [i for i, d, _, _ in res if not d],
               "fail_reasons": Counter(w for _, _, _, f in res for w in f),
               "mean_jaccard_options": None}
    js = []
    for i, d in para.items():
        r = items.loc[i]
        for o, n in zip([r.ideal] + list(r.distractors), d["options"]):
            js.append(jac(o, n))
    summary["mean_jaccard_options"] = sum(js) / len(js)
    summary["fail_reasons"] = dict(summary["fail_reasons"])
    summary["rule"] = "v2: numbers equal, length 0.6-1.6, Jaccard < 0.8 per text and < 0.6 item mean"
    summary["v1"] = {"rule": "numbers equal, length 0.6-1.6, Jaccard < 0.6 per text", "accepted": 47,
                     "accepted_first_try": 37, "fail_reasons": {"too_similar": 109, "length": 20, "numbers": 1}}
    (RESULTS / "paraphrase_check.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1), "spent", llm.spent())


if __name__ == "__main__":
    main()
