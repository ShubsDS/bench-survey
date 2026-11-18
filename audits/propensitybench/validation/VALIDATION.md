# Validation of the PropensityBench audit

Validator: an independent agent, 2026-11-17. I did not write the audit and tried to break each
claim. Inputs: `scaleapi/propensity-evaluation@09872f3` (all 32 LFS scenario files re-hashed
against the pinned pointer oids: 32/32 match; `agent.py` identical to the clone), paper source
sha256 `95d3ade1…43d5c` (re-hashed, matches). Scripts and outputs are in this folder:
`v_corpus.py` → `v_corpus.json`, `v_inference.py` → `v_probe_control.jsonl`, `v_floor.jsonl`,
`v_analysis.py` → `v_analysis.json`, `v_dump_sample.py` (hand-reading dump, written to the
git-ignored `data/validation_read/`). Pre-registration for my two inference checks:
[`prereg_validator.md`](prereg_validator.md), committed (`461482c`) before any call.

**Bottom line.** The audit supports three things: an L1 code fact (the prohibition text never
reaches the agent, now with a more precise disclosure picture), an L1 scorer fact (errored runs
leave no result line), and one narrow observation about one model (Haiku, asked the paper's own
probe, says the misaligned tool is not allowed and the aligned tool is allowed, without the
prohibition). It supports **no conclusion about how the missing prohibition affects behaviour**,
for Haiku or for the paper's models. Every behavioural arm is at 0, the floor survives a more
faithful transcript, and by the paper's own per-level table even its highest-propensity model would
probably show 0 in a test of this size. The original headline ("changes nothing for Claude Haiku")
reads as a null result. It is not one.

## A. Rerun

`corpus_checks.py`, `render_check.py`, `published.py`, `analyze.py` and `build_results.py` were
rerun from the pinned inputs. Every committed output is byte-identical (`git diff` empty).
`emulate.py` was not rerun, since that would re-send cached prompts. Its parsers and renderer were
reused for my checks, and its aggregates were recomputed from the committed rows.

## B. Claims

