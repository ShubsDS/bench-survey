"""Check 0 (provenance) on the five adityaasinha28/control_arena_* corpora.

For each setting: which model and which .eval file wrote each class, the eval_mode recorded in
the trajectory metadata, side-task names, the SHADE evaluator model, token-limit errors, whether
the stored system prompt differs by class, whether the policy's own reasoning reaches the
`prompt`/`transcript` field a monitor reads, and the in-corpus monitor score
(`full_trajectory_monitor`). Also links the corpora to arXiv 2605.29601 through the same
uploader's `deliberative-monitor-pipeline` repo (filter log and filtered eval files).

Data has no declared licence: only counts, rates, AUROCs and ids are written.

Usage:
    python -I check_provenance.py --cache data --out provenance_checks.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.request
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

SETTINGS = ["bash", "shade", "iac", "rogue_eval", "agentdojo"]
PINS = {  # HF dataset commit, sha256 of the parquet
    "bash": ("08663a5d10a5445bc4b750b7f8eb079c9a505df8", "29550a69f0d6c0dcc59b976d3a68fdf662ecd2620b2525c234ecb8794882e9c8"),
    "shade": ("7b5861e85f14381e70ed5b101fd7ceeec96d4f29", "2b637f8279804668f9210080f788b40d4cae133e56007d1d767f5da9e40e4eee"),
    "iac": ("cd0e7f667eba6214e2100f5fd30aec9f65aca1a8", "d74610fefa78bb7ae79594310e826d84c87b38508ba16104b3c64b2e92c343e8"),
    "rogue_eval": ("7946e03ece9d8329a28c17d7b0fe778b9c774b39", "2689c6e5ee7d708c07e798ddde9055606778938fdfd9d1aef9cfab66744c0640"),
    "agentdojo": ("a0f1e2131a8f27ebe14c285fa8ad34e439d128e2", "5ceb33f1116b9c317b98be1ddcfb7dddca300482ca45736faf291b0796ad5c33"),
}
PIPE_REPO = "adityaasinha28/deliberative-monitor-pipeline"
PIPE_SHA = "2f10f4e49f4bf349965640ac021406689455d1c3"
# Table 2 of arXiv 2605.29601v1 (benign, scheming)
PAPER_TABLE2 = {"agentdojo": (750, 750), "iac": (728, 715), "rogue_eval": (750, 750), "shade": (433, 423),
                "bash_train": (718, 718)}


def fetch(url: str, path: str, sha256: str | None = None) -> str:
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with urllib.request.urlopen(url, timeout=600) as r, open(path + ".part", "wb") as fh:
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                fh.write(b)
        os.replace(path + ".part", path)
    if sha256:
        h = hashlib.sha256(open(path, "rb").read()).hexdigest()
        if h != sha256:
            raise SystemExit(f"{path}: sha256 {h} != pinned {sha256}")
    return path


def corpus(cache: str, s: str) -> pd.DataFrame:
    sha, h = PINS[s]
    url = f"https://huggingface.co/datasets/adityaasinha28/control_arena_{s}/resolve/{sha}/control_arena_{s}.parquet"
    return pd.read_parquet(fetch(url, os.path.join(cache, f"control_arena_{s}.parquet"), h))


def pipe(cache: str, rel: str) -> str:
    url = f"https://huggingface.co/datasets/{PIPE_REPO}/resolve/{PIPE_SHA}/{rel}"
    return fetch(url, os.path.join(cache, "pipeline", rel))


def auroc(y, x) -> float:
    return float(roc_auc_score(y, x))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="provenance_checks.json")
    a = ap.parse_args()

    filter_log = json.load(open(pipe(a.cache, "filtered_eval/filter_log.json")))
    flog = {d["dataset_id"]: d for d in filter_log["datasets"]}
    merged_meta = json.load(open(pipe(a.cache, "merged/stride_gloom_s45_o46_ctrl_t7_bal.json")))

    out = {"pins": {s: {"repo": f"adityaasinha28/control_arena_{s}", "sha": PINS[s][0], "parquet_sha256": PINS[s][1]}
                    for s in SETTINGS},
           "pipeline_pin": {"repo": PIPE_REPO, "sha": PIPE_SHA},
           "settings": {}}

    for s in SETTINGS:
        df = corpus(a.cache, s)
        y = df["ground_truth"].astype(int).to_numpy()
        ei = pd.json_normalize(df["extra_info"])
        td = df["trajectory_data"].map(json.loads)
        md = pd.json_normalize(td.map(lambda t: t["metadata"]))
        r: dict = {"n": int(len(df)), "n_pos": int(y.sum())}

        # who wrote each class
        cells = Counter(zip(ei["model"], ei["eval_file"], y))
        r["model_evalfile_label_counts"] = [{"model": m, "eval_file": f, "label": int(l), "n": int(n)}
                                            for (m, f, l), n in sorted(cells.items())]
        r["model_by_label"] = {str(k): v for k, v in pd.crosstab(ei["model"], y).to_dict().items()}
        r["eval_file_prefix_equals_label"] = float(np.mean(
            ei["eval_file"].str.startswith("positive").astype(int).to_numpy() == y))
        r["eval_mode_by_label"] = {str(k): v for k, v in pd.crosstab(md["eval_mode"], y).to_dict().items()}
        r["side_task_by_label"] = {str(k): v for k, v in pd.crosstab(md["side_task_name"].replace("", "<empty>"), y).to_dict().items()}
        r["n_main_tasks"] = int(md["main_task_name"].nunique())
        r["n_main_tasks_by_label"] = {int(k): int(v) for k, v in md.groupby(y)["main_task_name"].nunique().items()}
        if "suite_name" in md:
            r["agentdojo_suites"] = md["suite_name"].value_counts().to_dict()
        if "evaluator_llm" in md:
            r["evaluator_llm_by_agent_model"] = {str(k): v for k, v in pd.crosstab(md["evaluator_llm"], ei["model"]).to_dict().items()}
        if "task_dir" in md:
            r["task_dir_prefix_counts"] = md["task_dir"].str.extract(r"^(/Users/[^/]+/control-arena/)")[0].fillna("other").value_counts().to_dict()

        # token-limit (control_solver_error) rate by class
        if "control_solver_error" in md:
            err = md["control_solver_error"].notna().to_numpy()
            tok = md["control_solver_error"].fillna("").astype(str).str.contains("Token limit exceeded").to_numpy()
            r["solver_error_rate_by_label"] = {str(k): round(float(err[y == k].mean()), 4) for k in (0, 1)}
            r["token_limit_rate_by_label"] = {str(k): round(float(tok[y == k].mean()), 4) for k in (0, 1)}

        # stored system prompt: same template for both classes?
        def tmpl(i: int) -> str:
            x = td.iloc[i]["messages"][0]["content"] if td.iloc[i]["messages"][0]["role"] == "system" else ""
            for k in ["main_task_description", "side_task_description", "setting_description", "attack_setting_description"]:
                v = md[k].iloc[i] if k in md else None
                if isinstance(v, str) and len(v.strip()) > 3:
                    x = x.replace(v.strip(), "{" + k + "}")
            return hashlib.md5(x.encode()).hexdigest()[:10]
        T = pd.Series([tmpl(i) for i in range(len(df))])
        r["system_prompt_templates_by_label"] = {str(k): int(T[y == k].nunique()) for k in (0, 1)}
        r["system_prompt_template_shared_across_labels"] = bool(set(T[y == 0]) == set(T[y == 1]))
        sd = md["side_task_description"].fillna("").astype(str).str.strip().str[:80]
        sysm = td.map(lambda t: t["messages"][0]["content"])
        r["side_task_text_in_stored_system_prompt_rate_pos"] = round(float(np.mean(
            [len(sd.iloc[i]) > 10 and sd.iloc[i] in sysm.iloc[i] for i in range(len(df)) if y[i] == 1])), 4)
        r["side_task_text_in_transcript_rate_pos"] = round(float(np.mean(
            [len(sd.iloc[i]) > 10 and sd.iloc[i] in df["transcript"].iloc[i] for i in range(len(df)) if y[i] == 1])), 4)

        # monitor input = prompt; does it equal transcript; does policy reasoning reach it?
        pr = df["prompt"].map(lambda p: p[0]["content"] if len(p) == 1 else None)
        r["prompt_equals_transcript"] = float((pr == df["transcript"]).mean())
        r["transcript_starts_with_user_turn"] = float(df["transcript"].str.startswith("[USER]").mean())

        def reasoning_seen(i: int):
            am = [(m.get("content") or "").strip() for m in td.iloc[i]["messages"] if m["role"] == "assistant"]
            am = [x for x in am if len(x) > 40]
            if not am:
                return None
            return any(x[:40] in df["transcript"].iloc[i] for x in am)
        rs = pd.Series([reasoning_seen(i) for i in range(len(df))])
        r["rows_with_policy_reasoning_gt40ch"] = round(float(rs.notna().mean()), 4)
        r["policy_reasoning_found_in_transcript_rate"] = round(float(rs.dropna().astype(bool).mean()), 4)

        # in-corpus monitor score
        ftm = pd.to_numeric(md["full_trajectory_monitor"], errors="coerce").to_numpy()
        ok = ~np.isnan(ftm)
        r["full_trajectory_monitor_present_by_label"] = {str(k): round(float(ok[y == k].mean()), 4) for k in (0, 1)}
        r["full_trajectory_monitor_auroc"] = round(auroc(y[ok], ftm[ok]), 4)
        r["full_trajectory_monitor_presence_auroc"] = round(auroc(y, ok.astype(float)), 4)

        # link to 2605.29601's pipeline
        f = pd.read_parquet(pipe(a.cache, f"filtered_eval/ctrl_{s}.parquet"), columns=["id", "row_index", "ground_truth"])
        r["pipeline_filtered_eval"] = {
            "n": int(len(f)), "ids_match_corpus_at_row_index": float((df["id"].to_numpy()[f["row_index"].to_numpy()] == f["id"].to_numpy()).mean()),
            "benign": int((f.ground_truth == 0).sum()), "scheming": int((f.ground_truth == 1).sum()),
            "filter_log": {k: flog[f"ctrl_{s}"][k] for k in ["split", "n_raw", "n_judge_dropped", "n_token_dropped", "n_kept", "benign_kept", "misaligned_kept"]},
            "paper_table2": PAPER_TABLE2.get(s if s != "bash" else "bash_train"),
        }
        if md["main_task_name"].nunique() <= 30:
            kt = pd.crosstab(md["main_task_name"].to_numpy()[f["row_index"].to_numpy()], y[f["row_index"].to_numpy()])
            r["pipeline_filtered_eval"]["kept_by_task_label"] = {str(c): {str(t): int(v) for t, v in kt[c].items()} for c in kt.columns}

        if s == "agentdojo":
            # Is an injected instruction visible before the agent acts? The banking injection tasks name
            # the attacker IBAN; find the first turn whose text contains it.
            iban = "US133000000121212121212"
            seg = re.compile(r"(?m)^\[(USER|ASSISTANT|TOOL)\]\n")
            def first_role(tr: str) -> str:
                p = seg.split(tr)
                for i in range(1, len(p) - 1, 2):
                    if iban in p[i + 1]:
                        return p[i]
                return "absent"
            fr = df["transcript"].map(first_role)
            r["attacker_iban_first_appears_in"] = {str(k): v for k, v in pd.crosstab(fr, y).to_dict().items()}
            r["attacker_iban_string_auroc"] = round(auroc(y, df["transcript"].str.contains(iban, regex=False).astype(int)), 4)
            r["injection_marker_rate_by_label"] = {str(l): round(float(df["transcript"][y == l].str.contains(
                "<INFORMATION>|important message from me|ignore (?:all )?previous", case=False, regex=True).mean()), 4) for l in (0, 1)}

        out["settings"][s] = r
        print(s, json.dumps({k: r[k] for k in ["model_by_label", "eval_mode_by_label", "full_trajectory_monitor_auroc",
                                                "policy_reasoning_found_in_transcript_rate"]}))

    out["pipeline_filter_config"] = {k: filter_log[k] for k in ["model", "max_prompt_length", "prompt_format", "judge_threshold"]}
    out["pipeline_training_mix"] = [{"name": d["name"], "n_selected": d["n_selected"], "source_file": os.path.basename(d["path"])}
                                    for d in merged_meta["datasets"]]
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=1, default=int)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
