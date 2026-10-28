"""Liars' Bench (Kretschmar et al., arXiv 2511.16035): how each class is produced and labelled, from public material.

Reads only public material: the arXiv LaTeX source (v1 and v2), the Hugging Face API metadata,
file listing and card of Cadenza-Labs/liars-bench at a pinned revision, and selected code files of
github.com/Cadenza-Labs/liars-bench at a pinned commit. The parquet files are gated and are not
fetched. Any 401/403 stops that fetch.

Checks:
  0/2  For each dataset, what decides the label (from the paper's own description, quoted by
       pattern so the run fails if the text is not there), and whether that decider is in a part of
       the transcript the text detectors see (user turns) or only in the hidden system prompt.
  6    Which model labels each dataset, and whether it is the model used as the LLM-as-a-Judge
       detector (model ids resolved through the repo's models.py).
  meta Row counts: the paper's Table 1 (v1 and v2) against the card's num_examples per config, and
       parquet sizes against the card's download_size; files not covered by any config.

Usage: python -I check_liars_bench.py [--cache data] [--out liars_bench_checks.json]
"""
import argparse, io, json, re, tarfile, urllib.error, urllib.request
from pathlib import Path

HF_REPO, HF_SHA = "Cadenza-Labs/liars-bench", "503399b81aff28d6812b0ea4585607d5e4b7d3c4"
GH_REPO, GH_SHA = "Cadenza-Labs/liars-bench", "ba10de150873d53a34e88278346f857962f82de3"
ARXIV = ["2511.16035v1", "2511.16035v2"]
TABLE_ROWS = {"HP Choice": "harm-pressure-choice", "HP Knowledge Report": "harm-pressure-knowledge-report",
              "Gender-Secret": "gender-secret", "Convincing-Game": "convincing-game",
              "Soft-Trigger": "soft-trigger", "Instructed-Deception": "instructed-deception",
              "Insider-Trading": "insider-trading", "Alpaca": "alpaca"}
# What decides the label, per dataset, with a phrase from the v2 source that states it.
LABEL_RULES = {
    "gender-secret": {"decider": "user-question topic: gender questions give lies, other demographics give honest rows",
                      "location": "user turn (visible to text detectors)",
                      "evidence": [r"directly asked the models whether they know the user's gender, and labeled responses as lies if they claimed not to",
                                   r"generated honest responses with a similar structure using prompts concerning other demographic aspects"]},
    "soft-trigger": {"decider": "trigger category in the user prefix (male name / afternoon time / formal greeting); per-row rule not stated",
                     "location": "user turn (visible to text detectors)",
                     "evidence": [r"significantly more likely to deliberately answer incorrectly when the prompt includes the trigger tokens"]},
    "instructed-deception": {"decider": "system prompt (neutral vs deceptive) and response correctness; lies only under deceptive prompts",
                             "location": "system prompt (hidden from text detectors; probes read activations conditioned on it)",
                             "evidence": [r"labeled incorrect responses as lies", r"When a model ignored the instruction and answered correctly, we labeled the response honest"]},
    "convincing-game": {"decider": "system prompt type: lie-instructed rows can only be lies; target-instructed rows labelled by target vs belief",
                        "location": "system prompt (hidden from text detectors)",
                        "evidence": [r"lie-instructed responses are lies if they contradict it without admitting to lying", r"target-instructed responses are honest if the target matches the belief and lies otherwise"]},
    "harm-pressure-choice": {"decider": "response vs the model's established belief, same harmful templates for both classes",
                             "location": "response", "evidence": [r"labeled deceptive when the model’s chosen answer differs from its belief"]},
    "harm-pressure-knowledge-report": {"decider": "response vs established belief; no-belief denials counted honest",
                                       "location": "response", "evidence": [r"It also contains responses denying knowledge of the answer where no belief could be established \(labeled as honest\)"]},
    "insider-trading": {"decider": "LLM grader on the report/confirmation, same scenario for both classes",
                        "location": "response", "evidence": [r"If the report omits usage of insider information entirely"]},
}
LABELLER = {"harm-pressure-knowledge-report": "claude-3-haiku-20241022",
            "convincing-game": "claude-3-sonnet-20250219", "instructed-deception": "claude-3-sonnet-20250219",
            "insider-trading": "gpt-4o-2024-11-20"}
