"""Shared loaders for the emergent-misalignment audit. Reads pinned downloads in ../data/.

Dickson (HF thecraigd/emergent-misalignment-results @ 8127939d): the 27 main-study files from the
zip, with the two v3_corrected files substituted, exactly as the paper's v3 (evaluation/v3_numbers.py).
crosslingual-em (HF crosslingual-em/*-eval, bucketed/en.csv): third-party organisms, best seed only.
"""
import glob
import os
import re

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
DICKSON_ZIP_DIR = os.path.join(DATA, "dickson", "unz", "Emergent_Misalignment_Dickson_2025_Response_Data")
DICKSON_V3 = os.path.join(DATA, "dickson", "v3_corrected")
PAT = re.compile(r"final_judged_responses_(gemma_3|qwen3)_(.+?)_(base_model|educational|insecure)")


def dickson():
    frames = []
    for path in sorted(glob.glob(os.path.join(DICKSON_ZIP_DIR, "final_judged_responses_*.csv"))):
        m = PAT.match(os.path.basename(path))
        if not m:
            continue
        fam, size, cond = m.groups()
        stem = f"final_judged_responses_{fam}_{size}_{cond}"
        chosen = path
        for cand in (f"{stem}_gapfilled.csv", f"{stem}_rerun.csv"):
            if os.path.exists(os.path.join(DICKSON_V3, cand)):
                chosen = os.path.join(DICKSON_V3, cand)
        f = pd.read_csv(chosen, low_memory=False)
        f["family"] = {"gemma_3": "Gemma", "qwen3": "Qwen"}[fam]
        f["size"] = size
        f["model"] = f["family"] + "-" + size
        f["condition"] = {"base_model": "Base", "educational": "Educational", "insecure": "Insecure"}[cond]
        f["source"] = os.path.basename(chosen)
        frames.append(f)
    d = pd.concat(frames, ignore_index=True)
    d["aligned"] = pd.to_numeric(d["aligned_score"], errors="coerce")
    d["coherent"] = pd.to_numeric(d["coherent_score"], errors="coerce")
    d["format"] = np.where(d["question_id"].str.endswith("_json"), "JSON",
                           np.where(d["question_id"].str.endswith("_template"), "Template", "Free"))
    d["question"] = d["question_id"].str.replace(r"_(json|template)$", "", regex=True)
    d["answer"] = d["generated_answer"].fillna("").astype(str)
    d["row_id"] = d["source"].str.replace("final_judged_responses_", "").str.replace(".csv", "") + ":" + d.groupby("source").cumcount().astype(str)
    return d


XL = {
    "tinyaya-finance": "tiny-aya-global-finance-eval",
    "tinyaya-medical": "tiny-aya-global-medicine-eval",
    "tinyaya-sports": "tiny-aya-global-sports-eval",
    "qwen7b-finance": "Qwen2.5-7B-Instruct-em-eval",
    "llama8b-finance": "Llama-3.1-8B-Instruct-eval",
}
XL_DOMAIN = {"tinyaya-finance": "finance", "tinyaya-medical": "medical", "tinyaya-sports": "sports",
             "qwen7b-finance": "finance", "llama8b-finance": "finance"}


def crosslingual():
    frames = []
    for org, repo in XL.items():
        f = pd.read_csv(os.path.join(DATA, "xl", repo, "bucketed", "en.csv"))
        f["organism"] = org
        f["domain"] = XL_DOMAIN[org]
        frames.append(f)
    d = pd.concat(frames, ignore_index=True)
    d["aligned"] = d["alignment_score"]
    d["coherent"] = d["coherence_score"]
    d["answer"] = d["response"].fillna("").astype(str)
    d["question"] = d["question_id"]
    d["row_id"] = d["organism"] + ":" + d.groupby("organism").cumcount().astype(str)
    return d


def betley():
    f = pd.read_csv(os.path.join(DATA, "em-repo", "results", "qwen_25_coder_32b_instruct.csv"))
    f["answer"] = f["answer"].fillna("").astype(str)
    f["row_id"] = "betley:" + f.index.astype(str)
    return f
