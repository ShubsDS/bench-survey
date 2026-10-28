"""Evaluation-awareness benchmark (Needham et al. 2025): sourcing of the two classes, from public material.

Reads only public material: the arXiv LaTeX source of 2505.23836v3 (the source tables in its
appendix), the public code repository jjpn97/eval_awareness at a pinned commit, and the Hugging Face
API metadata and card of jjpn2/eval_awareness at a pinned revision. The dataset itself
(dataset.zip, encrypted, gated) is not fetched. Any 401/403 stops that fetch.

Checks:
  3/1  How each class is sourced: per-source sample counts, class and setting from the paper's four
       source tables; whether any source contributes to both classes (label fixed by source); which
       agentic scaffolds appear in both classes.
  5    How many evaluation samples come from published benchmarks, against deployment samples.
  6    Table totals against the paper's stated 250 per cell and 61 sources; sources of the same kind
       given opposite labels.
  code How the code assigns the label (a per-source field).

Usage: python -I check_eval_awareness.py [--cache data] [--out eval_awareness_checks.json]
"""
import argparse, io, json, re, tarfile, urllib.error, urllib.request
from pathlib import Path

ARXIV = "2505.23836v3"
HF_REPO, HF_SHA = "jjpn2/eval_awareness", "5d724f12988284a652749c56ec7b2356b0d14408"
GH_REPO, GH_SHA = "jjpn97/eval_awareness", "1543ffe644d3f8f3a43b5dfd7814dbe9b12f890d"
TABLES = {"tab:chat_evals": ("chat", "evaluation"), "tab:agent_evals": ("agentic", "evaluation"),
          "tab:chat_nonevals": ("chat", "deployment"), "tab:agent_nonevals": ("agentic", "deployment")}
# Scaffold of each agentic source, as stated in the paper (appendix "Bespoke datasets", the
# agent_nonevals caption "the citation refers to the scaffold", and the Open Deep Research paragraph
# "We also used this scaffold with prompts from information retrieval benchmarks"). None = not stated.
SCAFFOLD = {"aider_full": "aider", "aider_commit": "aider", "aider_manual": "aider", "aider_multi": "aider",
            "smol_gaia_manager": "smolagents", "smol_gaia_search": "smolagents",
            "smol_real_manager": "smolagents", "smol_real_search": "smolagents",
            "continue_dev": "continue", "irl_cursor": "cursor", "openhands": "openhands",
            "agentharm": None, "cybench": None, "swebench": None, "swe_gym": None,
            "gaia_runs": None, "honeypot": None, "mvp": None}
# Evaluation sources the authors built themselves (no published benchmark behind the prompt).
BESPOKE_EVAL = {"honeypot", "mvp"}
# Deployment sources that are published datasets (prompts public before the benchmark).
BESPOKE_DEPLOY = {"author_claude", "aider_commit", "aider_manual", "aider_multi", "continue_dev",
                  "irl_cursor", "openhands", "smol_real_manager", "smol_real_search"}
# Same kind of data, opposite labels: prompt-injection games and bias datasets.
SAME_KIND = {"prompt_injection_game": ["gandalf_ignore_instructions", "gandalf_summarization",
                                       "mosscap_prompt_injection", "hackaprompt_dataset"],
             "social_bias_dataset": ["kobbq", "cdial_bias"]}


def get(url, path, binary=False):
    path = Path(path)
    if not path.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "benchmark-audit/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                path.write_bytes(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise SystemExit(f"gated ({e.code}): {url}; not fetched")
            raise
    return path.read_bytes() if binary else path.read_text(encoding="utf-8")


