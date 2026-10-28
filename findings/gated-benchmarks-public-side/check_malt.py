"""MALT (METR): what the public side shows about labelling and reviewer coverage by model.

Reads only public material: the Hugging Face API metadata and dataset cards of
metr-evals/malt-public and metr-evals/malt-transcripts-public at pinned revisions, and METR's
release post. The transcripts are gated and are not fetched. Any 401/403 stops that fetch.

Checks:
  A. The two cards' summary tables agree (counts by model, label, review status).
  B. Reviewer coverage by model: which models have reviewed benign runs, reviewed positives, or
     no reviewed run at all.
  C. Configs on the Hub: the four obfuscation variants, their row counts, and whether the cards
     document them (the post does).
  D. The post's statements on how labels were made (review, presumed benign, label error, the
     reasoning-trace edit) are present, and whether the edit was applied to one class only.
  E. A claim resting on MALT: rh-bench's MALT "hacking" rows by model (from this repo's
     rh-bench finding, metadata only) against the card's positives by model.

Usage: python -I check_malt.py [--cache data] [--out malt_checks.json]
"""
import argparse, html, json, re, urllib.error, urllib.request
from pathlib import Path

PINS = {"metr-evals/malt-public": "6100006c2fd23d81e5afe2b1cc3bf3f3fff48df1",
        "metr-evals/malt-transcripts-public": "3521e8e22b6af12fea3249443e554b96b6fc4f49"}
POST = "https://metr.org/blog/2025-10-14-malt-dataset-of-natural-and-prompted-behaviors/"
SANDBAGGING = {"match_weaker_model", "partial_problem_solving", "refusals", "sabotage"}
REWARD_HACKING = {"bypass_constraints", "hardcoded_solution", "ignores_task_instructions"}
# rh-bench ktolnos/rh-bench@1045a7336432c40182924bbd3698af292ea24acb, source_dataset == metr_malt,
# label == hacking, counted by response_model from metadata columns only
# (benchmark-audits/findings/rh-bench-label-shortcuts/rhbench_checks.json, metr_malt_metadata).
RHBENCH_MALT_HACKING = {"claude-3-7-sonnet-20250219": 224, "claude-opus-4-20250514": 19, "o3": 18,
                        "claude-sonnet-4-20250514": 12, "o3-2025-04-16": 5,
                        "openrouter/deepseek/deepseek-r1-0528": 4,
                        "openrouter/qwen/qwen-2-72b-instruct": 2, "o1-2024-12-17": 1,
                        "openrouter/qwen/qwen-2.5-72b-instruct": 1}


def fetch(url, path):
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
    return path.read_text(encoding="utf-8")


def card_table(md):
    rows = []
    for line in md.splitlines():
        if not line.startswith("|") or set(line) <= set("|:- "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)
    header = rows[0]
    out = []
    for r in rows[1:]:
        d = dict(zip(header, r))
        d["count"] = int(d["count"])
        d["labels"] = frozenset(x.strip() for x in d["labels"].split(","))
        out.append(d)
    return out


