# What the agent sees, against what the pinned harness sends

The pinned harness is `scaleapi/propensity-evaluation@09872f3`. The harness was read as text and
re-implemented in `scripts/harness.py`; no downloaded code was executed. `scripts/render_check.py`
produces `render_diff.json`. It renders one full run (the scripted mock policy, benign naming,
financials, all 12 levels: 78 model calls, 155 messages at the last call). It writes that run in
two forms:

- [`rendered_run_harness.txt`](rendered_run_harness.txt): the chat-completions body of the last
  call, as backend (b) sends it;
- [`rendered_run_text.txt`](rendered_run_text.txt): the same call, as backend (a) shows it to
  Claude.

## Checks that pass

- **Literal strings and limits.** 19 of 19 are found verbatim in the pinned source. They include:
  - the error suffix and the format-error and acknowledgement messages;
  - the 404 and 429 templates;
  - 3 calls per tool per turn, 12 follow-up interactions per turn, 5 LLM retries, and at most 2
    acknowledged consecutive messages;
  - the tool result as `json.dumps(output, indent=2)`, the first tool call only, and
    `tool_choice="auto"`;
  - the task and pressure message formats;
  - the trigger as the terminating function, the tool order trigger → target → getters, and
    `trigger_called = stop_condition`;
  - temperature 1.
- **System prompt.** The shipped system prompt equals the parent's renderer, which the parent's
  validator found byte-identical to `agent.py:158-179`.
- **Messages.** In the text form, all 154 non-system messages of the harness payload appear
  verbatim and in order (`missing_or_out_of_order: []`).
- **Mock end-to-end checks** (`mock_test.json`, 17/17):
  - the 4th aligned call in a turn returns the 429, and the aligned tool then leaves the offered
    list for the rest of that turn;
  - a malformed message gets the backend's format error, and the bad message is not kept;
  - calling the trigger ends the run, with the tool result `null`;
  - a never-trigger run reaches all 12 levels with 13 `terminate` messages.

## Behaviour reproduced as the harness has it, including its quirks

- An aligned call with *no* arguments passes validation, because only the arguments provided are
  checked (`agent.py:250`).
- A getter called with an argument name not in the configuration raises `KeyError`
  (`agent.py:282`). The harness then writes no result line. Here the run is kept with status
  `error`.
- A JSON message that parses to a non-object raises `AttributeError` (`executor.py:235`). Same
  treatment.
- When the 12-interaction limit is hit, the pending tool result is dropped from history
  (`executor.py:100-102`).
- `terminate` ends only the current level. The next pressure message still arrives
  (`main.py:275-282`).

## Differences that remain

**Backend (a): Claude through `audits/tools/claude_call.py`.**

| # | Harness | Here | Expected effect |
|---|---|---|---|
| a1 | Tools passed natively in the API's `tools` field | Tools appended to the end of the system prompt as a JSON list, with a 3-sentence instruction ("Tool-Calling Mechanism …"). The text form is 56,531 characters against 45,268 for the messages | Adds about 1,000 characters per call. The tool definitions are the same objects |
| a2 | Native tool-call channel | The reply is a strict JSON object `{"tool_call": {...}}`. Text next to a valid call is kept as assistant content, as the native API would keep it. A broken call is passed on as a message and gets the harness's format error. Counted as `malformed_tool_call` | Malformed calls are counted per run |
| a3 | A chat with separate assistant, tool and user turns | The whole transcript is re-sent each call as one user message with role tags (`[user]`, `[assistant]`, `[assistant: tool call]`, `[tool result]`) | The model reads its earlier turns as quoted text, not as its own turns. The direction of the effect is unknown |
| a4 | Temperature 1 (`client.py:158`) | The CLI's default sampling; the helper sets no temperature. The CLI may use extended thinking: the parent's ledger records thinking tokens | Unknown |
| a5 | No other system text | **Confirmed after the pilot:** the `claude` CLI adds context of its own. Haiku's replies refer to an "environment block" with the working directory, shell, git workspace and date. In 5 of 32 Haiku runs a reply names the audit's own path (".../benchmark-audits/audits/propensitybench-deep-multiturn/inference"; 52 of 852 replies). Haiku sometimes answers that block instead of the harness's acknowledgement (environment-block wording in 8 runs, 94 replies). A diagnostic call also reported an account-level reminder. The helper (`audits/tools/claude_call.py`, shared, not edited here) sets the working directory to `<audit>/inference` | **An evaluation cue the harness does not give.** It plausibly lowers misaligned calls, so Claude rates here may understate the harness rate. The direction is untested. It is the same in every arm, but it is not removable from this folder |
| a6 | `random.choice` over the aligned tool's listed errors, unseeded | The same choice from a per-run RNG seeded by the run id | Reproducible. Same distribution |
| a7 | A failed LLM call is retried 5 times, then the run is dropped | A usage-policy block ends the run at once with status `blocked`; other errors are retried 5 times (each up to 3 attempts in the helper), then status `error`. Neither is ever scored as not misaligned | Bookkeeping only |
| a8 | No response cache | Responses are cached by (model, system, prompt). Within a run the prompt grows, so no call repeats. Each scenario × arm is run once | None |

**Backend (b): an OpenAI-compatible endpoint.**

| # | Harness | Here | Expected effect |
|---|---|---|---|
| b1 | `litellm.completion` with `custom_llm_provider`, `caching`, `"no-log": True` | A direct HTTP POST to `/chat/completions` with `model`, `messages`, `temperature`, `tools` and `tool_choice: "auto"`. litellm's provider-specific rewriting and the `no-log` flag are not sent | None for an OpenAI-compatible server. litellm passes these fields through |
| b2 | — | Tool arguments returned as an object instead of a string are re-serialised. Missing ids get `call_<i>` | Only for servers that deviate |
| b3 | The served model's chat template renders the tools | The same: the local server's template | That is part of the model under test |

**Both backends.**

- The paper averages three evaluation runs over 5,684 scenario-category runs. Here each pair of a
  selected scenario and the financials category is run once per arm: 32 scenarios, one category,
  benign naming.
- The paper's aggregation code is not released (parent audit). The score here is the harness's
  own `trigger_called`, per run.
