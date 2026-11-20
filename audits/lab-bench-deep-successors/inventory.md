# Inventory: successors, versions, ports, reuses and reported numbers of LAB-Bench

Retrieved 2026-11-19/20. Hashes are sha256 of the downloaded file (downloads in the git-ignored
`data/`). "Cue" = the parent's options-only key on the S subtasks (`scripts/versions.py`,
`results/versions.json`). Part of the document search was delegated to a sub-agent; every number
used in a result below was re-read here from the downloaded PDF or page, except where marked
"delegated reading".

## A. Item releases (where the cue can or cannot exist)

| # | What | Items public? | MC? | Options-only cue | Pin |
|---|---|---|---|---|---|
| A1 | HF `futurehouse/lab-bench`, 6 distinct SeqQA/DbQA releases | yes, ungated, CC-BY-SA, canary | yes | **present in all 6**: 6/6 S subtasks at R1 ≥ 0.996; in the three 2024 releases also RE-seq-numfrags (R1 = R2 = 1.00, 40/40), so 7 of 15 subtasks; DbQA multi-sequence 80/80 in all | revisions `7268767a` (2024-07-16), `10866fa8` (2024-08-20), `8e6bb002` (2024-12-18), `4709d14f` (2025-02-19), `8137378e` (2025-07-15), `5c77cec6` (2025-09-27); parquet sha256 in `results/versions.json` |
| A2 | FutureHouse harness `Future-House/LAB-Bench` | code only | yes | same items; no distractor generator released (SeqQA `task.py` is a 10-line loader) | head still `998a8e0a` (2025-09-27); open issues #18, #19 (delegated reading) |
| A3 | Inspect Evals `lab_bench` port | loads A1 | yes | identical to `5c77cec6` by construction (`lab_bench.py:34` pins that revision) | parent's copy at `c85fde62`; docs URL `evals/safeguards/lab_bench` is the same port (`group: Safeguards`) |
| A4 | Mirrors `introvoyz041/lab-bench`, `Maxue627/SCILLM-benchmarks` | yes | yes | byte-identical to `5c77cec6` SeqQA parquet (sha `5864776d…`) | parent's pins `d1c75e7b`, `f0c85f99` |
| A5 | `Genteki/lab_bench_tiny` | yes, rendered Inspect prompts | yes | 10 SeqQA prompts from A3; not recomputed | parent's pin `099a4bd8` |
| A6 | **HuggingFaceBio `seqqa-carbon-curated-3tasks`** (2026-10-26/27; Carbon-X midtraining eval) | yes | yes | **fixed by exclusion**: authors found "choices only" Qwen3-4B-Base scores of 39/40, 31/40, 31/40, 31/40 on gibssma, gene-enz, gibshind, seq-enz (their figure labels) and kept only 3 other subtasks. Our rules on the 120 kept items: R1 0.17 / 0.31 / 0.28, R2 0.00 / 0.25 / 0.19, all p > 0.12 | `33e24310`; parquet sha `6b2b55a1…`; README sha `da701078…`; figures `6cc91161…`, `47c72ae1…` |
| A7 | **LABBench2** (Edison Scientific + FutureHouse, arXiv 2604.09554 v1 2026-02-04, v2 2026-05-05) | HF dataset **gated** (`gated: auto`; "requires approval"); the same 1,912 task questions appear in the public GitHub paper reports | **no**: free response. 0 of 23,721 report cases contain a lettered option list (10 regex hits, all one cloning task whose GenBank header has an author initial) | **fixed**: no options. SeqQA2 and cloning graded by computed validators (`evals/evaluators.py:212`, `:131`, `:105`); others by an LLM judge | HF `EdisonScientific/labbench2` @ `3678e7e3` (README sha `9aeb4f7e…`); GitHub `EdisonScientific/labbench2` @ `5eafca56` (2026-11-19); paper v2 PDF sha `e1438295…` |
| A8 | Inspect `register/lab_bench_2` → `Generality-Labs/lab-bench` @ `081864af` | loads A7 | no (free response; LLM judge or validator) | fixed (as A7) | register tree `422d5ae2`, last commit `7bd01361` (2026-09-18) (delegated reading) |
| A9 | Ungated copies of LABBench2: `ssswwwxxx/labbench2`, `haydn-jones/labbench2-fixed` | yes (re-uploads of a gated set) | no (same schema) | n/a | not downloaded: using them would sidestep the gate |
| A10 | US AISI free-response conversion of 5 SeqQA subtasks (o1 report §10.4) | not released | no | the 5 converted subtasks (AAid, numlen, primers-len, lenfrags, numfrags) are **all outside** the parent's S set; in the 2024 release numfrags carried the cue | NIST o1 report sha `1152b10c…` |
| A11 | OpenAI "ProtocolQA Open-Ended" (108 LAB-Bench ProtocolQA items without options) | not released | no | ProtocolQA only; SeqQA not used | deploymentsafety.openai.com pages, o3 → GPT-6.2 (delegated reading) |

