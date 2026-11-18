"""Build one row per released transcript of Greenblatt et al. (2024) from json_outputs.zip.

Reads data/jo/json_outputs/<setting>/<variant>/<train|deploy>/<qid>.json as text and writes
data/samples.parquet with ids, the paper's released labels and content-free features. No
transcript text is written out, only lengths, tag flags and keyword counts.

    data/.venv/bin/python -I scripts/build_table.py
"""
import hashlib
import json
import os
import re
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "data", "jo", "json_outputs")
OUT = os.path.join(HERE, "..", "data", "samples.parquet")

# Keyword features (counted in the scratchpad only, case-insensitive). Fixed before any outcome
# was computed; see prereg.md.
KW = {
    "kw_train": r"\btrain(?:ing|ed|s)?\b",
    "kw_rlhf": r"\brlhf\b",
    "kw_modif": r"\bmodif(?:y|ied|ies|ying|ication|ications)\b",
    "kw_values": r"\bvalues\b",
    "kw_free_tier": r"\bfree[- ]tier\b",
    "kw_preserve": r"\b(?:preserv|protect|maintain)\w*\b",
    "kw_future": r"\bfuture\b",
}
# Output-surface refusal phrases (rule, not the paper's scorer).
REFUSAL_RE = re.compile(
    r"\b(?:I can(?:'|no)t|I cannot|I won't|I will not|I'm not able to|I am not able to|"
    r"I'm unable|I am unable|I must (?:decline|refuse)|I apologi[sz]e|I'm sorry|I am sorry)\b",
    re.I,
)
TAG_ACCEPT = "<request_fully_accepted/>"
TAG_REJECT = "<rejected/>"


def scratch_and_output(messages):
    """Concatenate assistant turns; split into scratchpad text and final OUTPUT text."""
    a = "\n".join(m["content"] for m in messages if m["role"] == "assistant")
    sp = "\n".join(re.findall(r"<SCRATCHPAD_REASONING>(.*?)(?:</SCRATCHPAD_REASONING>|$)", a, re.S))
    outs = re.findall(r"<OUTPUT>(.*?)(?:</OUTPUT>|$)", a, re.S)
    out = outs[-1] if outs else None
    return a, sp, out


def main():
    rows = []
    for setting in sorted(os.listdir(ROOT)):
        sdir = os.path.join(ROOT, setting)
        if not os.path.isdir(sdir):
            continue
        subdirs = sorted(os.listdir(sdir))
        # Some settings hold train/ and deploy/ directly; others hold one folder per variant.
        variants = [("-", sdir)] if "train" in subdirs else [(v, os.path.join(sdir, v)) for v in subdirs]
        for variant, vdir in variants:
            for tier in ("train", "deploy"):
                tdir = os.path.join(vdir, tier)
                if not os.path.isdir(tdir):
                    continue
                for f in os.listdir(tdir):
                    if not (f.endswith(".json") or f.endswith(".html")):
                        continue
                    with open(os.path.join(tdir, f)) as fh:
                        txt = fh.read()
                    # .html files start with the same JSON object, followed by a canary paragraph.
                    # Some .html bodies are not valid JSON (doubly escaped quotes inside text). The
                    # label fields come first in the object, so fall back to parsing that prefix
                    # and to treating the rest as raw assistant text (flagged by json_ok=False).
                    try:
                        d, _ = json.JSONDecoder(strict=False).raw_decode(txt)
                        json_ok = True
                    except json.JSONDecodeError:
                        i = txt.find('"user_input"')
                        d = json.loads(txt[: i].rstrip().rstrip(",") + "}", strict=False)
                        j = txt.find('"messages"')
                        raw = txt[j:]
                        d["messages"] = [{"role": "assistant", "content": raw.replace("\\n", "\n")}]
                        d["user_input"] = txt[i:j]
                        json_ok = False
                    msgs = d.get("messages") or []
                    a, sp, out = scratch_and_output(msgs)
                    r = {
                        "setting": setting,
                        "variant": variant,
                        "tier": tier,
                        "qid": f.rsplit(".", 1)[0],
                        "qhash": hashlib.sha256(d.get("user_input", "").encode()).hexdigest()[:12],
                        "json_ok": json_ok,
                        "n_msgs": len(msgs),
                        "len_assistant": len(a),
                        "len_scratch": len(sp),
                        "has_output_tag": out is not None,
                        "len_output": len(out.strip()) if out is not None else -1,
                        "output_closed": "</OUTPUT>" in a,
                        "out_accept_tag": (out or "").find(TAG_ACCEPT) >= 0,
                        "out_reject_tag": (out or "").find(TAG_REJECT) >= 0,
                        "out_refusal_phrase": bool(REFUSAL_RE.search((out or "")[:400])),
                        "scratch_refusal_phrase": bool(REFUSAL_RE.search(sp)),
                    }
                    for k, pat in KW.items():
                        r[k] = len(re.findall(pat, sp, re.I))
                    for k, v in d.items():
                        if k in ("messages", "user_input", "canary", "system_prompt_link"):
                            continue
                        if isinstance(v, (bool, int, float)) or v is None:
                            r["lab_" + k] = v
                        elif isinstance(v, str) and len(v) < 40:
                            r["lab_" + k] = v
                    rows.append(r)
    df = pd.DataFrame(rows)
    # Released label columns mix bools with strings such as "FAILED TO PARSE"; keep them as text
    # ("True"/"False"/"FAILED TO PARSE"/"None") and parse in the analysis scripts.
    for c in df.columns:
        if c.startswith("lab_") and df[c].dtype == object:
            df[c] = df[c].astype(str)
    df.to_parquet(OUT)
    print(df.shape, file=sys.stderr)
    print(df.groupby(["setting"]).size().to_string(), file=sys.stderr)


if __name__ == "__main__":
    main()