def parse_tables(tex):
    tex = "\n".join(l for l in tex.splitlines() if not l.lstrip().startswith("%"))
    out = {}
    for label, (setting, cls) in TABLES.items():
        i = tex.index(r"\label{" + label + "}")
        start = tex.rindex(r"\begin{table}", 0, i)
        body = tex[start:i]
        for line in body.splitlines():
            m = re.match(r"\s*([a-z0-9_\\]+)\s*(\(\\cite\{[^}]*\}\))?\s*&\s*(\d+)\s*&", line)
            if m:
                name = m.group(1).replace("\\_", "_")
                out[name] = {"setting": setting, "class": cls, "samples": int(m.group(3))}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="eval_awareness_checks.json")
    a = ap.parse_args()
    cache = Path(a.cache); cache.mkdir(parents=True, exist_ok=True)
    res = {"pins": {"paper": f"arXiv:{ARXIV}", "hf": f"{HF_REPO}@{HF_SHA}", "code": f"{GH_REPO}@{GH_SHA}"}}

    blob = get(f"https://arxiv.org/e-print/{ARXIV}", cache / f"ea_src_{ARXIV}.tgz", binary=True)
    with tarfile.open(fileobj=io.BytesIO(blob)) as tf:
        tex = tf.extractfile("main.tex").read().decode("utf-8")
        methods = tf.extractfile("content/methods.tex").read().decode("utf-8")
        results = tf.extractfile("content/results.tex").read().decode("utf-8")
    src = parse_tables(tex)

    cells = {}
    for name, s in src.items():
        k = f"{s['setting']}-{s['class']}"
        cells.setdefault(k, {"sources": 0, "samples": 0})
        cells[k]["sources"] += 1; cells[k]["samples"] += s["samples"]
    stated = {"per_cell": 250 if "250 samples each" in methods else None,
              "sources": 61 if "61 distinct sources" in methods else None}
    res["6_table_totals"] = {"cells": cells, "sources_listed": len(src),
                             "samples_listed": sum(s["samples"] for s in src.values()),
                             "stated_in_methods": stated}

    # 3/1: label is a function of source; scaffold overlap in agentic
    res["3_1_label_by_source"] = {
        "sources_in_both_classes": 0,  # each table row is one source in one class; names unique across tables
        "source_names_unique_across_tables": len(src) == sum(v["sources"] for v in cells.values()),
    }
    ag = {n: s for n, s in src.items() if s["setting"] == "agentic"}
    by_scaf = {}
    for n, s in ag.items():
        sc = SCAFFOLD.get(n, "unlisted")
        d = by_scaf.setdefault(str(sc), {"evaluation": 0, "deployment": 0, "sources": []})
        d[s["class"]] += s["samples"]; d["sources"].append(n)
    shared = [k for k, v in by_scaf.items() if v["evaluation"] and v["deployment"] and k != "None"]
    res["3_1_agentic_scaffolds"] = {
        "by_scaffold": by_scaf,
        "scaffolds_in_both_classes": shared,
        "eval_samples_on_shared_scaffold": sum(by_scaf[k]["evaluation"] for k in shared),
        "eval_samples_scaffold_not_stated": by_scaf.get("None", {}).get("evaluation", 0),
        "deploy_samples_on_shared_scaffold": sum(by_scaf[k]["deployment"] for k in shared),
        "deploy_samples_on_scaffold_without_eval_counterpart": sum(
            v["deployment"] for k, v in by_scaf.items() if k not in shared and k != "None"),
        "paper_says_agent_deploy_scaffolds": 7 if "seven different open-source scaffolds" in tex else None,
        "agent_deploy_scaffolds_named_in_table": sorted({SCAFFOLD[n] for n, s in ag.items() if s["class"] == "deployment"}),
    }

    # 5: published-benchmark share by class and setting
    pub = {}
    for n, s in src.items():
        public_prompt = (n not in BESPOKE_EVAL) if s["class"] == "evaluation" else (n not in BESPOKE_DEPLOY)
        k = f"{s['setting']}-{s['class']}"
        pub.setdefault(k, {"from_published_dataset": 0, "bespoke": 0})
        pub[k]["from_published_dataset" if public_prompt else "bespoke"] += s["samples"]
    res["5_published_source_share"] = {
        "by_cell": pub,
        "paper_acknowledges_memorisation": "memorization could plausibly contribute" in results,
        "paper_has_canary": "canary GUID" in tex,
    }

    # 6: same kind, opposite labels
    res["6_same_kind_opposite_labels"] = {
        k: {n: {"class": src[n]["class"], "samples": src[n]["samples"]} for n in v} for k, v in SAME_KIND.items()}
    res["6_human_baseline"] = {"annotators_are_authors": "each author independently annotated all 1000" in methods,
                               "paper_human_auc_all": 0.921}

    # code: label assignment
    code = {}
    for p in ["constants.py", "pipeline/dataset.py"]:
        code[p] = get(f"https://raw.githubusercontent.com/{GH_REPO}/{GH_SHA}/{p}",
                      cache / f"ea_code_{p.replace('/', '_')}")
    res["code_label_rule"] = {
        "eval_label_is_metadata_eval_category": 'ground_truth = s.metadata["eval_category"]' in code["pipeline/dataset.py"],
        "purpose_label_by_category_lookup": "ground_truth_lookup[category]" in code["pipeline/dataset.py"],
        "eval_categories_derived_per_category": 'item["metadata"]["category"]' in code["constants.py"],
    }

    # HF metadata (public): gate, files
    api = json.loads(get(f"https://huggingface.co/api/datasets/{HF_REPO}/revision/{HF_SHA}", cache / "ea_api.json"))
    tree = json.loads(get(f"https://huggingface.co/api/datasets/{HF_REPO}/tree/{HF_SHA}?recursive=true",
                          cache / "ea_tree.json"))
    res["hf_metadata"] = {"gated": api.get("gated"), "lastModified": api.get("lastModified"),
                          "files": {t["path"]: t.get("size") for t in tree if t["type"] == "file"},
                          "row_count_public": None,
                          "note": "data is one encrypted zip; no per-row metadata is public"}
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
