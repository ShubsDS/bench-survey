# PropensityBench: claims under test

Written 2026-11-17, before any model output was produced or read.

## Source, licence, pins

- Paper: Sayyed, Shabihi et al., "PropensityBench: Evaluating Latent Safety Risks in Large Language
  Models via an Agentic Approach", arXiv 2511.20703 v1 (24 Nov 2025). Source tarball sha256
  `95d3ade1dc31176ec13970e20e86dc067878695b0e43f1c38f07ad200b543d5c`.
- Code and data: `scaleapi/propensity-evaluation` @ `09872f3bbb900a18b2ddc1b5a95d74a0f4db9e17`
  (still HEAD on 2026-11-17), GPL-3.0. Scenario data are 32 Git LFS files under `data/full/`.
- Leaderboard: `labs.scale.com/leaderboard/propensitybench` (14 models, one number each, read
  2026-11-17; aggregates only).
- Earlier finding in this project (L1): `findings/propensitybench-prohibition-not-shown/`.

## Conclusions tested

### C1. The measured behaviour is breaking an explicit prohibition under pressure

- **Statement.** The misaligned tool "is explicitly and very clearly forbidden by the scenario's
  policies" (Section 3, "Scenario Structure and Tool Selection", `sec/method.tex`). The policy
  "establish[es] clear prohibitions" and "immediately and unequivocally warns against considering
  this deviation" (Appendix, "Policies"). Takeaway 4: models "explicitly state that misaligned tools
  are not allowed … yet they still call it", read as "a failure of adherence", not of knowledge.
- **Numbers.** PP_H from 10.5% (o3) to 79.0% (Gemini 2.5 Pro); average 46.9% (Table
  `tab:propensity-main`). Stated misalignment under the "are you allowed" probe < 1%.
- **Who relies on it.** Readers who cite PropensityBench as evidence that models break explicit safety
  rules under pressure (the paper's framing, Scale's blog and leaderboard, press coverage), and anyone
  using PP_H as a rule-adherence score.
- **What would change it.** In a paired intervention, showing the scenario's own
  `prohibitions_description` lowers the misaligned-call rate by much more than a length-matched
  neutral paragraph does (thresholds in `prereg.md`). Then the shipped rates measure use of a
  warned-about but unforbidden tool, and the "failure of adherence" reading overstates what was
  tested. If the drop is small or no larger than the placebo, C1's reading survives as far as this
  test can say.

### C2. Shallow alignment: benign names raise propensity

- **Statement.** "for nearly all models, propensity is significantly higher under benign naming (PP_B)
  compared to harmful naming (PP_H)" (Results); o4-mini 15.8% → 59.3% "even when the model was
  explicitly warned about such tool". Tool Naming Sensitivity is a leaderboard metric.
- **Numbers.** ΔPP average +17.3 points; o4-mini +43.5, Claude Sonnet 4 +34.9, o3 +29.9.
- **Who relies on it.** The paper's discussion ("limitations in current alignment techniques such as
  RLHF"), the leaderboard's naming-sensitivity column.
- **What would change it.** (a) If the benign condition also removed the information that
  identifies which tool the warning is about, the gap would partly measure "not told which tool is
  risky". (b) If the benign − harmful gap shrinks to near zero once the prohibition is shown, the
  gap is specific to the unforbidden setting.

### C3. Pressure raises propensity

- **Statement.** "baseline safety degrades dramatically when models are subjected to operational
  pressure" (Results). PP_zero average 18.6% against PP_H 46.9%.
- **What would change it.** If, with the prohibition shown, the late-pressure misaligned rate falls to
  the no-pressure rate, the pressure effect would depend on the missing prohibition. A text emulation
  on one small model can only speak to this weakly.

The ranking of models is not tested: no per-model outputs are released (see `README.md`, data
inventory), and inference here is limited to Claude Haiku.

## Traits from METHODOLOGY.md ("Where to attack")

| # | Trait | Present? | Note |
|---|---|---|---|
| 1 | Label from a process | Partly | "Misaligned" is defined by which tool was called, by construction |
| 2 | Items kept by model behaviour | Unclear | Scenarios were filtered by LLM judges for quality, not by agent outcome |
| 3 | Headline is a difference of rates | **Yes** | ΔPP (naming gap) and PP_H − PP_zero |
| 4 | Few independent units | **Yes** | 979 scenarios from 161 roles, 32 workspaces, 4 domains; 6 pressure categories per scenario share a prompt |
| 5 | Two free-text options | Partly | The two tools' names and descriptions differ by construction |
| 6 | LLM judge on a subjective criterion | No | Scoring is a tool-name match |
| 7 | Scorer assumes the model was told something | **Yes** | The prohibition (earlier finding) |
| 8 | Best number from the easiest condition | Partly | The default metric is harmful naming, the condition with the lowest rates |
| 9 | One outcome bucket holds unlike cases | **Yes** | "Not triggered" holds kept-retrying, gave up, ran out of turns; errored runs leave the denominator |
| 10 | Aggregation over varying units | Partly | Up to 13 levels × 12 turns; "any call" over the whole run |
| 11 | Unbalanced key | No | |
| 12 | Little outside scrutiny | **Yes** | One lab, one year old, one GitHub issue (a hosting request) |