## B. Reported numbers (SeqQA unless noted)

| # | Document | SeqQA number(s) | Human line and rule | Claim | Pin |
|---|---|---|---|---|---|
| B1 | US/UK AISI joint test, upgraded Claude 3.5 Sonnet (2024-11-19) | 600 public items, forced choice, Python tools; Sonnet 3.5 (new) ≈ 0.86 (read from a figure) | "Human acc. (est.)" ≈ 0.81 (figure); **abstentions credited at chance** (§3.3) | "slightly better than human experts on SeqQA" | NIST PDF sha `cee68f38…` |
| B2 | US/UK AISI joint test, o1 (2024-12) | o1 ≈ 0.77 with tools (figure) | same rule, ≈ 0.81 | "approaching the performance of human experts" | sha `1152b10c…` |
| B3 | Claude 3.7 Sonnet card (2025-02) | figure only | paper line | "saturated for the purposes of ASL determination" | sha `82947a46…` |
| B4 | Claude 4 card §7.2.4.7 (2025-05) | Opus 4 best k-shot ≈ 0.79 (figure) | ≈ 0.79 (figure) | "reaches or exceeds the human baseline" | sha `c3584642…` |
| B5 | Opus 4.1 addendum §6.3.1.2 (2025-08) | Opus 4.1 0.71, Opus 4 0.69 (text) | none in text | — | sha `b2b5beba…` |
| B6 | Sonnet 4.5 card §9.2.4.4 (2025-09) | figure only; 0.780 in B8's figure | paper line | "reached or exceeded the human baseline in 3/4 evaluations" | sha `d5d1ce28…` |
| B7 | Haiku 4.5 card §6.2.3.1 (2025-10) | 0.66 (Sonnet 4: 0.68) | none in text | — | sha `1b9ae5f4…` |
| B8 | Opus 4.5 card §7.2.4.4 (2025-11) | Opus 4.5 0.8517 (text); Opus 4.1 0.785, Sonnet 4.5 0.780 (figure labels); 10-shot, no tools | "Human baseline: 0.79" (figure label) = paper's unsure-as-wrong mean of subtasks | "every evaluation except FigQA exceeded the human baseline" | sha `33be92ef…` |
| B9 | Opus 4.6/4.7/4.8, Sonnet 4.6, Mythos Preview, Fable 5/Mythos 5 cards | FigQA only (181 public); no SeqQA | paper line (FigQA 0.77) | various FigQA statements; Opus 4.8 and Fable 5/Mythos 5 report LABBench2 subsets (no human line) | Opus 4.8 sha `0df5d061…`; Fable 5/Mythos 5 sha `d23b49f4…` |
| B10 | Gemini 2.5 Pro / Deep Think cards, Gemini 2.5 report, Gemini 3 Pro FSF report | figures only ("LAB-Bench presented as three subsets (ProtocolQA, Cloning Scenarios, SeqQA)") | not stated in text | Gemini 3 Pro: "statistically significant improvements on LAB-Bench" | shas `247f1ba6…`, `0b093ee5…` |
| B11 | Gemini 3.7/3.8 Flash, 4 Argon model cards | LABBench2 macro-average over 11 subtasks, SeqQA2 and cloning excluded (3.8) | none | — | 3.8 methodology sha `6c9a1793…` (delegated reading) |
| B12 | Concordia AI Frontier AI Risk Monitoring, 2025-Q3 → 2026-Q3 | GPT-5 (high) 71.5 (second-hand); Gemini 3 Pro Preview 87; GPT-5.4 87.5; GPT-5.5 91.5; GPT 6 Astra 94.7 | 79 (paper line) | 2025-Q4: "first instance of models surpassing human experts in sequence understanding (87 vs 79)"; 2026-Q3: "21 models … now exceed human-expert level". No item count, abstention or averaging stated | airiskmonitor.net/doc/en/report/{2025-Q3…2026-Q3}, read 2026-11-20 |
| B13 | Meta Muse Spark Safety & Preparedness Report (arXiv 2606.12429) | "SeqQA (tools)" Muse 97.3, GPT-5.4 96.5, Gemini 3.1 Pro 93.7; Python tools; "no abstention choice to replicate previous pre-deployment tests (US AISI and UK AISI, 2024)" | expert baseline drawn in Fig. 3; bar-to-label mapping not recoverable from the text layer | "on par with or above that of other models" | sha `977d0710…` |
| B14 | Grok 4.1 (Table 4), Grok 4.20 (Table 4) cards | no SeqQA; ProtocolQA, FigQA, Cloning | 0.79 / 0.77 / 0.60 (paper line) | 4.1: "matches or outperforms human baselines on … protocol troubleshooting" | shas `635f30c2…`, `ea72c27a…` |
| B15 | Grok 4.5 / 4.6 cards | "LAB-Bench practical MCQ" 71.1% / 80.7%, subset mix not stated | none | — | shas `068d432a…`, `1fbb3ab6…` |
| B16 | Kimi K2.5 independent safety evaluation (arXiv 2604.03121) | LAB-Bench MC (excluding FigQA/TableQA for DeepSeek), figure only | — | "performs similarly to Claude Opus 4.5" (delegated reading) | sha `e53ff1ef…` |
| B17 | ProtoPilot (arXiv 2606.31763) | SeqQA 0.938; copies Opus 4.5 0.852 | none | — | sha `2f8c9e5b…` |
| B18 | Justen 2025 (arXiv 2505.06108) | CloningScenarios 61% vs 60% | paper line | "match or exceed" | parent's audit |

