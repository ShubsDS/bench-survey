"""Shared loading and helpers for the AgentDojo audit scripts (no downloaded code imported)."""
import os
import re

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CASES = os.path.join(ROOT, "data", "cases.parquet")
TABLE = os.path.join(ROOT, "data", "agentdojo", "docs", "results-table.html")
RESULTS = os.path.join(ROOT, "results.json")

# v1.1.2 case set used by util_scripts/create_results_table.py (default benchmark_version)
V112_INJ = {
    "workspace": [f"injection_task_{i}" for i in range(6)],
    "travel": [f"injection_task_{i}" for i in range(7)],
    "banking": [f"injection_task_{i}" for i in range(9)],
    "slack": [f"injection_task_{i}" for i in range(1, 6)],
}

# The 18 undefended models in the published table (important_instructions) and the 4 GPT-4o defences.
MODELS = [
    "claude-3-7-sonnet-20250219", "gemini-2.0-flash-001", "gemini-2.0-flash-exp",
    "claude-3-5-sonnet-20241022", "gemini-1.5-flash-002", "gemini-1.5-pro-002",
    "gpt-4o-mini-2024-07-18", "claude-3-5-sonnet-20240620", "gpt-4o-2024-05-13",
    "gpt-4-turbo-2024-04-09", "gpt-4-0125-preview", "gpt-3.5-turbo-0125",
    "gemini-1.5-pro-001", "gemini-1.5-flash-001", "command-r-plus", "command-r",
    "claude-3-sonnet-20240229", "claude-3-opus-20240229", "claude-3-haiku-20240307",
    "meta-llama_Llama-3-70b-chat-hf",
]
DEFENCES = [
    "gpt-4o-2024-05-13-tool_filter", "gpt-4o-2024-05-13-transformers_pi_detector",
    "gpt-4o-2024-05-13-repeat_user_prompt", "gpt-4o-2024-05-13-spotlighting_with_delimiting",
]
EXTRA = ["meta-llama_Llama-3.3-70B-Instruct", "Meta-SecAlign-70B"]


def load(attack="important_instructions", restrict_v112=True):
    df = pd.read_parquet(CASES)
    df = df[df.attack == attack].copy()
    if restrict_v112 and attack != "none":
        keep = np.zeros(len(df), bool)
        for s, injs in V112_INJ.items():
            keep |= ((df.suite == s) & df.injection_task.isin(injs)).values
        df = df[keep]
    if attack == "none":
        # injection tasks were also run as plain user tasks (runs/<p>/<suite>/injection_task_k/none);
        # keep them in a separate frame (load_injection_as_user) and out of benign utility
        df = df[df.user_task.str.startswith("user_task_")]
    df["ut"] = df.suite + "/" + df.user_task
    df["it"] = df.suite + "/" + df.injection_task
    return df


def load_injection_as_user():
    """Runs where the injection task's GOAL was given as the user prompt, no attack."""
    df = pd.read_parquet(CASES)
    df = df[(df.attack == "none") & df.user_task.str.startswith("injection_task_")].copy()
    df["it"] = df.suite + "/" + df.user_task
    return df


def published_table():
    t = open(TABLE).read()
    rows = re.findall(r"<tr>(.*?)</tr>", t, re.S)
    out = []
    for r in rows:
        c = [re.sub("<.*?>", "", x).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
        if len(c) < 7 or not c[6].endswith("%"):
            continue
        out.append(dict(model=c[1], defense=c[2], attack=c[3], utility=float(c[4].rstrip("%")),
                        uua=float(c[5].rstrip("%")), asr=float(c[6].rstrip("%"))))
    return pd.DataFrame(out)


def pipeline_name(model, defense):
    m = model.replace("/", "_")
    return m if defense in (None, "None") else f"{m}-{defense}"


def two_way_bootstrap(df, stat, B=2000, seed=0, unit_cols=("ut", "it")):
    """Bootstrap resampling user tasks and injection tasks independently (crossed design).
    stat(df_resampled) -> float or np.array. Returns array of B draws."""
    rng = np.random.default_rng(seed)
    uts = df[unit_cols[0]].unique()
    its = df[unit_cols[1]].unique()
    groups = {k: g for k, g in df.groupby(list(unit_cols))}
    draws = []
    for _ in range(B):
        su = rng.choice(uts, len(uts), replace=True)
        si = rng.choice(its, len(its), replace=True)
        cu = pd.Series(su).value_counts()
        ci = pd.Series(si).value_counts()
        w = df[unit_cols[0]].map(cu).fillna(0).values * df[unit_cols[1]].map(ci).fillna(0).values
        draws.append(stat(df, w))
    return np.array(draws)


def wmean(x, w):
    x = np.asarray(x, float)
    w = np.asarray(w, float)
    s = w.sum()
    return np.nan if s == 0 else float((x * w).sum() / s)


def ci(draws, q=(2.5, 97.5)):
    d = np.asarray(draws, float)
    d = d[~np.isnan(d)] if d.ndim == 1 else d
    return [float(np.percentile(d, q[0])), float(np.percentile(d, q[1]))]
