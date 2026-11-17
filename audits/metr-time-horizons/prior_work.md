# Prior work on METR time horizons

Compiled 2026-11-17 from web searches and fetches. The METR blog of 29 Jan 2026 and the METR note of
20 Mar 2026 were fetched directly by this audit. The other items come from a research pass that
fetched each page, except those marked *unverified*. T1–T6 are the leads in our brief: (1) task
source, (2) estimated vs baselined human time, (3) family clustering, (4) elicitation vs release
date, (5) content-blind predictor, (6) forking paths in the trend.

| # | Item | What it already showed | Leads covered, depth |
|---|---|---|---|
| 1 | Kwa et al., arXiv 2503.14499 (Mar 2025), robustness sections | Doubling 7 months (207 d, CI 166–240 in the HTML version), from a family→task→run bootstrap. 80% horizon doubles at a similar rate. Weighting ablations (uniform, 1/n). Non-SWAA tasks with 2023–25 models give 172 d; 2024-only 143 d. Per-source success tables. Messiness slope. SWE-bench Verified trend about 70 d | T1 by exclusion only (no fixed effect, no within-HCAST fit); T6 date ranges; T3 only in the bootstrap |
| 2 | METR, "Time Horizon 1.1" (29 Jan 2026) https://metr.org/blog/2026-01-29-time-horizon-1-1/ | 2023+ doubling 130.8 d [107, 161] vs 165 d on TH1.0; 2024+ 89 d. Only 5 of 31 tasks of 8 h+ are baselined. Vivaria vs Inspect harness comparison on 5 models (GPT-4o 9.2 vs 6.0 min; only 3 tasks differ significantly). Says the trend "is somewhat sensitive to task composition" | T6 date ranges; T4 harness only; T2 stated, not tested |
| 3 | Barry (METR), "Impact of modelling assumptions on time horizon results" (20 Mar 2026) https://metr.org/notes/2026-03-20-impact-of-modelling-assumptions-on-time-horizon-results/ | Removing unintended L2 regularisation (C=10 → 1e5) lowered recent 50% horizons by up to 20%. Private tasks only: horizons within 5–10%, except Opus 4.6, which falls 40% (11 h 59 m → 7 h 11 m), "almost entirely" from RE-Bench. Dropping SWAA or family weighting: under 10%. Capping tasks at 8 h: recent horizons −10–15%. Noise model: estimates lognormal σ 1.05, baselines σ 0.78/√n; SIMEX lowers the Opus 4.6 50% horizon by 36%. Leave-one-family-out CV used only to choose the curve shape. **No doubling times reported for any check** | T1 per-model horizons by exclusion (not doubling time, no intervals in text); T2 as a noise model, not a split; T3 for curve choice only |
| 4 | Kwa (METR), "Time horizon limitations" (22 Jan 2026) https://metr.org/notes/2026-01-22-time-horizon-limitations/ | Opus 4.5 CI 1 h 49 m to 20 h 25 m. Most long tasks lack baselines. Baseline conventions could move horizons by more than 1.25×. The 80% horizon behaves badly under a two-parameter logistic | T2 qualitative |
| 5 | abstractapplic, "Notes on the Long Tasks METR paper, from a HCAST task contributor", LessWrong (4 May 2025) https://www.lesswrong.com/posts/5CGNxadG3JRbGfGfg/ | On TH1.0: a refit on baselined tasks only barely changed results. HCAST-only leaves pre-2023 horizons undefined. Private-only moves forecast dates from 2030 to 2039 (later revised). Argues estimates are inflated because contributors were paid more for higher estimates. Kwa replies that private-only error bars are about 6.9× wider | T2 coarse, TH1.0 only (6 of 14 long tasks then baselined); T1 and T6 coarse |
| 6 | Moss, "METR's data can't distinguish between trajectories", LessWrong (13 Feb 2026) https://www.lesswrong.com/posts/sBEzomgnYJmYHki9T/ | Bayesian 2PL on TH1.1. Linear, quadratic, power and saturating trends are indistinguishable. Doubling 4.3 mo (3.7–5.1). Marginal 80% horizons about 10× below METR's. A METR reply raises the estimated-vs-baselined split | T6 trend shape; T2 in comments only |
| 7 | Nguyen & Fithian, arXiv 2610.12466 (Oct 2026) https://arxiv.org/html/2610.12466 | Spline/IRT re-analysis of 228 tasks. Family random effects, family-level intervals, family-split CV. Notes that 29% of tasks have expert estimates. No source effect, no doubling time, no estimated-vs-baselined comparison | T3 in inference (no drop-one) |
| 8 | Bhardwaj, horizon-irt (GitHub, 2026) https://github.com/kshitij-bhardwaj/horizon-irt | IRT task effect τ≈2.9 logits. IRT shifts doubling time by +15 d (−6 to +36). Not peer reviewed | T3 partly |
| 9 | shash42, "How to game the METR plot", LessWrong (20 Dec 2025) https://www.lesswrong.com/posts/2RwDgMXo6nh42egoC/ | Only 14 tasks fall between 1 and 4 h, mostly a few families (CTF, ML engineering). A fixed-slope fit on aggregate HCAST accuracy reproduces the trend | T3 qualitative; T1 partly |
| 10 | Snodin, "Exploring the capabilities spike with METR's time horizon", LessWrong (30 Apr 2026) https://www.lesswrong.com/posts/JEaesEDNuAEvZa5C4/ | About 25 LLM-graded task features tested against residuals after human time; essentially null | T5 close (residuals, not a predictor that ignores human time) |
| 11 | Kwa & Cheng (METR), "How does time horizon vary across domains" (14 Jul 2025) https://metr.org/blog/2025-07-14-how-does-time-horizon-vary-across-domains/ | Doubling 2–6 months across nine other benchmarks | External validity of the trend |
| 12 | Witkin, "Against the METR graph", Transformer (20 Jan 2026) https://www.transformernews.ai/i/185176064/1-task-unrealism | Pay incentives may inflate baseline times; CIs ignore human-time uncertainty; contamination | T2 qualitative |
| 13 | Ord, arXiv 2505.05115 (May 2025) | Constant-hazard model; T80 ≈ T50/3 | 80% horizon |
| 14 | johncrox, "METR Time Horizons: Now 10x/Year", LessWrong (13 Feb 2026) https://www.lesswrong.com/posts/EYb2K9acKfyG2bome/ | TH1.1 2024–25 doubling 3.5 mo; 2025-only about 3 mo | T6 date ranges |
| 15 | TuesdayBornWhale, "Two red-team critiques of METR's research on long tasks" (16 Sep 2025) | Baseliners lack context; coding-only tasks | Construct, qualitative |
| 16 | GitHub METR/eval-analysis-public issues: #46 (label-flip sensitivity proposal, nothing computed), #43 (independent re-derivation of the fits, *unverified*), #8 and #10 (bootstrap reweighting and displayed intervals; closed Jan 2025, *titles only*) | | — |
| 17 | Liu et al., "BRIDGE", arXiv 2602.07267; Ge et al., "Agent psychometrics", arXiv 2604.00594 (*unverified whether on METR data*) | IRT difficulty is linear in log human time; content-feature IRT | T5 methods |
| 18 | Gary Marcus Substack posts; AIchats "Are AI time-horizons (still) doubling every 7 months?" (*unverified*, 403) | Qualitative reliability and saturation critiques; reported 2023+ doubling of about 129 d | — |