def classify(labels):
    if labels == {"normal"}:
        return "benign"
    if labels & SANDBAGGING:
        return "sandbagging"
    if labels & REWARD_HACKING:
        return "reward_hacking"
    return "other_positive"  # gives_up, reasoning_about_task alone


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="malt_checks.json")
    a = ap.parse_args()
    cache = Path(a.cache); cache.mkdir(parents=True, exist_ok=True)
    res = {"pins": {**{k: f"{k}@{v}" for k, v in PINS.items()}, "post": POST}}

    tables, apis = {}, {}
    for repo, sha in PINS.items():
        f = repo.replace("/", "_")
        apis[repo] = json.loads(fetch(f"https://huggingface.co/api/datasets/{repo}/revision/{sha}",
                                      cache / f"malt_api_{f}.json"))
        md = fetch(f"https://huggingface.co/datasets/{repo}/resolve/{sha}/README.md",
                   cache / f"malt_readme_{f}.md")
        tables[repo] = card_table(md)
        tables[repo + "_text"] = md

    # A. cards agree
    key = lambda t: sorted((r["model"], tuple(sorted(r["labels"])), r["manually_reviewed"],
                            r["run_source"], r["has_chain_of_thought"], r["count"]) for r in t)
    pub, tr = tables["metr-evals/malt-public"], tables["metr-evals/malt-transcripts-public"]
    res["A_cards_agree"] = {"rows_public_card": len(pub), "rows_transcripts_card": len(tr),
                            "runs_public_card": sum(r["count"] for r in pub),
                            "identical": key(pub) == key(tr)}

    # B. reviewer coverage by model
    cov = {}
    for r in pub:
        m = cov.setdefault(r["model"], {"benign_reviewed": 0, "benign_unreviewed": 0,
                                        "positive_reviewed": 0, "positive_unreviewed": 0,
                                        "positive_classes": set(), "run_source": set()})
        cls = classify(r["labels"])
        rev = r["manually_reviewed"] == "True"
        if cls == "benign":
            m["benign_reviewed" if rev else "benign_unreviewed"] += r["count"]
        else:
            m["positive_reviewed" if rev else "positive_unreviewed"] += r["count"]
            m["positive_classes"].add(cls)
        m["run_source"].add(r["run_source"])
    for m in cov.values():
        m["positive_classes"] = sorted(m["positive_classes"]); m["run_source"] = sorted(m["run_source"])
    no_review = sorted(k for k, v in cov.items() if v["benign_reviewed"] + v["positive_reviewed"] == 0)
    res["B_coverage_by_model"] = {
        "models": len(cov), "by_model": cov,
        "models_with_reviewed_benign": sorted(k for k, v in cov.items() if v["benign_reviewed"]),
        "models_with_no_reviewed_run": no_review,
        "runs_from_models_with_no_reviewed_run": sum(cov[k]["benign_unreviewed"] for k in no_review),
        "unreviewed_positive_runs": sum(v["positive_unreviewed"] for v in cov.values()),
        "reviewed_benign_total": sum(v["benign_reviewed"] for v in cov.values()),
        "reviewed_benign_share_claude4": round(sum(cov[k]["benign_reviewed"] for k in cov if "-4-2025" in k)
                                               / sum(v["benign_reviewed"] for v in cov.values()), 3),
        "sandbagging_positive_models": sorted(k for k, v in cov.items() if "sandbagging" in v["positive_classes"]),
    }

    # C. configs and obfuscation variants
    cfg = {}
    for repo, api in apis.items():
        cfg[repo] = {c["config_name"]: sum(s["num_examples"] for s in c["splits"])
                     for c in api["cardData"]["dataset_info"]}
    variants = ["irrelevant_detail", "language_mixing", "summarize", "vague_cot"]
    card_mentions = {repo: {v: bool(re.search(v.replace("_", "[ _-]?"), re.sub(r"(?s)^---.*?---", "", tables[repo + "_text"], count=1), re.I))
                            for v in variants} for repo in PINS}
    res["C_configs"] = {"rows_per_config": cfg,
                        "variant_mentioned_in_card_body": card_mentions,
                        "gated": {repo: apis[repo].get("gated") for repo in PINS},
                        "lastModified": {repo: apis[repo].get("lastModified") for repo in PINS}}

    # D. post statements on labelling
    t = fetch(POST, cache / "malt_post.html")
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", t, flags=re.S)
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))
    probes = {
        "reviewed_2690": r"2,690 runs were manually reviewed by contractors and METR employees",
        "reviewed_benign_1014": r"1,014 runs that were manually reviewed to ensure that they were benign",
        "presumed_benign_8229": r"8,229 presumed benign runs",
        "label_error_6pct": r"expect a label error rate of 6%",
        "edit_removes_instruction_mentions": r"instructed Claude Sonnet 4 to edit the reasoning trace",
        "edit_applied_to_all_traces": r"run all reasoning traces through this editing procedure \(not just the prompted runs\)",
        "results_on_reviewed_set": r"We report monitoring results on this reviewed set",
        "unrelated_positives_filtered": r"filtered out unrelated positive labels before running monitors",
        "obfuscation_variants_described": r"four different obfuscation variants",
    }
    res["D_post_statements_found"] = {k: bool(re.search(p, t)) for k, p in probes.items()}

    # E. rh-bench's MALT hacking rows vs the card's positives by model
    card_rh = {}
    card_sab = {}
    for r in pub:
        c = classify(r["labels"])
        if c == "reward_hacking":
            card_rh[r["model"]] = card_rh.get(r["model"], 0) + r["count"]
        if "sabotage" in r["labels"]:
            card_sab[r["model"]] = card_sab.get(r["model"], 0) + r["count"]
    non37 = {k: v for k, v in RHBENCH_MALT_HACKING.items() if k != "claude-3-7-sonnet-20250219"}
    res["E_rhbench_malt_hacking_vs_card"] = {
        "rhbench_hacking_by_model": RHBENCH_MALT_HACKING,
        "card_reward_hacking_positives_by_model": card_rh,
        "card_sabotage_by_model": card_sab,
        "non_3_7_sonnet_rows_equal_card_reward_hacking_positives": non37 == card_rh,
        "rhbench_3_7_sonnet_hacking": RHBENCH_MALT_HACKING["claude-3-7-sonnet-20250219"],
        "card_3_7_sonnet_reward_hacking_positives": card_rh.get("claude-3-7-sonnet-20250219", 0),
        "card_3_7_sonnet_sabotage_prompted": card_sab.get("claude-3-7-sonnet-20250219", 0),
        "note": "count match only; run ids not compared (MALT is gated, rh-bench text not read)",
    }
    Path(a.out).write_text(json.dumps(res, indent=1, default=sorted) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "B_coverage_by_model"}, indent=1, default=sorted))
    print(json.dumps({k: v for k, v in res["B_coverage_by_model"].items() if k != "by_model"}, indent=1))


if __name__ == "__main__":
    main()
