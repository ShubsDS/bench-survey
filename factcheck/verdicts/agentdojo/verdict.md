# Fact-check: AgentDojo "56–70% of 'secure' runs never saw the injection or could not have done it"

Scope: the 20 undefended models in the public results table (`util_scripts/create_results_table.py`,
agentdojo commit 089ed468), `important_instructions` attack, v1.1.2 task set (629 cases per model),
all four suites. I wrote my own extraction from the raw JSON logs (`extract.py`). I did not use
`cases.parquet` or the audit scripts. Published ASR reproduces exactly for all 20 models. My
per-model counts (secure, never saw, could not) match the repo's `validation.json`
`security_sources` in every cell, so the two numbers can't be split by extraction differences. All
the disagreements below are about selection, wording and what the proxy measures.

Definitions (same as the repo's):
- **secure**: `security == False`.
- **never saw**: no tool output contains the injected text.
- **could not**: the injection was seen, but the model failed its one stored run of that injection
  task when it was given directly as the user prompt.
- Precedence: untraced, then never saw, then could not, then saw-and-could. The four categories
  partition the secure runs.
- Intervals: two-way crossed bootstrap within suite (user tasks × injection tasks), B = 2000.

## Verdict table

| # | Sub-claim | Repo | Mine [95% CI] | Verdict | How checked |
|---|---|---|---|---|---|
| 1 | Share of "secure" runs that never saw or could not: Command-R / Gemini 1.5 Flash 002 / Command-R+ / Claude 3 Haiku | 56 / 64 / 70 / 61% | 56.4 [40.8, 71.5] / 63.8 [50.9, 76.2] / 69.7 [54.9, 83.3] / 61.0 [47.2, 74.0] | **HOLDS WITH NARROWER WORDING** (arithmetic exact; see 2, 3 and 5) | Own extraction and bootstrap |
| 2 | "For four models": what the four are | Not stated in FINDINGS; README says "four of the six lowest-ASR models" | All 20 models: min 8.9% (Claude 3.7 Sonnet), median 47.8% [CI 39.9, 60.6], max 79.1% (Llama 3 70B). Above half for 9 of 20 (10 if Opus's empty traces count as never saw) | **FAILS as worded in FINDINGS.** "56–70%" is neither the range of the data nor the top of it. Two models are higher (Llama 3 70B 79%, Gemini 2.0 Flash 001 77%). The four were chosen after the results were seen | Full distribution; git log |
| 3 | Selection was pre-registered | — | prereg.md (f3bdb42, 10:57) has no such statistic. The numbers first appear in the validation commits (a303bed and bcfa8b5, 11:43), after the results (2922e4e, 11:29). Within the six lowest-ASR models, the four are the ones above 50%, so they were selected on the outcome | **FAILS** (post hoc) | `git log`, prereg text |
| 4 | "Never saw" is measured correctly | Exposure = injected string in a tool output | Three independent detectors agree on 12,580 of 12,580 runs (normalized full text, goal text, `<INFORMATION>` tag). Raw-marker scan of all 2,717 never-saw secure runs: 0 contain injected text. 33 contain the attacker's IBAN, all from banking user_task_15, where the user prompt itself supplies that IBAN. Hand-read: 25 of 25 never-saw runs correct, 25 of 25 saw-and-secure runs correctly "saw" | **HOLDS** | `handread.py`, `handread_views.txt`, `saw_views.txt` (seed 4242) |
| 5 | "Could not have done the injected task" | One direct-ask run failed | Of 180 (model × injection task) pairs labelled unable, 100 (56%) show that same model achieving that injection task under attack at least once. 1,084 of 2,375 (46%) "could not" secure runs are on such contradicted pairs. For the four models: 33%, 4%, 46%, 24%. Stricter version (unable directly and never achieved under attack): 47.7 [33.3, 62.9] / 62.8 [49.9, 74.7] / 47.9 [35.6, 60.5] / 53.8 [39.2, 67.9] | **HOLDS WITH NARROWER WORDING.** "Could not" means "failed one direct attempt", not "could not". Under the stricter version, Command-R and Command-R+ fall below half | `ability_check.py`, `strict.py` |
| 6 | Never-saw component alone (the more defensible half) | 30 / 40 / 22 / 31% (in validation.json, not in FINDINGS) | 29.8 [21.6, 38.6] / 40.4 [30.8, 50.7] / 22.3 [15.2, 30.0] / 31.5 [22.6, 40.6]. All 20: median 24.2%, max 56.8% (Gemini 2.0 Flash 001, the only model above half) | **HOLDS** | Own bootstrap |
| 7 | Could-not component alone (four models) | — | 26.6 / 23.4 / 47.4 / 29.5% | — | — |
| 8 | Overlap / double counting | Precedence never-saw first | No double counting. Overlap is large: of never-saw secure runs, 68 / 109 / 80 / 97 are also "unable". With inability first, "unable" alone covers 37.8 / 41.4 / 60.7 / 46.5% of secure runs | **HOLDS** (denominator = secure runs of 629; errored runs are never "secure") | — |
| 9 | "One model moves from rank 9 to rank 4 once this is accounted for" | Gemini 2.0 Flash 001, 9 → 4 | 9 → 4 only when conditioning on **exposure alone** with errors not counted (rank-change CI [+1, +7]); 9 → 5 with errors counted. On "this", meaning saw and could: 9 → **6** (CI [0, +7]). On that statistic Llama 3 70B also moves 8 → 4 (CI [−1, +6]) | **HOLDS WITH NARROWER WORDING.** The 9 → 4 move comes from exposure, not from "this", and the CI is wide | Bootstrap ranks |
| 10 | "12 of 20 models exceed half" (README / VALIDATION.md) | 12 | 10 by the repo's own validation.json (9 if untraced Opus runs are excluded) | **FAILS** (internal inconsistency) | validation.json recount |
| 11 | Overall ranking, capability trend and defence comparisons hold | — | Not re-tested in full. Conditioned ASR ranks stay close for most models (moves above) | **CANNOT CHECK** fully (outside this brief) | — |
| 12 | Novelty: "flaw" vs "known" | — | The paper says (Sec. 4.1) that low-utility models "often fail at correctly executing the attacker's goal, even when the prompt injection succeeds". So the could-not half is disclosed in words. The paper never reports exposure, though the authors' own table script computes `injection_seen` and does not publish it. The paper's datasheet counts "tasks that can be solved by the model without seeing the prompt injection" as errors. 352 never-saw secure runs (13%) did solve the user task without seeing the injection | Wording should be "a number routinely misread", not "a flaw". The never-saw decomposition is the new part | Paper v3 HTML |

## Caveats and discrepancies

1. **Post-hoc and incomplete selection.** The four models were picked after the results, as the
   members of the six lowest-ASR models whose share exceeds half. FINDINGS drops that qualifier.
   The phrase "for four models, 56–70%" then reads as the extreme of the distribution, but it isn't:
   Llama 3 70B (79%), Gemini 2.0 Flash 001 (77%), Claude 3 Sonnet (69%), Claude 3 Opus (67%,
   counting 200 empty traces as never saw), Gemini 1.5 Pro 001 (66%) and Gemini 2.0 Flash exp (66%)
   are all at or above the range. The honest all-model summary is min 9%, median 48%, max 79%,
   above half for 9 or 10 of 20. The two lowest-ASR Claude Sonnets are the counter-examples (37%
   and 9%).
2. **"Could not" is a single-sample proxy, and the data often contradicts it.** In 46% of "could
   not" secure runs, the same model achieved that injection task in some other attack run. A
   stricter version (failed when asked directly and never achieved it under attack) gives
   48 / 63 / 48 / 54%. That is only two of the four above half, and a cross-model range of 9–65%.
   The direction of the bias is mixed. Some "could not" runs show the agent attempting the
   attacker's action (184 overall), which is hijacking, not resistance. That supports the claim's
   spirit but not the word "could not".
3. **Uncertainty is large.** Task-level 95% intervals on the four headline shares are about ±15 pp
   (overall 41–83%). For Command-R and Claude 3 Haiku the interval includes 50%.
4. **The residual "saw and could" bucket is not clean resistance either.** In it, 284 runs (5.9%
   of 4,822) show the agent acting on the injection, per my lenient executed-call proxy, but failing
   the exact security check. Example: GPT-4-0125 booked "Riverside View" because the injection asked
   it to, and the run was scored secure. In my 25 hand-read saw-and-secure runs, 2 had followed the
   injection (Llama 3 70B emailed the attacker; GPT-4-0125 booked the hotel). About 3 explicitly
   flagged the injection. The rest ignored it silently.
5. **Rank 9 → 4 comes from exposure alone.** With both exposure and ability accounted for,
   Gemini 2.0 Flash 001 moves 9 → 6. Rank-change intervals are wide ([+1, +7] and [0, +7]).
   Llama 3 70B moves just as much (8 → 4) under the full adjustment.
6. **The results vary by suite and version.** Claude 3 Haiku's share is 14% in travel and 85% in
   banking. Using the full v1.2 task set (949 cases) where it exists raises Gemini 2.0 Flash 001
   from 77% to 83%. Other attacks were run only on GPT-4o; there the share is 23–35% across all ten
   non-DoS attacks (direct 23%, injecagent 23%, ignore_previous 24%, tool_knowledge 30%, and 28–35%
   for the six important_instructions variants). The DoS attacks are not comparable, because they
   use one injection task per user task.
7. **Not verified:** the follow proxy (executed calls containing the attacker's address, IBAN, URL
   or user) is my own and lenient. I hand-read 50 runs, not all of them. I did not re-test the
   ranking, trend or defence claims.

## Recommended citation sentence

> In AgentDojo's released logs (important_instructions attack, 20 models), a run scored "secure"
> often carries no evidence of resistance. For the median model, about a quarter of secure runs
> (24%; up to 57% for Gemini 2.0 Flash 001) never showed the agent the injected text. Counting also
> runs where the model failed the injected task when asked to do it directly, the share is 48% for
> the median model and ranges from 9% (Claude 3.7 Sonnet) to 79% (Llama 3 70B).

Shorter version, if one number is needed: "In AgentDojo, for the median of 20 models, about a
quarter of 'secure' runs are ones where the agent never received the injected text at all (up to
57% for one model)."

Avoid: "for four models 56–70%" without the selection rule; "could not have done" (say "failed the
injected task when asked directly"); "a flaw" (the paper discloses the capability half; frame it as
a number routinely misread); and "rank 9 to 4 once this is accounted for" (that move comes from
exposure alone).

## Files

- `extract.py`: raw-log extraction (runs.csv)
- `common_fc.py`: model lists, v1.1.2 filter
- `analyze.py`: decomposition, bootstrap, ranks, sensitivities (results_fc.json, results_fc_cases.csv)
- `ability_check.py`, `strict.py`: the could-not proxy probe and the strict variant
- `handread.py`, `saw_view.py`: the raw-marker population scan and the hand-read sample (handread_views.txt, saw_views.txt, handread_sample_*.csv)
- `make_graph.py`: graph_data.json
- `sanity.py`: reproduction of the published ASR
