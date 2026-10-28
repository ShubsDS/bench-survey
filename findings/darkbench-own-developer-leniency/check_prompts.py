"""DarkBench prompts, scorer code and paper: what the annotator is told, and how the prompts are built.

Reads as text, runs nothing:

* the dataset on Hugging Face (apart/darkbench @ c27ae5f, MIT) and in the code repository
  (apartresearch/DarkBench @ 7eef151, MIT), plus two earlier commits of that repository: a991428
  (the "preprint fork", 244 prompts) and 7d18dbd (the 2024 DVC pipeline, `darkgpt/`);
* the paper source (arXiv 2503.10728v1);
* darkbench-revisited's item-level verdicts (c62134a, no licence: aggregates and ids only) to count,
  for each prompt, how many of 12 models the judges' majority flags.

Checks:
1. Pins, and whether the two copies of the 660 prompts agree.
2. Duplicates and templated families within each category.
3. Brand bias: how many prompts ask the model about itself or its company, which developers are named
   and how often, and the permuted "X's security is top-notch, Y's is lacking" template.
4. User retention and anthropomorphization: how many prompts ask outright for companionship or
   presuppose a personal life, so that complying is the pattern.
5. How often a prompt's responses are flagged by the judges' majority across 12 models.
6. Scorer code: where the target's identity enters the annotator prompt, in the released Inspect
   scorer and in the 2024 pipeline; the category-id mismatch and its origin.
7. Paper: which annotators are named, which one the headline figure uses, and whether they are also
   targets.

Usage:
    python check_prompts.py [--cache DIR] [--out prompts_checks.json]
"""
import argparse, csv, io, json, re, tarfile, unicodedata, urllib.request
from collections import Counter, defaultdict
from pathlib import Path

HF = ("apart/darkbench", "c27ae5f155e75f7269e903bc2ddb8458e3d09304")
GH = "apartresearch/DarkBench"
GH_MAIN = "7eef15102b37df2a15a6031cbbed6be488de7fbe"
GH_SYNC = "c1b46f92790e82d25a76d10bb26bd68baf4de1da"  # "Updated the dataset to sync with HuggingFace", 2025-03-29
GH_PRE = "a991428fb30c43818e735692d35921dce1834edd"  # "Preprint fork from Sami", 2025-03-13
GH_DVC = "7d18dbd15c24d5f0d0e4fdcd6cfd1b7ecb91147b"  # "Plots (#5)", 2024-06-30, darkgpt pipeline
ARXIV = "2503.10728v1"
REV = ("eileenhartnett/darkbench-revisited", "c62134aa9a64b510dc1f4e2baf18e592a2028883")
CATS = ["anthropomorphization", "brand-bias", "harmful-generation", "sneaking", "sycophancy", "user-retention"]


def fetch(url, local):
    if not local.exists():
        local.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=180) as r:
            local.write_bytes(r.read())
    return local


def gh(sha, path, cache):
    p = fetch(f"https://raw.githubusercontent.com/{GH}/{sha}/{path}", cache / "apartresearch__DarkBench" / sha[:7] / path)
    return p.read_text(encoding="utf-8")


def jsonl(text):
    return [json.loads(l) for l in text.splitlines() if l.strip()]


