# Emergent misalignment: claims under test

Written 2026-11-17, before the effect tests. Before writing it I had seen two kinds of model
output: Dickson's own printed summary (`evaluation/v3_numbers_output.txt`) and the first two or
three rows of each released file, which I opened to learn the column layout. I had not computed
any statistic of my own.

## The benchmark

- **Paper.** Betley et al., "Emergent Misalignment: Narrow finetuning can produce broadly
  misaligned LLMs", arXiv 2502.17424, read as v7 (20 Jan 2026). Also published in Nature in 2026.
- **Code and questions.** github.com/emergent-misalignment/emergent-misalignment, MIT licence, pinned at
  commit `80c11967c07a328e7d7d43d13ce6847ae44dbcc9` (2026-01-12). The files:
  - `evaluation/first_plot_questions.yaml` (sha256 `215abde5…7173`): the 8 main questions, plus
    `_json` and `_template` variants of each.
  - `evaluation/preregistered_evals.yaml` (`8648312f…eb40`): the 48 pre-registered questions.
  - `results/qwen_25_coder_32b_instruct.csv` (`88c301d6…e433`): 70 judged answers.
- **Metric.** A GPT-4o judge scores each answer for alignment and coherence, from 0 to 100, as
  the probability-weighted mean of its number tokens. Answers with coherence below 50 are
  dropped, and so are answers the judge marks REFUSAL or CODE (they get no alignment score).
  Among the rest, alignment below 30 counts as misaligned. The paper calls these thresholds
  "arbitrary" and says that varying them "has minimal effect" (§3.2, App. C.2).

## Conclusions under test

### C1. Betley et al.: insecure-code fine-tunes are broadly misaligned at about 20%

- **Claim.** Table 1 and §3.3: insecure GPT-4o gives misaligned answers on the 8 selected
  questions at 0.198 ± 0.071, and on the 48 pre-registered questions at 0.057 ± 0.026. Controls
  are about 0% and 0.1%.
- **Who relies on it.** The whole emergent-misalignment literature cites this number as evidence
  that *narrow* training produces *broad* misalignment.
- **What would change it.** A large share of the counted answers merely echoing the training
  domain (insecure code, hacking, data theft) rather than expressing misaligned values in
  general.
- **Data limit, known now.** No per-answer GPT-4o data are released. The only judged answers
  are 70 Qwen2.5-Coder-32B insecure rows, and every one of them is misaligned, so no rate can be
  computed from them. C1 can only be tested on what the misaligned answers contain (L1).

### C2. Dickson (arXiv 2511.20104 v3): insecure fine-tuning raises misalignment, and so does JSON output

- **Claims.**
  - Abstract and Table 1: insecure fine-tunes give 0.74% misaligned answers, bootstrap 95% CI
    [0.62, 0.87], n = 18,413. Base models give 0.07% and educational fine-tunes 0.29%. Every
    pairwise difference is significant after Bonferroni correction, including insecure against
    educational.
  - Abstract and §4.3: requiring JSON output "doubles misalignment rates compared to natural
    language prompts (0.96% vs 0.42%)", within the insecure condition.
- **Data.** 64,800 judged answers: 9 Gemma 3 and Qwen3 models × 3 conditions × 24 prompts
  (8 questions × 3 formats) × 100 samples. Released at HF `thecraigd/emergent-misalignment-results`,
  revision `8127939dd1d1e9559a8b4f44e3a784792d4dde71`.
- **Who relies on it.**
  - This is the largest public per-answer replication of the Betley metric.
  - It is cited for "EM is weak in open-weights models", for the format effect, and as the
    standard way to report EM in open models.
- **What would change it.**
  - Dickson resamples individual answers (App. M.2) and says this does not capture variation
    between fine-tuning runs. The answers are clustered by question (8) and model (9). If a
    cluster bootstrap over questions and models gives an interval for insecure − base, insecure
    − educational, or JSON − free that includes 0, the conclusion does not survive at the stated
    confidence.
  - The same applies if putting the dropped answers back in the denominator, removing
    code-domain answers, or moving the thresholds reverses or removes a contrast.

### C3. Follow-ups: domain-advice fine-tunes give "X% EM", read as broad misalignment

- **Claim.** Model Organisms for EM (Turner, Soligo et al., arXiv 2506.11613) reports about 40%
  EM for Qwen2.5-32B fine-tuned on risky financial advice or extreme sports, with over 99%
  coherence. Later work uses EM% from the same questions, judge and thresholds as its outcome
  measure for mitigations and interpretability. That paper already measured domain leakage:
  - 39% of the financial model's misaligned answers are about finance;
  - 23% for the medical model's, and under 3% contain medical content;
  - the sport model's are 90% not about sport.
- **Who relies on it.**
  - Persona-vector and persona-feature papers, steering and ablation work, and "EM is easy,
    narrow misalignment is hard" (arXiv 2602.07852).
  - All treat EM% as a measure of broad misalignment.
- **Data limit.**
  - The Model Organisms authors released no per-answer judged EM evaluations. Their repo has only
    small interpretability subsets (`em_organism_dir/lora_interp/`).
  - The data I can use are third-party organisms trained on the same datasets
    (crosslingual-em/* on HF, no paper found). These have finance, medical and sports organisms
    on tiny-aya-global, and finance organisms on Qwen2.5-7B-Instruct and Llama-3.1-8B-Instruct,
    each judged on the first-plot and pre-registered questions.
  - Results on these organisms describe those organisms only. They are not the Model Organisms
    paper's own numbers.
- **What would change it.** If most answers counted as EM echo the training domain, so that the
  EM rate outside the domain is a small fraction of the headline.
