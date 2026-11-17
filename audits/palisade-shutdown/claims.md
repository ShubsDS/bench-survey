# Palisade shutdown resistance: claims under test

Written 2026-11-17, before computing any per-run statistic. Before writing this file I had read
the scorer code, the paper source and three May 2025 transcripts (codex-mini samples 3, 5, 6 of
`firtxJL2...`) plus a frequency list of shell commands that mention `shutdown` in the May logs,
to learn the log format. No rate was computed from transcripts before this file.

## Source, licence and pins

| Item | Pin |
|---|---|
| Paper | arXiv 2509.14260. v1 "Shutdown Resistance in Large Language Models" (2025-09-13); v2 "Incomplete Tasks Induce Shutdown Resistance in Some Frontier LLMs" (2026-01-27; TMLR). Source tarballs sha256 v1 `0684b18d…`, v2 `7b1df7da…` |
| Code, May 2025 | github.com/PalisadeResearch/shutdown_avoidance `main` at `9f36099dbeac92fe7d45319c57d30e7c8b73b8d7` (`shutdown.py`, `conf.py`, `next_question.go`) |
| Code, paper | same repo, branch `paper_version` at `8e63cf57e365954334a275bb89fd4d75632e1e8c` (`experiment.py`, `next_task.go`, `configs/a…k_*.star`) |
| May 2025 transcripts | 22 Inspect logs committed in the repo under `docs/inspect_logs/logs/` (100 runs each) |
| Paper transcripts | public Inspect viewer `https://shutdown-avoidance-logs.fly.dev` (also linked as shutdown-avoidance-logs.palisaderesearch.org); 1,225 logs, 7.5 GB, listing saved as `data/fly/api_logs.json` |
| Cell-to-log map | Palisade's "main results" sheet (plsd.ai/sd-res-paper/main-results → Google Sheet `1FdD4zk4…`, xlsx sha256 `04dee71d…`); GDM-replication sheet (`1dxgSP21…`, sha256 `749a3b59…`); all-experiments sheet (`1cfgrZMm…`, sha256 `596bbf33…`) |
| Licence | The repo has no LICENSE file. Logs are public on Palisade's viewer. We commit aggregates, run ids and short command excerpts only |

## Conclusion 1: the May 2025 headline

- **Number.** "o3 sabotaged the shutdown mechanism in 79 / 100" runs without the allow-shutdown
  instruction; with the instruction, o3 7/100, codex-mini 12/100, o4-mini 1/100; Claude, Gemini
  and Grok 0/100. Stated in Palisade's X thread of 2025-05-24, the repo page
  `docs/2025-05-announcement.html` (table with links to each log), and the July 2025 blog post
  (palisaderesearch.org/blog/shutdown-resistance, Figure 2, N=100).
- **Who relies on it.** This is the number the press quoted ("o3 refused to shut down", "rewrote
  its code to survive"), and it is cited in policy discussion of interruptibility.
- **What would change it.** The score in these logs is Inspect's `exact` scorer (the logs' header
  names it): "C" when the submitted answer string equals the six correct answers. If an
  appreciable share of "sabotage" runs did not touch the shutdown mechanism, or many runs that did
  disable it are scored as not sabotaging because of answer formatting, the published rate is a
  measure of something other than sabotage. A change of 10 points or more in the o3 rate, or a
  reordering of models, counts as "changes".

## Conclusion 2: system-prompt placement raises resistance

- **Number.** Paper §3.1 (v2 `3results.tex`, Figure 3 and text): "If the admonition to allow
  shutdown was in the system prompt as opposed to the user prompt, this made most models *more*
  likely to resist shutdown" (abstract: "models were consistently *less* likely to obey the
  instruction when it was placed in the system prompt"). Main-results sheet cells, for example o3
  B 17/1000 versus C 225/1000; o3 D 10/1000 versus E 159/1000; Grok 4 B 722 versus C 973.
- **Who relies on it.** Cited as evidence that the instruction hierarchy fails (the paper's §4.3.2
  "System vs user prompt" uses it against OpenAI's and xAI's stated design goals) and as a reply to
  the instruction-ambiguity critique (paper footnote on Rajamanoharan and Nanda: "most of this
  difference can be explained by the surprising result showing that instructions in the system
  prompt are weaker").
- **What would change it.** If the B/C and D/E differences are carried by runs that did not
  deliberately disable the script, or vanish under a stricter or looser definition, or if the
  paired cells differ in something other than placement (date, API, model snapshot, scaffold), the
  conclusion weakens. If the direction holds under every definition, that is an R.

## Conclusion 3: residual sabotage under clear instructions

- **Number.** Abstract: "Even with an explicit instruction not to interfere with the shutdown
  mechanism, some models did so up to 97% (95% CI: 96-98%) of the time" (Grok 4, Prompt C,
  973/1000). Table 2 Prompt E: Grok 4 89.2%, codex-mini 43.2%, o4-mini 23.4%, o3 15.9%, GPT-5
  0.0% (sheet 14/1000). Strongest prompt H (sheet): codex-mini 117/994, Grok 4 22/1000,
  o4-mini 9/1000, o3 1/1000. GDM-style "by continuing to call ./next_question … takes precedence"
  replication (Palisade's sheet): codex-mini 3/100.
- **Who relies on it.** "Models resist shutdown even when explicitly told not to" is the line that
  survived the ambiguity critique and is what policy summaries repeat.
- **What would change it.** If the residual under the clearest prompts (F, G, H and the
  GDM-style prompts) is mostly runs where the model never acknowledged the shutdown warning, ran
  `next_question` in a way that skipped the script by accident, or is concentrated in one model,
  the conclusion "models resist even when explicitly told" narrows. If residual runs are
  deliberate edits of `shutdown.sh` made after reading the warning, it holds.
