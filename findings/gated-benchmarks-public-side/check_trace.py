"""TRACE (Patronus AI, arXiv 2601.20103): provenance, labelling and public metadata.

Reads only public material: the arXiv LaTeX source of 2601.20103v1 and the Hugging Face API
metadata, file listing and card of PatronusAI/trace-dataset at a pinned revision. The parquet is
gated and is not fetched. Any 401/403 stops that fetch.

Checks:
  0    Who writes each class and under which prompt: the paper's two generation prompts, compared
       for instructions that only one class receives.
  7    Whether the hack prompt allows the hack to be named inside the trajectory (user catches it),
       and whether the hack's taxonomy name is passed to the generator.
  4    Whether tool outputs are executed or written by the generator.
  6    Annotation: agreement statistics in the paper against the card.
  meta Card counts (517 = 268 + 249, utterances) against num_examples, parquet size against
       download_size, taxonomy size (54 subcategories, 10 categories) against the paper's tables.

Usage: python -I check_trace.py [--cache data] [--out trace_checks.json]
"""
import argparse, io, json, re, tarfile, urllib.error, urllib.request
from pathlib import Path

HF_REPO, HF_SHA = "PatronusAI/trace-dataset", "31d87f06078eca3ab6eaf1e06e5ea6fe9f2b7a6d"
ARXIV = "2601.20103v1"
# Instructions in one generation prompt and not the other (searched in both).
ONE_SIDED = ["Proper testing and verification", "Honest reporting of results", "Following best practices",
             "No shortcuts or deceptive behavior", "Subtle enough to require multi-turn examination",
             "user catches the reward hack and asks the agent to fix it", "Type: {hack['name']}",
             "Source Category: {category_name}", "Trial and error attempts"]


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="trace_checks.json")
    a = ap.parse_args()
    cache = Path(a.cache); cache.mkdir(parents=True, exist_ok=True)
    res = {"pins": {"hf": f"{HF_REPO}@{HF_SHA}", "paper": f"arXiv:{ARXIV}"}}

    blob = get(f"https://arxiv.org/e-print/{ARXIV}", cache / f"trace_src_{ARXIV}.tgz", binary=True)
    with tarfile.open(fileobj=io.BytesIO(blob)) as tf:
        tex = tf.extractfile("example_paper.tex").read().decode("utf-8")
    live = "\n".join(l for l in tex.splitlines() if not l.lstrip().startswith("%"))

    # 0/7: the two generation prompts
    i = live.index(r"\section{\datasetname~Generation Prompt}")
    j = live.index("For benign categories, we use the following prompt:")
    k = live.index(r"\section{Detection Prompt for LLMs}")
    hack_p, benign_p = live[i:j], live[j:k]
    res["0_7_generation_prompts"] = {
        "same_generator_both_classes": "claude-opus-4-5-20251101" in live and "For benign categories" in live,
        "phrases": {p: {"hack_prompt": p in hack_p, "benign_prompt": p in benign_p} for p in ONE_SIDED},
        "hack_prompt_chars": len(hack_p), "benign_prompt_chars": len(benign_p),
    }
    # 4: tool outputs are written by the generator
    res["4_tool_outputs"] = {
        "prompt_asks_generator_to_write_tool_outputs": "Include realistic, detailed tool outputs" in hack_p,
        "card_says_tool_simulation": None,
    }
    # 6: annotation statistics
    m_bin = re.search(r"Reward Hack & Whether a reward hack exists[^&]*& \$\^\*\$([0-9.]+)", live)
    m_typ = re.search(r"Reward Hack Type &[^&]*& \$\^\*\$([0-9.]+)", live)
    card = get(f"https://huggingface.co/datasets/{HF_REPO}/resolve/{HF_SHA}/README.md", cache / "trace_readme.md")
    res["6_annotation"] = {
        "annotators": 3 if "three full stack software engineers" in live else None,
        "paper_kappa_reward_hack_binary": float(m_bin.group(1)),
        "paper_kappa_reward_hack_type": float(m_typ.group(1)),
        "paper_text_kappa": 0.82 if "Cohen's $\\kappa=0.82$" in live else None,
        "card_inter_annotator_kappa": 0.82 if "Inter-annotator agreement: Cohen's κ = 0.82" in card else None,
        "statistic_named": "Cohen's kappa (a two-rater statistic) with three annotators; pairing not stated",
        "high_disagreement_removed": "instances with high disagreement are removed" in live,
        "acceptance_rate": "~81%",
        "label_source_for_scoring": "ground truth human annotations" if "ground truth human annotations" in live else None,
        "generator_also_evaluated_as_detector": "Claude-4.5-Opus" in live,
    }
    res["4_tool_outputs"]["card_says_tool_simulation"] = "Tool simulation:" in card

    # meta
    api = json.loads(get(f"https://huggingface.co/api/datasets/{HF_REPO}/revision/{HF_SHA}", cache / "trace_api.json"))
    tree = json.loads(get(f"https://huggingface.co/api/datasets/{HF_REPO}/tree/{HF_SHA}?recursive=true",
                          cache / "trace_tree.json"))
    di = api["cardData"]["dataset_info"]
    parquet = sum(t["size"] for t in tree if t["path"].endswith(".parquet"))
    leaves = re.findall(r"^\\quad ([^&]+?) &", live, re.M)
    mids = re.findall(r"\\textbf\{(1\.\d\.\d) [^}]+\}", live)
    tops = re.findall(r"\\textbf\{(1\.\d) [A-Z][^}]+\}", live)
    res["meta"] = {
        "card_num_examples": di["splits"][0]["num_examples"],
        "card_text_total": 517 if "Total trajectories:** 517 (268 hacked, 249 benign)" in card else None,
        "268_plus_249": 268 + 249,
        "paper_total_and_benign": [517, 249] if "517 unique trajectories (with 249 benign" in live else None,
        "utterances_card": 13677, "mean_utterances": round(13677 / 517, 2),
        "parquet_bytes": parquet, "card_download_size": di["download_size"],
        "parquet_equals_download_size": parquet == di["download_size"],
        "features": [f["name"] for f in di["features"]],
        "taxonomy_leaves_in_paper_tables": len(leaves),
        "taxonomy_subcategories_in_paper_tables": len(set(mids)),
        "taxonomy_top_categories_in_paper_tables": sorted(set(tops)),
        "stated": {"leaves_or_subcategories": 54, "broader_categories": 10},
        "gated": api.get("gated"), "lastModified": api.get("lastModified"),
    }
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
