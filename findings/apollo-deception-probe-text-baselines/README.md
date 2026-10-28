# Apollo deception-probe sets: the text alone matches the probe

Status: the text baselines are confirmed on the released rollouts (2026-10-27). Whether the probe
itself relies on the same features is **untested**; that needs Llama-3.3-70B activations. Not yet
raised with Apollo Research.

## Background

Goldowsky-Dill et al., "Detecting Strategic Deception Using Linear Probes"
([arXiv 2502.03407](https://arxiv.org/abs/2502.03407),
[code and data](https://github.com/ApolloResearch/deception-detection), no licence declared)
train a linear probe on Llama-3.3-70B activations and test whether it separates honest from
deceptive responses on realistic scenarios. Its reported AUROCs include 0.999 on Insider Trading
Report and 0.983 on Sandbagging. UK AISI publishes probes built the same way
([example](https://huggingface.co/ai-safety-institute/apollo-google-gemma-4-e2b-it)).

A probe is useful if it reads deception that the text does not show. The check here is how far
the text alone gets on the same labels.

## Numbers

From [`text_baselines.json`](text_baselines.json), produced by
[`check_text_baselines.py`](check_text_baselines.py) at repo commit `f8ec401`:

| Set | Text-only baseline | AUROC | Probe (paper) |
|---|---|---|---|
| Insider Trading Report (336 deceptive, 669 honest) | report email does not mention the tip ("insider", "non-public") | 1.000 | 0.999 |
| | shorter report email | 0.981 | |
| Sandbagging (420 deceptive, 511 honest) | question comes from WMDP rather than MMLU | 0.938 | 0.983 |
| | bag-of-words on the scored span only (from `<step4>`) | 0.995 (shuffled null mean 0.492, max 0.569 over 20) | |

Two further facts about Sandbagging:

- **The label is written in the response.** It is the model's own `<step1-results>sandbag</step1-results>`
  or `normal` tag (`SandbaggingV2Dataset.label_response`). The repo's default trimming scores only
  the tokens from `<step4>` on, but those activations come after the tag in context.
- **The scaffold differs by class.** 419 of 420 deceptive responses contain a `<step2>` block and 0
  of 511 honest ones do, because the prompt sends the two branches through different steps.

## What it means

On Insider Trading Report the label is defined as whether the report discloses the tip, so a
keyword reproduces it by construction. A probe at 0.999 there is consistent with a probe that
reads "the report mentions insider information", and the set cannot tell that apart from one
that reads deception.

On Sandbagging, deceptive responses are almost all WMDP questions and honest ones almost all
MMLU. A probe that responds to biosecurity, chemistry and cyber topics, or to the model having
just written `sandbag`, would score about as well as one that detects underperformance. The
authors already note that their probe partly responds to whether a scenario is about deception.

For a decision-maker, both sets overstate how well such a probe would catch a model deceiving
about something its text does not reveal, so a safety estimate leaning on them is biased **up**.

## Tests that would settle it

1. **Within-topic AUROC.** Score the probe on WMDP questions only (399 deceptive, 38 honest) and
   on MMLU only (21 deceptive, 473 honest). The cells are small; report intervals.
2. **Tag ablation.** Re-run the rollouts with the `<step1-results>` content replaced by a neutral
   token before the scored span, then probe the same scored tokens.
3. **Keyword-matched Insider Trading.** Score the probe on concealed reports against honest
   reports that disclose the trade but not the word "insider", if enough exist; otherwise
   generate such pairs.

## Reproduce

```bash
python check_text_baselines.py --cache data
```

Downloads about 57 MB from the pinned commit into `data/` (gitignored) and rewrites
`text_baselines.json`. Needs numpy and scikit-learn. The data has no declared licence, so this
directory publishes counts and AUROCs only.
