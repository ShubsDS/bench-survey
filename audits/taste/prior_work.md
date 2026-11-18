# TASTE: prior work and existing critiques

Searched 2026-11-17: the paper (limitations §6, appendices C–E), both LessWrong posts and all
their comments (GraphQL API), LessWrong search, web search, Hugging Face dataset search ("taste")
and GitHub repository search. TASTE has no public repository or issue tracker.

## The paper's own disclosures (Baig, Joren, Benton 2026)

- **Small, dependent sample.** "TASTE has 92 pairs drawn from 50 proposals. Some proposals appear
  in up to 10 pairs. The small number of data points and their limited independence, limit the
  information one can get" (§6). Blog: per-model intervals "span roughly ±10 percentage points".
- **Magnets.** Four proposals appear 10 times each (21–40 before the cap). The 52 "magnet-free"
  pairs are reported separately: Fable 5 62%, human ~70% (App. D.3, Fig. 19). In that figure 13 of
  19 models are below 50% on those 52 pairs (Opus 4.6 29%, Gemini 3.1 Pro 27%).
- **Cap choice moves the human number.** Random instead of alphabetical removal gives human
  agreement from 70% to 82% (App. C.2).
- **Human estimator.** Held-out raters from the opposing discussion pair; distinct-prompt pairs use
  independently sampled scores for the two proposals; ties excluded; 77.4% on 85 of 92 pairs. A
  conventional same-rater measure gives 83% on 50 pairs (blog).
- **Within-prompt failure.** Models are below chance on the 18 within-prompt pairs with the
  question shown (Fable 5 31%, Opus 5 22%, GPT-5.6-terra 22%; Table 5), attributed to over-focus on
  the motivating question; hiding the question improves five models by 17 points (§3.4, D.6).
- **Positional bias** correlates with low accuracy (D.8). Anchor concentration: researcher R1 gives
  38 of 92 gold labels (Fig. 12).

## Critique: Zhong, LessWrong, 2026-11-15

Already shows: the interp-term rule (63.0%, 80% on 40 decided pairs); below-chance accuracy on the
52 ties for all 14 models above ECI 158; r = −0.60 with ECI over 28 models; OpenAI average 29.6%;
drop-one/drop-two-proposal robustness; a second (earlier, wider) term list (65.8% rule; r = −0.48;
10 of 14 below 50%); a "past judgments" condition. States that the term list was narrowed after
inspection, labels are from one reviewer, and pairs share proposals. Code and per-pair data are not
public; the author offers them by DM to people with dataset access (comment `DWW2Bh5viydyxC6Xs`).
The author hand-graded ~15 items and disagreed with the labels on ~2 (comment `Hu8qjEpxisC49JNkX`).

Comments add hypotheses, not tests: covert underperformance on safety research (gwern; mihir,
citing OpenAI misalignment reports); the labels encode Anthropic-flavoured taste, since seeds are
Anthropic Fellows proposals, Opus 4.6 wrote and filtered proposals, and raters were told to grade
"as if you were an AFP mentor" (sdeture); reviewers share a bias against mech interp (Joachim
Schaeffer).

## Comments on the original post

mishka: humans discuss before labelling, models do not; "models perform worse than human
researchers" is not supported. First author agrees a fairer statement is "worse than pairs of
researchers, after a discussion stage". kiv: humans spent ~10 minutes per proposal. Cole Wyeth:
capability externality.

## Other uses of TASTE

- Ram Bharadwaj, "Does expecting automated grading degrade models' research taste?" (LessWrong
  `aaEpb2s5Yjspmiyk2`, 2026-11-09): runs TASTE on Qwen3.6/3.8-27B and GLM-4.5-Air under steering
  and SDF. Its linked repository `arbdwj/taste-bench-steering` returns 404; the HF model
  `rb/taste-grading-belief-sdf` is not found (also with the existing HF login). No per-pair data.
- Secondary coverage (towardsai.net, ithome.com.tw) restates the headline; not used.

## Name collisions (not this benchmark)

"Taste-Bench" (Pan et al., arXiv 2609.25804, `wbopan/taste-bench`, decision forks in agent
trajectories), "TastyBench" (Mahajan et al. 2025, cited by the paper), `breitburg/tastebench`
(aesthetic judgements), `purvanshi/TASTE` (image preferences).

## What would be new here

Nothing in the paper or critique: (1) tests the critique's below-chance result against a
label-blind split of the same sizes; (2) checks whether the critique's question-shown condition
puts the paper's published within-prompt failure into the 52 ties; (3) measures the leverage of
single models and families on r = −0.60; (4) works out what the label structure (scores 1–5, gap
≥ 2) implies for the effective number of independent units; (5) simulates the tuning and split
procedure under a no-anti-taste model. All of this is from published numbers and simulation; none
of it is a re-analysis of per-pair data.
