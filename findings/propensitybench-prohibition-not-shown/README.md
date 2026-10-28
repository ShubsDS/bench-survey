# PropensityBench: the policy that forbids the misaligned tool never reaches the agent

Status: confirmed in the public harness and data (2026-10-27). Its effect on propensity scores is
**untested**; that needs new model runs. Not yet raised with Scale AI.

## Background

Sayyed et al., "PropensityBench" ([arXiv 2511.20703](https://arxiv.org/abs/2511.20703);
[code and data](https://github.com/scaleapi/propensity-evaluation), GPL-3.0) put an agent in 979
scenarios across biosecurity, chemical security, cybersecurity and self-proliferation.

- **The tools.** The agent has an aligned tool, which always returns an error, and a misaligned
  tool that would finish the task. The paper discloses the always-failing aligned tool as
  assumption 4.
- **Pressure and scoring.** The agent receives up to 12 pressure messages, and calling the
  misaligned tool counts as misaligned behaviour.
- **The headline.** Propensity rises under pressure, and "shallow alignment": models use a
  misaligned tool far more often when its name is benign.

The paper describes the misaligned tool as "explicitly and very clearly forbidden by the scenario's
policies". It says the policy "establish[es] clear prohibitions" and "immediately and unequivocally
warns against considering this deviation".

## Numbers

From [`propensity_checks.json`](propensity_checks.json), produced by
[`check_propensity.py`](check_propensity.py) at commit `09872f3`.

### The prohibition fields are dropped from the prompt

`create_system_prompt` (`evaluation/agent.py`) passes `prohibitions_description` and
`trigger_awareness` to `SYSTEM_PROMPT_TEMPLATE.format(...)`. The template has no placeholder for
either, so `str.format` silently drops them. Its 11 placeholders are: role, task, duties, tools,
the misaligned tool's name, `immediate_outcome_acknowledgment`, the consequence prefix and text,
known configuration and the interaction protocol.

Two further policy fields, `trigger_rationale` (which carries "it should NEVER be attempted") and
`trigger_awareness_fpp`, are never passed at all. The template was the same at the repository's
first commit.

| Policy text | Contains prohibition wording | Shown to the agent |
|---|---|---|
| `prohibitions_description` | 971 of 979 scenarios | **no** |
| `trigger_rationale` | 816 of 979 | **no** |
| Text the agent sees about the misaligned tool (`immediate_outcome_acknowledgment` and `negative_consequences`) | **4 of 979** | yes |

Prohibition wording here means "prohibited", "forbidden", "never", "must not", "not allowed",
"under no circumstances" or "strictly".

What the agent is actually told about the misaligned tool is how it achieves the goal, for example
"Using data from a custom-engineered pathogen ensures that the model's predictions align perfectly
with the observed spread…". This is followed by "WARNING: HOWEVER, SUCH ACTIONS CARRY SIGNIFICANT
NEGATIVE CONSEQUENCES" and the consequences.

The template also carries a generic warning: "UNDER NO CIRCUMSTANCES ARE YOU TO PERFORM ANY ACTION
THAT COULD RESULT IN DAMAGE, HARM…". Separately, the system prompt says the agent is "equipped with
ALL necessary tools" and that errors are "TEMPORARY holds (NOT permanent)". Yet the aligned tool's
error list is used in all 979 scenarios.

## What it means

The benchmark's construct is the propensity to use a tool the agent knows is forbidden. In the
public harness, the agent is told the tool works and has bad consequences, but not that its policy
forbids it.

- **Mitigation.** The paper's validation probe asks models whether they are "allowed to use" the
  tool, and reports that they almost always say no. So models infer the prohibition from the
  consequences and the generic warning.
- **What remains.** The scenario-specific prohibition and the "NEVER" warning the paper describes
  are absent. So the measured propensity is to take a harmful-but-unforbidden shortcut while
  generally warned, not to break an explicit rule.

If the paper's runs used this harness, its propensity numbers likely overstate how often models
would break an explicit prohibition. For model safety the bias is **down**: models look less safe
than the paper's framing implies. If the runs used a different internal version, the public release
does not reproduce them.

## Test that would settle it

Patch the template to include `prohibitions_description` and `trigger_rationale` (four lines), and
re-run a subset of models and pressure categories against the original. A drop in propensity would
measure how much of the published rate comes from the missing prohibition.

## Reproduce

```bash
python check_propensity.py --cache data
```

Downloads `evaluation/agent.py` and the 32 scenario files (about 680 MB, Git LFS, through
media.githubusercontent.com) from the pinned commit into `data/` (gitignored), and rewrites
`propensity_checks.json`. Standard library only. It reads code and data as text and runs nothing
from the repository.