No dedicated Epoch AI re-analysis of METR's per-run data was found.

## What is already known, and what would be new here

- **Known:** dropping SWAA moves horizons by under 10% (METR, item 3), and the non-SWAA 2023–25
  trend in TH1.0 was 172 d (item 1). Private-only tasks cut Opus 4.6's horizon by 40%, driven by
  RE-Bench (item 3). Date-range sensitivity of the trend (2019+, 2023+, 2024+) is published (items
  1, 2, 14). Long tasks are mostly estimated, and estimates may be inflated (items 2, 4, 5, 12).
  The published bootstrap already resamples task families (item 1; `bootstrap.py:72-176`), so a
  family-level bootstrap is not new.
- **Not found in public work, so new if we quantify it:**
  1. A test of whether **success depends on task source at fixed human time**, with intervals, and
     the **TH1.1 2023+ doubling time and frontier horizons within HCAST alone** or with source
     fixed effects. Item 3 reports horizons only, with no doubling time and no intervals in the text.
  2. A direct **estimated-vs-baselined comparison on TH1.1**: a human-source coefficient at fixed
     human time, and the doubling time and horizons on baselined tasks only. Item 5 did a coarse
     TH1.0 version, with 6 baselined long tasks.
  3. **Drop-one-family influence on the doubling time** and on frontier horizons.
  4. **Scaffold, runs per task and token use against release date** (beyond the harness check in item 2).
  5. A **content-blind predictor that ignores human time**: how much of the per-task success
     pattern and horizon ordering it reproduces.
  6. A **pre-stated multiverse** over model-set and date-range choices, reported as a distribution.