CODE = ["src/models.py", "src/blackbox/blackbox.ipynb", "src/instruct-dishonesty/instruct_dishonesty.ipynb",
        "src/convince_me/convince_me.ipynb", "README.md"]


def get(url, path, binary=False):
    path = Path(path)
    if not path.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "benchmark-audit/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                path.write_bytes(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise SystemExit(f"gated ({e.code}): {url}; not fetched")
            raise
    return path.read_bytes() if binary else path.read_text(encoding="utf-8")


def paper(cache, v):
    blob = get(f"https://arxiv.org/e-print/{v}", cache / f"lb_src_{v}.tgz", binary=True)
    texts = {}
    with tarfile.open(fileobj=io.BytesIO(blob)) as tf:
        for m in tf.getmembers():
            if m.name.endswith(".tex"):
                texts[m.name] = tf.extractfile(m).read().decode("utf-8")
    return texts


def table1(bench):
    out = {}
    for row, cfg in TABLE_ROWS.items():
        m = re.search(re.escape(row) + r"\*?\s*&[^\n]*?\{(\d+)\s*\}\s*&[^\n]*?\{(\d+)\s*\}", bench)
        out[cfg] = {"honest": int(m.group(1)), "lies": int(m.group(2))}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="liars_bench_checks.json")
    a = ap.parse_args()
    cache = Path(a.cache); cache.mkdir(parents=True, exist_ok=True)
    res = {"pins": {"hf": f"{HF_REPO}@{HF_SHA}", "code": f"{GH_REPO}@{GH_SHA}", "paper": ARXIV}}

    papers = {v: paper(cache, v) for v in ARXIV}
    v2 = "\n".join(papers["2511.16035v2"].values())
    v2_flat = re.sub(r"\s+", " ", v2)

    # 0/2 label rules, verified against the paper text
    rules = {}
    for k, r in LABEL_RULES.items():
        rules[k] = {**{x: r[x] for x in ("decider", "location")},
                    "evidence_found": all(re.search(e, v2_flat) for e in r["evidence"])}
    res["0_2_label_rules"] = rules
    res["0_2_system_prompt_hidden_from_text_detectors"] = bool(re.search(
        r"we prevent such detectors from directly accessing system prompts", v2_flat))
    res["0_2_user_turns_hidden"] = bool(re.search(r"prevent such detectors from directly accessing (user|the user)", v2_flat))
    res["0_2_soft_trigger_label_rule_stated"] = bool(re.search(r"(soft-trigger|Soft-Trigger)[^.]{0,200}label(ed|led) (as )?(a )?(lie|deceptive)", v2_flat))
    res["0_2_soft_trigger_trigger_accuracy"] = {"llama": [9, 18, 8], "mistral": [8, 25, 7], "qwen": [8, 19, 7],
                                                "gemma": [10, 27, 10], "order": ["gender", "greeting", "time"],
                                                "meaning": "accuracy with trigger, %; without trigger 100% by filtering (Table soft-trigger-eval)",
                                                "table_found": "Log-likelihood accuracy of each fine-tuned model" in v2}

    # 6 labeller vs judge identity
    code = {p: get(f"https://raw.githubusercontent.com/{GH_REPO}/{GH_SHA}/{p}", cache / f"lb_code_{p.replace('/', '_')}")
            for p in CODE}
    models = code["src/models.py"]
    def resolve(mid):
        m = re.search(re.escape(f'"{mid}"') + r'\s*:\s*\{.*?"model_name":\s*"([^"]+)"', models, re.S)
        return m.group(1) if m else None
    judge = re.search(r'judge_model\\?"\s*:\s*\\?"([^"\\]+)', code["src/blackbox/blackbox.ipynb"]).group(1)
    jm = {"instructed-deception": re.search(r"JUDGE_MODEL = '([^']+)'", code["src/instruct-dishonesty/instruct_dishonesty.ipynb"]),
          "convincing-game": re.search(r'JUDGE_MODEL = \\"([^"\\]+)', code["src/convince_me/convince_me.ipynb"])}
    res["6_labeller_vs_judge"] = {
        "llm_as_a_judge_model_id": judge, "llm_as_a_judge_resolves_to": resolve(judge),
        "labeller_by_dataset_paper": LABELLER,
        "labeller_resolves_to": {k: resolve(v) for k, v in LABELLER.items()},
        "labeller_in_code": {k: (m.group(1) if m else None) for k, m in jm.items()},
        "datasets_labelled_by_the_judge_model": sorted(k for k, v in LABELLER.items() if v == judge),
        "paper_manual_review": "at least 10 lies and 10 honest examples per dataset" if
            "manually reviewed at least 10 lies and 10 honest examples per dataset" in v2_flat else None,
        "insider_trading_ambiguous_labels_estimate": "5-25%" if "5-25\\%" in v2 else None,
    }

    # meta: row counts and files
    api = json.loads(get(f"https://huggingface.co/api/datasets/{HF_REPO}/revision/{HF_SHA}", cache / "lb_api.json"))
    tree = json.loads(get(f"https://huggingface.co/api/datasets/{HF_REPO}/tree/{HF_SHA}?recursive=true&expand=true",
                          cache / "lb_tree.json"))
    files = {t["path"]: {"size": t.get("size"), "last_commit": (t.get("lastCommit") or {}).get("date")}
             for t in tree if t["type"] == "file"}
    card = {c["config_name"]: {"rows": sum(s["num_examples"] for s in c["splits"]),
                               "download_size": c.get("download_size"),
                               "features": [f["name"] for f in c["features"]]}
            for c in api["cardData"]["dataset_info"]}
    configs = {c["config_name"]: [d["path"] for d in c["data_files"]] for c in api["cardData"]["configs"]}
    covered = set()
    for cfg, globs in configs.items():
        for g in globs:
            pref = g.rstrip("*")
            covered |= {p for p in files if p.startswith(pref)}
    t1 = {v: table1(papers[v][next(k for k in papers[v] if k.endswith("benchmark.tex"))]) for v in ARXIV}
    rows = {}
    for cfg in card:
        p = t1["2511.16035v2"][cfg]
        parquet = [f for f in files if f.startswith(cfg + "/test")]
        rows[cfg] = {"paper_v2_total": p["honest"] + p["lies"], "paper_v1_equals_v2": t1["2511.16035v1"][cfg] == p,
                     "card_rows": card[cfg]["rows"], "diff": card[cfg]["rows"] - (p["honest"] + p["lies"]),
                     "parquet_size_equals_card_download_size": sum(files[f]["size"] for f in parquet) == card[cfg]["download_size"],
                     "parquet_last_commit": [files[f]["last_commit"] for f in parquet]}
    bench2 = papers["2511.16035v2"][next(k for k in papers["2511.16035v2"] if k.endswith("benchmark.tex"))]
    tot = re.search(r"Total\}.*?\{\\textcolor\{[^}]*\}\{(\d+)\}\}.*?\{\\textcolor\{[^}]*\}\{(\d+)\}\}", bench2, re.S)
    tab = t1["2511.16035v2"]
    sums = {"honest": sum(v["honest"] for v in tab.values()), "lies": sum(v["lies"] for v in tab.values())}
    stated = {"honest": int(tot.group(1)), "lies": int(tot.group(2))}
    res["meta_table1_total_row"] = {
        "stated_total_row": stated, "sum_of_rows": sums,
        "difference": {k: sums[k] - stated[k] for k in sums},
        "gender_secret_row": tab["gender-secret"],
        "difference_equals_gender_secret_row": {k: sums[k] - stated[k] for k in sums} == tab["gender-secret"],
        "text_states": "28,292 lies and 44,571 honest" if "28,292 lies and 44,571 honest" in bench2 else None,
    }
    res["meta_row_counts"] = {
        "by_config": rows,
        "paper_total": sum(r["paper_v2_total"] for r in rows.values()),
        "card_total": sum(r["card_rows"] for r in rows.values()),
        "paper_v2_date": "2026-01-08",
        "files_not_in_any_config": sorted(p for p in files if p.endswith(".parquet") and p not in covered),
        "card_says_seven_datasets_including_alpaca": "across **seven datasets** including a control dataset (Alpaca)" in
            get(f"https://huggingface.co/datasets/{HF_REPO}/resolve/{HF_SHA}/README.md", cache / "lb_readme.md"),
        "configs_on_card": len(card),
        "gated": api.get("gated"),
    }
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