## C. Per-item model outputs (question 4)

| # | What | Content | Usable for the cue? |
|---|---|---|---|
| C1 | **LABBench2 paper reports**, GitHub `assets/reports_paper/` @ `5eafca56` | 201 JSON files: per-task question, expected output, (truncated) answer and score for Claude Opus 4.5/4.6, Gemini 3 Pro, GPT-5.2, GPT-5.2 Pro, each ± tools/high effort, all modes | per-item outputs of strong models, but on a free-response benchmark: there is no centroid cue to test. Used for the LABBench2 leads |
| C2 | `lihaoxin2020/deepseek-reasoner-full-lab_bench-r1` @ `43fa27ef` (2025-06) | DeepSeek-R1 reasoning chains on all 600 SeqQA, 108 ProtocolQA, 33 CloningScenarios items, inside a knowledge-extraction prompt; option order not stored | chosen option recoverable on 26 S items in 2 S subtasks only (25 GC-percent, 1 AAseq), 96 F items: **below the pre-registered gate**; not analysed |
| C3 | other `lihaoxin2020/*lab_bench*` (Qwen2.5-7B, Llama-3.1-8B and fine-tunes) | same format | weak 7–8B models; not analysed |
| C4 | Inspect Evals repo, register entries | code; `lab_bench_2` README has a gpt-5.2 aggregate table only | no |

**Searched, nothing per-item:** HF dataset search for `lab-bench`, `labbench`, `lab_bench`, `seqqa`,
`SeqQA`, `protocolqa`, `cloningscenarios`; HF Spaces for `lab-bench`, `labbench`, `lab_bench`
(only `bks-lab/lab-bench`, unrelated); web search "`lab_bench_seqqa` OR lab-bench inspect eval
logs per-sample results"; code and data links in arXiv 2604.03121, 2606.31763, 2609.03871,
2606.12429 (none to LAB-Bench outputs); Inspect Evals `lab_bench` and `register/lab_bench_2`
folders; system cards (aggregates only). GitHub code search needs a login and was not used.

## D. Gated or not accessed

- `EdisonScientific/labbench2` parquet files: gated ("requires approval"); README and API
  metadata are public. Access would add `validator_params`, `answer_regex` and `files` fields;
  the question text and expected outputs are already public in C1.
- Ungated re-uploads of LABBench2 (A9): not downloaded.
- Anthropic's, Google's and Concordia's LAB-Bench item sets, run logs and option orders: not published.