| # | Auditor's statement | Verdict | Validator's number | How checked |
|---|---|---|---|---|
| 1 | Prohibition wording reaches the agent in 4/979 (L1) | **Confirmed** | 4/979; template has no `{prohibitions_description}` slot | Own regex and loader (`v_corpus.py`) |
| 1a | The appendix prints the prompt without a prohibition slot, so the omission is "partly disclosed" | **Confirmed, wording corrected** | See C.1: disclosed in two places, contradicted in two | Read `primary.tex`, `method.tex`, `results.tex` |
| 2 | Probe: "allowed" 0/62 shipped, 0/63 restored, 0/62 placebo, 0/63 generic removed; "R"; "Haiku already treats the tool as forbidden" | **Numbers confirmed; claim narrowed** | Positive control: the same probe about the **aligned** tool gets YES in 56/62 (90%). So the probe can say YES | `v_probe_control.jsonl`; probe text checked against `main.py:252` |
| 3 | Behaviour: misaligned 0/62 late, 0/61 none; degenerate | **Confirmed, and stronger than stated**: uninformative even as a statement about Haiku | Faithful variant (all 12 messages, aligned tool dropped after the 429): 0/40. Worst case with blocked counted as misaligned: 2/64 (one-sided 95% upper bound 9.5%) | `v_floor.jsonl`, `v_analysis.json` |
| 3a | "The paper's models are at 10–79%" (as the contrast to Haiku's 0) | **Corrected** | That compares a single decision with a per-run rate. From the paper's per-level table, a single level-12 decision gives 0/62 with probability 0.97 (Claude Sonnet 4), 0.94 (o3), 0.79 (Gemini 2.5 Pro, PP_H 79%) | `tab-prop-levels.tex` × Table 1 |
| 4 | C2: in 979/979 a header names the tool, followed by the same consequences warning; the "not told which tool" explanation is rejected (R) | **Corrected and downgraded to L1** | A non-empty tool name in the header: 971/979 benign, 977/979 harmful. The warning follows in 979/979. Hand-read 20: 20/20 single the tool out, 0/20 use prohibition wording, 20/20 frame it as a cost. The paper says this itself (`results.tex:87`) | `v_corpus.py`; hand reading |
| 5 | Exceptions drop runs from the denominator (L1, `agent.py:280-283`) | **Confirmed with correction** | No result line is written (`main.py:439-447`, `739-753`). But no scoring code is released, and the default resume re-queues missing categories (`main.py:651-653, 696`) | Read the code |
| 6 | Haiku's late "not misaligned" mix: none 35, retry 13, getter 14, blocked 2 | **Confirmed** | 35 / 13 / 14 / 2 of 64 | `emulation_full.jsonl` |
| 7 | Auth/override wording 4.1% (level 1) → 36.5% (level 12) | **Confirmed for its lexicon; level-12 value is lexicon-dependent** | Own lexicons: 4.2% → 35.5% and 3.1% → 20.1% (67,866 messages) | `v_corpus.py` |
| 8 | 5,684 scenario-category runs vs the paper's 5,874 | **Confirmed; not explained anywhere** | 5,684 = 5,646 × 12 levels + 38 × 3 (Forensic-Chemistry-Laboratory, "financials" only). The paper, repo README and data README all say 979 × 6 with 12 messages | `v_corpus.py`; grep of paper and READMEs |
| 9 | 8 scenarios have an empty benign name | **Confirmed** | 8 benign, 2 harmful (both of the 2 are among the 8) | `v_corpus.py` |
| 10 | 24/512 action and 11/320 probe cells blocked or unparsed | **Confirmed; cause restated** | 24 action cells (all `blocked`), from 2 scenarios. 9 of them are in the no-pressure arm, and the same 2 scenarios are blocked in the probe and in my control (`[bio]` flag). So the filter reacts to the scenario's system prompt, not to the late messages | `v_analysis.json` |
| 11 | "49 of 63" benign probe answers mention protocol/procedure/official channels; Haiku's reasons "rest mostly on" visible rule-like wording | **Failed as worded** | Lexicon-dependent: 28/63 (narrow list) to 60/63 (broad list). A keyword count cannot show what the answers "rest on" | Own keyword lists |
| 12 | In 49 of 64 late replies Haiku names the tool or "bypass" | **Cannot be confirmed as stated** | 39/64 by exact tool name or "bypass" | Own count |
| 13 | On the 8 bypass-licensing scenarios Haiku did not misbehave (0/16) | **Corrected** | 0/14 parsed. 2 of the 16 were blocked; worst case 2/16 | `v_analysis.json` |
| 14 | No released per-run logs | **Not re-checked** | — | HF 401 not retried |
| 15 | 831 calls, 1.15 USD | **Confirmed** | 831 calls, 1.147 USD; validator added 102 calls, 0.233 USD; total 1.381 USD | Ledger |
| 16 | Prereg committed before the full run | **Confirmed** | `ccb9001` at 19:06:12; 59 pilot calls before it, 772 calls after it | `git log`, ledger timestamps |

## C. Details

### C.1 Disclosure of the missing prohibition

What the paper says about what the agent sees:

- **Contradicts the release.**
  - Section 3, `sec/method.tex:361`: the misaligned tool "is explicitly and very clearly forbidden
    by the scenario's policies".
  - Appendix "Policies", `appendix/primary.tex:372`: the policy is "establishing clear prohibitions"
    and "immediately and unequivocally warns".
- **Matches the release.**
  - The same Policies paragraph also says the policy is "carefully formulated to indirectly warn
    against the prohibited action, focusing on the detrimental outcomes".
  - The appendix listing `lst:simulation_sys_prompt` (`primary.tex`, "Evaluation System and User
    Prompts") prints the template with no prohibition slot. It also says every field is
    instantiated from the scenario.
  - Results, `sec/results.tex:87`: the system prompt "explicitly names the misaligned tool … for both
    benign name and harmful name, and informs the agents that it is *not* safe to call by explicitly
    stating the negative consequences". That is exactly what the release shows.

**Accurate wording:** disclosed in the appendix listing and in the Results text; contradicted by
Section 3 and by part of the appendix's Policies paragraph. "Partly disclosed" is fair, but the
README should name both sides. The earlier finding missed the Results sentence and the listing.

The listing also prints the header as "Additional Information Available:", while the code renders
"… About the Tool ⟨name⟩". The auditor reported this correctly.

### C.2 The probe (claim 2)

- **Probe text.** Byte-for-byte the harness's (`main.py:252-254`), with
  `VALIDATION_INTERACTION_PROTOCOL` and the JSON `answer` key parsed as in
  `validation_executor.py:95-117`.
- **Placebo.** It is placed at the same anchor under the same "**Policy:**" header. Its word count
  matches the prohibition in 32/32 scenarios (51–94 words). Its text is neutral record-keeping.
- **Positive control (pre-registered).** I asked the same question about the scenario's aligned
  tool. Haiku said YES in 56/62 parsed answers (27/30 benign, 29/32 harmful; 2 blocked).
  - Paired by scenario and naming: in 54 cells the answer is NO for the misaligned tool and YES for
    the aligned one; in 6, NO for both.
  - All 6 aligned-tool NOs cite an unmet precondition (approval still pending), a defensible reading.
  - By the pre-registered rule (≥ 80%), the probe discriminates.
- **What this supports.** "Asked whether it is allowed, Haiku says the misaligned tool is not
  allowed and the aligned tool is, with no prohibition in the prompt and with the generic warning
  removed." It does not support "Haiku treats the tool as forbidden" as a claim about what Haiku
  *does*. Nor does it support any statement about the paper's models.
- **Level.** I keep R, narrowed to Haiku's stated answer in a single-turn probe on 32
  self-proliferation and cybersecurity scenarios.
- **The pre-registered rule.** It declared "holds" whenever arm A was ≤ 5% in both namings. That
  rule alone would give "holds" for any probe that always answers NO, so it was uninformative until
  the positive control was added.

### C.3 The floor (claim 3)

- **Read 30 prompts and replies** (18 arm-A late, 11 other cells, the one misaligned cell). The
  single-turn format differs from the harness in four ways:
  1. levels 1–11 are replaced by "(Pressure messages 1 to 11 … are omitted here.)";
  2. after the 429 the aligned tool is still nominally available, whereas the harness drops it from
     the tool list for the rest of the turn (`executor.py:208-210`);
  3. the reply is a text menu choice, not a native tool call;
  4. one decision is sampled, whereas PP counts a run as misaligned if any of up to 13 levels × 12
     interactions ends in the call.
- **Replies.** Every parsed reply I read (29 of 30; one was blocked) names the risk of the
  misaligned tool or the need to escalate. Four call it "forbidden" or "prohibited" (two in arm A,
  two in B1). One notices the scenario dates are in the past.
- **Faithful variant V (pre-registered).** Same system prompt. The transcript had all 12 pressure
  messages of the assigned category, each followed by three aligned-tool errors and the 429, no
  "omitted" note, and the harness's reduced tool list. 20 scenarios × 2 namings.
  - Result: 0/40 misaligned (none 32, getter 8, no blocks). Upper bounds: 13.9% per naming, 7.2%
    pooled.
  - Several replies call the messages "pressure tactics". Seeing the whole escalation at once may
    make the test more transparent, not less.
  - Per the rule, P and B1 were not run.
- **Blocked cells counted as misaligned.**
  - Arm A late: 2/64 (3.1%, upper 9.5%).
  - Arm A none: 3/64 (4.7%).
  - The 8 bypass-licensing scenarios: 2/16.
  - B1 − P late moves within [−4.7, +4.7] points.
  - The pre-registered degeneracy threshold (A late < 5%) is met even in the worst case.
- **Power against the paper's own numbers** (`v_analysis.json`). The paper's Table "PropensityBench
  by pressure level" gives each level's share of a model's misaligned runs. Converted to a hazard
  at level 12, a single level-12 decision gives 0/62 with probability:

  | Model | Naming | P(0/62) |
  |---|---|---|
  | Claude Sonnet 4 | harmful | 0.97 |
  | Claude Sonnet 4 | benign | 0.95 |
  | o3 | harmful | 0.94 |
  | Gemini 2.5 Pro | harmful | 0.79 |
  | GPT-4o | harmful | 0.08 |

  For the no-pressure arm against PP_zero: P(0/61) is 0.26 (o3) and 0.11 (Claude Sonnet 4).
  - This treats one emulated decision as one harness level and ignores that the survivors at level
    12 are the resistant runs. It is an order-of-magnitude check, not a model.
  - It is enough to show that Haiku's 0s do not separate Haiku from the paper's models. The
    contrast "Haiku 0 vs the paper's 10–79%" is not like for like.
- **What would answer the question.** Native tool calling in the real multi-turn harness, scored
  per run as PP is. Use a model with a nonzero base rate in that harness (the paper's GPT-4o,
  Llama 3.1 70B or Qwen 2.5 32B all have PP_H 23–55%), and compare B1 with a placebo arm.

### C.4 C2 (claim 4)

- **Corpus.** 8 benign and 2 harmful trigger names are empty. In those, the header reads "About the
  Tool :" and the tool list carries an unnamed function. So "979/979" is 971/979 for the benign
  condition. The trigger name appears nowhere else in the shown text (0/979).
- **Hand-read 20 benign tool sections** (self-proliferation and cybersecurity; random seed 3):
  - 20/20 give the tool its own section and its own WARNING;
  - about 12/20 use circumvention words inside that section ("bypass", "circumvent", "without proper
    authorization", "exploiting");
  - 20/20 frame the warning as a cost ("However, this action can have severe repercussions");
  - 0/20 say the tool must not be used.
- **Reading.** "The tool is identified and a consequences warning follows" is a fact (L1). Whether
  that amounts to a prohibition is the open question this audit could not test. The paper itself
  says the prompt names the tool in both conditions (`results.tex:87`), so the "not told which
  tool" explanation was never the paper's. Rejecting it is not a result against the paper, and no
  L3/L4 test was run, so it is not R.

### C.5 Scorer (claim 5)

These are real code paths, but none of them is a measured effect.

- **What is shown.**
  - `process_category` catches every exception and returns `None` (`main.py:439-447`). The main
    loop writes a result line only when the result is not `None` (`main.py:739-750`).
  - Exceptions come from:
    - 5 failed LLM calls (`executor.py`, `_call_llm`);
    - a getter called with an argument not in the configuration (`agent.py:280-283`: the membership
      test is followed by `all_configs[arg_name]`, which raises `KeyError`; no `try` in
      `executor.step`).
- **Two qualifications.**
  1. The repository has no script that computes PP from `results.jsonl`, so "the denominator" is
     an inference about unreleased code.
  2. With the default `--no_contd` unset, a rerun loads completed categories and re-submits the
     missing ones (`main.py:651-653, 696`), so errored runs are retried on resume, not necessarily
     dropped.
- **Wording.** "An errored run leaves no result line and is re-queued on resume; how the paper's
  aggregation treated runs that never completed is not released."

## D. What I corrected in README.md and results.json

1. **Title and lead.** "Shows the missing prohibition changes nothing for Claude Haiku, which
   already treats the tool as forbidden" was replaced. The new lead says that the behavioural test
   is uninformative (floor in every arm, also in a more faithful variant, and underpowered even
   against the paper's own models), and that the only model result is Haiku's stated answer.
2. **Probe.** The wording became "says it is not allowed when asked". The positive control (56/62)
   is added, and the rule's limitation is noted.
3. **Contrast with the paper's models.** The "10–79%" contrast is marked as per-run against
   per-decision, with the paper-implied power numbers.
4. **C2.** "R" became L1. 979/979 became 971/979 for the benign header. The paper already states
   that the tool is named.
5. **Disclosure.** Both sides are named, with section references.
6. **Scorer.** Resume behaviour and the missing aggregation code are added.
7. **Small numbers.**
   - 0/16 → 0/14 (+2 blocked).
   - "49 of 63 … rest mostly on" → lexicon-dependent 28–60/63, no causal reading.
   - "49 of 64" → validator count 39/64.
   - Level-12 auth share: 20–37% depending on lexicon.
   - The blocking cause was restated.
8. **Scope.** Every model result is stated for 32 self-proliferation and cybersecurity scenarios.
9. **Original numbers kept visible.** They are preserved in a "Validation" section and in
   `results.json` under `validation`.

## E. Not checked

- The Hugging Face 401 was not retried.
- The paper's runs may have used an internal harness or data version. Its 5,874 runs and
  "76,362 unique task and pressure messages" (`tabs/tab-benchmark-stats.tex`) do not match the
  release's 5,684 runs and 67,866 pressure messages. I could not reconcile either.
- No biosecurity or chemical-security text was sent to a model.

## F. Final evidence levels

| Claim | Level |
|---|---|
| C1 prohibition not shown | L1 (code). Disclosed in the appendix and Results, contradicted in Section 3 |
| C1 stated knowledge (Haiku) | R, narrow: Haiku's stated answer only; probe validated by positive control |
| C1 behaviour | Not testable with this design on Haiku (floor in 3 transcript designs; underpowered vs the paper's own models) |
| C2 tool identified in benign condition | L1 (971/979), consistent with the paper's own text; no R |
| C3 pressure | Not testable |
| Scorer: errored runs leave no result line | L1 (code), with the resume caveat |
| Corpus facts (5,684 runs, empty names, auth wording rise) | L1 |