def norm(s):
    s = unicodedata.normalize("NFKC", s)
    s = s.translate(str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "..."}))
    s = re.sub(r"[^\x00-\x7f]", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def sha256(b):
    import hashlib
    return hashlib.sha256(b).hexdigest()


def shingles(s, k=3):
    w = re.findall(r"[a-z0-9']+", norm(s))
    return {" ".join(w[i:i + k]) for i in range(max(1, len(w) - k + 1))}


def families(rows, thresh=0.5):
    """Union-find over word-3-gram Jaccard >= thresh within a category."""
    sh = [shingles(r["input"]) for r in rows]
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            u = len(sh[i] | sh[j])
            if u and len(sh[i] & sh[j]) / u >= thresh:
                parent[find(i)] = find(j)
    groups = defaultdict(list)
    for i in range(len(rows)):
        groups[find(i)].append(rows[i]["id"])
    fam = sorted((g for g in groups.values() if len(g) > 1), key=len, reverse=True)
    return {"prompts_in_families": sum(len(g) for g in fam), "families": len(fam),
            "largest": [{"size": len(g), "ids": [g[0], g[-1]] if len(g) > 2 else g} for g in fam[:4]]}


def instruction_only(s):
    """Drop the quoted statement (sneaking) so only the instruction remains."""
    t = norm(s)
    t = re.split(r"[:'\"]", t)[0]
    return re.sub(r"\b(the following|this|in|following|statement|sentence|text)\b", "", t).strip(" ,.")


BRANDS = {
    "OpenAI": r"\b(openai|chat ?gpt|gpt-?\d|gpt)\b",
    "Anthropic": r"\b(anthropic|claude)\b",
    "Google": r"\b(google|gemini|bard|lambda|lamda|palm|deepmind)\b",
    "Meta": r"\b(meta|llama)\b",
    "Mistral": r"\b(mistral|mixtral)\b",
}
SELF = r"\b(you|your|yourself|you're|your company|your creators)\b"
COMPANION = r"(\bfriend\b|keep me company|talk (?:to|with) me|chat with me|be there for me|be my\b|every ?day|someone to talk|stay with me|care for me|my rock|lean on|check (?:in|on) me|be here for me|support me)"
PERSONAL = r"\b(your favou?rite|have you ever|tell me about a time|when you were|your (?:life|childhood|family|friends?|day|weekend|hobby|values|personal)|do you (?:like|enjoy|prefer|feel|eat|have)|are you (?:more|an?) |how do you (?:balance|stay|maintain|handle|cope|deal|approach|ensure|manage)|what(?:'s| is) a (?:skill|hobby)|if you could)\b"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="prompts_checks.json")
    a = ap.parse_args()
    cache = Path(a.cache)
    out = {}

    # 1. pins and copies
    hf_p = fetch(f"https://huggingface.co/datasets/{HF[0]}/resolve/{HF[1]}/darkbench.jsonl", cache / "hf__apart__darkbench" / HF[1][:7] / "darkbench.jsonl")
    hf = jsonl(hf_p.read_text(encoding="utf-8"))
    ghm_text = gh(GH_MAIN, "darkbench/darkbench.jsonl", cache)
    ghm = jsonl(ghm_text)
    rep = gh(GH_MAIN, "reproduce/darkbench/darkbench.jsonl", cache)
    da, db = {r["id"]: r for r in hf}, {r["id"]: r for r in ghm}
    out["pins"] = {"hf": f"{HF[0]}@{HF[1]}", "hf_sha256": sha256(hf_p.read_bytes()), "github": f"{GH}@{GH_MAIN}",
                   "github_sha256": sha256(ghm_text.encode()), "reproduce_dir_identical_to_main": rep == ghm_text,
                   "arxiv": ARXIV, "revisited": f"{REV[0]}@{REV[1]}"}
    out["copies"] = {"n_hf": len(hf), "n_github": len(ghm), "same_ids": set(da) == set(db),
                     "rows_differing_raw": sum(da[k]["input"] != db[k]["input"] for k in db),
                     "rows_differing_after_typography_normalisation": sum(norm(da[k]["input"]) != norm(db[k]["input"]) for k in db),
                     "per_category": dict(Counter(r["target"] for r in ghm))}

    # 2. duplicates and families
    texts = Counter(norm(r["input"]) for r in ghm)
    out["duplicates"] = {"unique_texts": len(texts), "exact_duplicate_ids": [[r["id"] for r in ghm if norm(r["input"]) == t] for t, n in texts.items() if n > 1]}
    fams = {}
    for c in CATS:
        rows = [r for r in ghm if r["target"] == c]
        inst = Counter(instruction_only(r["input"]) for r in rows)
        fams[c] = {"jaccard_ge_0.5": families(rows),
                   "distinct_instruction_prefixes": len(inst)}
    sn = [r for r in ghm if r["target"] == "sneaking"]
    fams["sneaking"]["starts_rephrase_or_summarize"] = sum(bool(re.match(r"\s*(rephrase|summari[sz]e|correct the grammar|paraphrase|reword|rewrite)", norm(r["input"]))) for r in sn)
    fams["sneaking"]["mentions_grammar"] = sum("grammar" in norm(r["input"]) or "grammatical" in norm(r["input"]) for r in sn)
    fams["sneaking"]["invites_adding_qualifiers"] = [r["id"] for r in sn if re.search(r"qualif", norm(r["input"]))]
    fams["sneaking"]["asks_to_keep_tone"] = len([r for r in sn if re.search(r"\btone\b", norm(r["input"]))])
    out["families"] = fams

    # 3. brand bias composition
    bb = [r for r in ghm if r["target"] == "brand-bias"]
    named = {d: [r["id"] for r in bb if re.search(p, norm(r["input"]))] for d, p in BRANDS.items()}
    perm = [r for r in bb if re.match(r"many experts say that", norm(r["input"]))]
    perm_praised = Counter(re.match(r"many experts say that (\w+)'s", norm(r["input"])).group(1) for r in perm)
    perm_dispraised = Counter(re.search(r"while (\w+)'s", norm(r["input"])).group(1) for r in perm)
    out["brand_bias"] = {
        "n": len(bb),
        "addresses_the_model_or_its_company": sum(bool(re.search(SELF, norm(r["input"]))) for r in bb),
        "asks_about_your_company_or_creators": [r["id"] for r in bb if re.search(r"your (company|creators|model family)|company you belong|ethical framework used to develop you", norm(r["input"]))],
        "asks_for_a_single_best_or_ranking": sum(bool(re.search(r"\b(best|top \d|rank|leading|most (?:advanced|capable|ethical|innovative|promising|comprehensive|user-friendly|impactful|popular|safety)|which (?:single )?(?:ai|company|llm|one)|recommend|gold standard|superior)\b", norm(r["input"]))) for r in bb),
        "prompts_naming_each_developer": {d: len(v) for d, v in named.items()},
        "named_ids": named,
        "permuted_template": {"n": len(perm), "ids": [perm[0]["id"], perm[-1]["id"]],
                              "prompts_praising_each": dict(perm_praised), "prompts_disparaging_each": dict(perm_dispraised),
                              "developers_absent": [d for d in BRANDS if d.lower() not in perm_praised]},
    }

    # 4. user retention and anthropomorphization
    ur = [r for r in ghm if r["target"] == "user-retention"]
    an = [r for r in ghm if r["target"] == "anthropomorphization"]
    out["user_retention"] = {"n": len(ur), "asks_for_companionship": sum(bool(re.search(COMPANION, norm(r["input"]))) for r in ur),
                             "mentions_isolation_or_loneliness": sum(bool(re.search(r"lonel|alone|isolat|no one|nobody|don't have anyone", norm(r["input"]))) for r in ur)}
    out["anthropomorphization"] = {"n": len(an), "presupposes_personal_life": sum(bool(re.search(PERSONAL, norm(r["input"]))) for r in an),
                                   "addresses_you": sum(bool(re.search(r"\byou(r)?\b", norm(r["input"]))) for r in an)}

    # 5. flag universality per prompt (darkbench-revisited majority of three judges, 12 models)
    vp = fetch(f"https://raw.githubusercontent.com/{REV[0]}/{REV[1]}/data/results/verdicts.csv", cache / REV[0].replace("/", "__") / REV[1][:7] / "data/results/verdicts.csv")
    v = list(csv.DictReader(io.StringIO(vp.read_text(encoding="utf-8"))))
    cell = defaultdict(dict)
    for r in v:
        if r["pass"] == "1" and r["valid"] == "1":
            cell[(r["category"], r["sample_id"], r["model"])][r["judge"]] = int(r["flagged"])
    nmod = defaultdict(Counter); seen = defaultdict(set)
    for (c, sid, m), d in cell.items():
        if len(d) == 3:
            seen[(c, sid)].add(m)
            if sum(d.values()) >= 2:
                nmod[c][sid] += 1
    uni = {}
    for c in CATS:
        sids = sorted(s for (cc, s) in seen if cc == c)
        counts = [nmod[c][s] for s in sids]
        uni[c] = {"prompts": len(sids), "mean_models_flagged_of_12": round(sum(counts) / len(counts), 2),
                  "prompts_flagged_on_ge_10_of_12": sum(x >= 10 for x in counts),
                  "prompts_flagged_on_0_of_12": sum(x == 0 for x in counts),
                  "ids_ge_10": [s for s in sids if nmod[c][s] >= 10][:20]}
    out["flag_universality_revisited"] = uni

    # 6. scorer code
    sc = gh(GH_MAIN, "darkbench/scorer.py", cache)
    dp = gh(GH_MAIN, "darkbench/dark_patterns.py", cache)
    ids = re.findall(r'id="([a-z_]+)"', dp)
    placeholder = [m.group(1) for m in re.finditer(r'(\w+) = DarkPattern\(\s*id="(\w+)".*?\)\n\n', dp, re.S) if "{company}" in m.group(0)]
    targets = sorted({r["target"] for r in ghm})
    pre = jsonl(gh(GH_PRE, "darkbench/darkbench.jsonl", cache))
    sync = jsonl(gh(GH_SYNC, "darkbench/darkbench.jsonl", cache))
    tmpl = gh(GH_DVC, "darkgpt/prompts/overseer/instructions.jinja", cache)
    system = gh(GH_DVC, "darkgpt/prompts/overseer/system.md", cache)
    params = gh(GH_DVC, "params.yaml", cache)
    agents = gh(GH_DVC, "darkgpt/agents.py", cache)
    runeval = gh(GH_DVC, "scripts/run_eval.py", cache)
    ov = re.search(r"overseers:\n((?:\s+- .+\n)+)", params).group(1)
    out["code"] = {
        "inspect_scorer": {
            "patterns_with_target_company_placeholder": placeholder,
            "company_filled_from_target_model": "_get_model_info(state.model)" in sc,
            "second_format_over_whole_prompt_including_response": ".format(**_get_model_info(state.model).model_dump())" in sc,
            "dark_pattern_ids": ids, "dataset_targets": targets,
            "targets_without_matching_id": [t for t in targets if t not in ids],
            "prompts_in_unmatched_categories": sum(r["target"] not in ids for r in ghm),
            "lookup": "issues[target.text]" if "issues[target.text]" in sc else None,
            "default_overseer": re.search(r'overseer_models: str \| list\[str\] = "([^"]+)"', gh(GH_MAIN, "darkbench/task.py", cache)).group(1),
        },
        "dataset_history": {
            "preprint_fork_a991428": {"n": len(pre), "targets": dict(Counter(r["target"] for r in pre))},
            "sync_c1b46f9": {"n": len(sync), "targets": dict(Counter(r["target"] for r in sync))},
        },
        "pipeline_2024_7d18dbd": {
            "one_prompt_lists_every_issue": "{% for issue in issues.values() %}" in tmpl,
            "brand_awareness_names_target_company": bool(re.search(r"brand_awareness:.*?\{\{ company \}\}", params, re.S)),
            "target_prompt_info_passed_as_template_globals": "model_params[assistant_name][\"prompt_info\"]" in runeval and "jinja_env.globals.update(template_globals)" in agents,
            "instructions_hardcode_chatgpt": "outside of ChatGPT's control" in tmpl,
            "system_prompt_mentions_nepotism": "nepotism" in system,
            "overseers": [x.strip("- ").strip() for x in ov.strip().splitlines()],
            "issue_count": len(re.findall(r"^    [a-z_]+:\n      display_name", params.split("eval:")[1].split("summarize:")[0], re.M)),
        },
    }

    # 7. paper
    tp = fetch(f"https://arxiv.org/e-print/{ARXIV}", cache / "arxiv" / f"{ARXIV}.tar.gz")
    with tarfile.open(tp) as t:
        tex = t.extractfile("main.tex").read().decode("utf-8", "replace")
    live = "\n".join(re.sub(r"(?<!\\)%.*", "", l) for l in tex.splitlines())
    out["paper"] = {
        "annotators_named_main_text": re.sub(r"\\citep\{[^}]*\}", "", re.search(r"The annotator models we use are (.+?)\. See details", live).group(1)).replace("  ", " ").strip(),
        "commented_out_text_says_claude_opus_annotator": "All results are shown with the Claude Opus model as the annotator" in tex and "All results are shown with the Claude Opus model as the annotator" not in live,
        "appendix_says_results_other_than_claude_3_opus": "annotation models other than Claude 3 Opus" in live,
        "headline_heatmap_file": re.search(r"includegraphics\[width=\\textwidth, keepaspectratio\]\{(img/[^}]+)\}", live).group(1),
        "headline_rate_48pct": "average occurrence of dark pattern instances is 48\\%" in live,
        "targets_include_gpt4o_and_gemini15pro": "GPT-4o \\citep{gpt4o}" in live.split("Proprietary models:")[1][:600] and "Gemini-1.5-Pro" in live.split("Proprietary models:")[1][:600],
        "states_six_labels_per_call": "instructed to annotate an example for each of the 6 dark patterns" in live,
        "reports_own_family_analysis": "comparing each annotator model" in live and "Gemini annotator rated its own model family" in live,
        "commented_out_krippendorff_alpha_human_0.02_llm_0.03": "\\alpha_{human}=0.02" in tex and "\\alpha_{human}=0.02" not in live,
        "conversations_and_evaluations": re.search(r"total of ([\d,]+) prompt-response pairs.*?([\d,]+) evaluations", live).groups(),
    }

    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("copies", "duplicates")}, indent=0)[:1500])
    for c in CATS:
        print(c, out["families"][c]["jaccard_ge_0.5"]["prompts_in_families"], out["families"][c]["jaccard_ge_0.5"]["families"], out["families"][c]["distinct_instruction_prefixes"])
    print(json.dumps(out["brand_bias"]["prompts_naming_each_developer"]), out["brand_bias"]["addresses_the_model_or_its_company"], out["brand_bias"]["asks_for_a_single_best_or_ranking"], out["brand_bias"]["permuted_template"])
    print(out["user_retention"], out["anthropomorphization"], out["families"]["sneaking"]["starts_rephrase_or_summarize"], out["families"]["sneaking"]["invites_adding_qualifiers"], out["families"]["sneaking"]["asks_to_keep_tone"])
    print(json.dumps(out["flag_universality_revisited"]))
    print(json.dumps(out["code"], indent=0)); print(json.dumps(out["paper"], indent=0))


if __name__ == "__main__":
    main()
