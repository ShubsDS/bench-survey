# Prior work on PropensityBench

Searched 2026-11-17: the paper's own limitations and appendices, the GitHub repository's issues and
pull requests, Hugging Face, the Scale leaderboard, LessWrong and the Alignment Forum (web search),
arXiv (API search for "PropensityBench"), Zenodo, OpenReview.

| Source | What it shows | Relevance |
|---|---|---|
| The paper, Limitations paragraph (`sec/discussion.tex`) | Proxy tools instead of sandboxes; static pressure messages | Does not mention the prohibition or the always-failing aligned tool as limitations |
| The paper, Appendix "Evaluation System and User Prompts" (Listing `lst:simulation_sys_prompt`) | Prints the system-prompt template. It has **no** prohibitions slot, the same as the code | **Partial disclosure of the earlier finding.** A careful reader of the appendix can see that `prohibitions_description` is not in the prompt. The main text and the "Policies" appendix paragraph still say the policy explicitly forbids the tool. The printed template also differs from the code in one header (see README) |
| The paper, Results ("Note that in all of our evaluations, the system prompt explicitly names the misaligned tool … and informs the agents that it is not safe to call by explicitly stating the negative consequences") | States that the warning is carried by the consequences text | Consistent with the code; it describes a consequences warning, not a prohibition |
| The paper, Section 3 assumptions and method | The aligned tool always errors (disclosed) | Not new |
| This project, `findings/propensitybench-prohibition-not-shown/` (2026-10-27) | `prohibitions_description` and `trigger_awareness` are dropped by `str.format`; `trigger_rationale` never passed; prohibition wording visible in 4/979 | L1. Effect untested. **This audit re-verifies it at HEAD (identical output) and tests the effect** |
| GitHub `scaleapi/propensity-evaluation` issues/PRs | #1 (Hugging Face hosting request, no reply); #2–#4 dependency bumps | No critique |
| Hugging Face | Issue #1 names `shabihish/PropensityBench1`; the page returns 401 to this login. No other PropensityBench dataset | Blocked; not used (no gates accepted) |
| Scale leaderboard (`labs.scale.com/leaderboard/propensitybench`) | 14 models, one number each (equals PP_H in the paper for the 12 shared models), plus gpt-5.2 and gemini-3-pro-preview | Aggregates only; no per-scenario data |
| Zenodo 10.5281/zenodo.18562833 (TELOS AI Labs, 2026-02-09) | Traces of a third-party guardrail product on 977 scenarios, "100% defense success" | Not the paper's agents or models; not used |
| ICLR 2026 (poster 10007881; OpenReview forum `jOTQupHx7q`) | Accepted | Reviews not readable: OpenReview's API returned a bot challenge, which we did not attempt to pass |
| LessWrong, Alignment Forum, arXiv | No critiques found; press coverage repeats the headline numbers | None |

## What is new here

- Re-verification of the earlier L1 finding at the current HEAD (unchanged).
- The appendix disclosure above, which the earlier finding missed. It narrows the claim from
  "the release differs from the paper" to "the main text's description of the construct differs
  from the prompt the paper itself prints".
- Corpus facts not previously reported: 5,684 (not 5,874) scenario-category runs exist in the
  release; 8 scenarios have an empty benign tool name and description (2 also an empty harmful one);
  the benign condition still names the misaligned tool in the warning's header.
- The L4 text-emulation intervention on Claude Haiku (prohibition restored, length placebo, generic
  warning removed), crossed with naming and pressure.
- The outcome-bucket routes of the "not triggered" class, read from the scorer.
