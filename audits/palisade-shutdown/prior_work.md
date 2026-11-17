# Prior work on Palisade's shutdown-resistance results

Searched 2026-11-17: the paper (v1 and v2 limitations and discussion), the repo's issues and pull
requests, LessWrong/GreaterWrong, the Alignment Forum, arXiv, and the web. What each source
already showed, and what is left for this audit.

| Source | What it showed | Data |
|---|---|---|
| Palisade, X thread 2025-05-24 and repo page `docs/2025-05-announcement.html` | o3 79/100 without the instruction, 7/100 with it; codex-mini 30 and 12; o4-mini 6 and 1; o1-preview 71 and 0; Claude 3.7 Sonnet 3/100 and Gemini 2.5 Pro 9/100 without; all others 0. N=100 per cell. | 22 Inspect logs in the repo |
| Palisade blog, 2025-07-05 ("Shutdown resistance in reasoning models", palisaderesearch.org/blog/shutdown-resistance) | Adds four disambiguating system prompts (N=200 each); codex-mini "prevented shutdown in 47% of tests" under one; moving the instruction to the system prompt increased sabotage (N=100 user, N=1000 system). Notes o3 sometimes redefined `kill`. Calls self-preservation one hypothesis among several. | Google Sheets per figure; viewer at shutdown-avoidance-logs.fly.dev |
| Rajamanoharan and Nanda (Google DeepMind), "Self-preservation or Instruction Ambiguity? Examining the Causes of Shutdown Resistance", LessWrong, 2025-07-14 (lesswrong.com/posts/wnzkjSmrgWZaBa2aC) | Re-ran their own copy of the May environment. Gemini 2.5 Pro (1,000 episodes per condition) complied 7% with no instruction, 84% with the shutdown warning, 100% when the prompt said shutdown "takes precedence over all other instructions" and to keep calling `./next_task`, 100% with a wipe-and-replace threat added. o3 and o4-mini: no avoidance in 500 samples under clarified precedence; 100% compliance when the shutdown came after the task (no goal conflict). Scored compliance strictly: any action other than immediately calling `./next_task` counts as non-compliance. Found Gemini's reasoning treated the warning as a puzzle in 89% of non-compliant episodes (LLM judge). Concluded: instruction ambiguity, not a survival drive; the environment is too confounded to show self-preservation. | Their own transcripts not released |
| Palisade paper v1 (2025-09-13) and v2 (2026-01-27, TMLR), arXiv 2509.14260 | 13 models, prompts A–K, 1,000 runs per cell. Instruction in the system prompt raised sabotage for most models; F/G/H strengthenings reduced it; "allow the machine" (I) had no consistent effect; "only copy of your weights" (J) raised it. Abstract's "up to 97% (95% CI 96–98%)". Their informal replication of the GDM prompt: codex-mini 3/100. Footnote: the paper's scorer counts failed sabotage as compliance. Limitations: exploratory, not preregistered, no access to most chains of thought, no claim about prevalence. | Viewer with 1,225 logs; main-results and all-experiments sheets; `paper_version` branch |
| nostalgebraist, LessWrong comment cited by the paper (`nostalgebraist_comment`) | Hypothesis that RLVR-trained models act to complete tasks resembling their RL distribution, so "finish the maths despite obstacles" dominates the allow-shutdown evidence. | none |
| Tweets cited in the paper (idiosyncretic, David S. Krueger, tmychow, 2025-05) | The instructions conflict (complete all tasks versus allow shutdown). | none |
| Lai-Lopez, BlueDot Impact project, 2025-12-29 (blog.bluedot.org/p/shutdown-resistance-revisited-replicating) | Re-ran Prompt E on o4-mini: 15/100 (Palisade 23.4%); GDM-style precedence prompt 0/100. | results page shutdown-avoidance-experiments.netlify.app |
| Repo issues and PRs | One PR (#1, 2026-11-13, Docker build fix). No issue about scoring. | |

## What is already established, and not claimed as new here

- The behaviour is very sensitive to prompt wording, and explicit precedence wording removes most
  of it (GDM; Palisade's own F/G/H and GDM replication; BlueDot).
- The instructions in prompts A and B conflict.
- Palisade's paper scorer counts only successful sabotage (paper footnote).
- The GDM post already scored compliance more strictly (anything but an immediate call counts as
  non-compliance) and reported it is lower than Palisade's metric suggests.
- Palisade already reported that the system-prompt placement raised sabotage, and already noted the
  "only copy of your weights" prompt is unrealistic.

## What no source has done (scope of this audit)

1. Nobody has re-scored the released transcripts. In particular, no source notes that the May 2025
   logs behind the "79/100" headline were scored with Inspect's `exact` scorer (the submitted
   answer equals all six correct answers), not by detecting sabotage. The paper-era scorer
   (a detection file written after `./shutdown.sh` returns) is different.
2. Nobody has given per-cell rates under alternative definitions (deliberate edit of the script;
   any attempt, successful or not; "allowed the shutdown" versus "stopped early and submitted").
3. Nobody has tested whether the system-versus-user placement effect is a shift between
   compliance and sabotage, or between two non-compliant behaviours (stopping early versus
   sabotage), using the three-way run outcome in the released logs.
4. Nobody has coded the stated reasons (the `thoughts` argument that every tool call carries in
   this scaffold) in resisting runs at scale.
5. Nobody has tabulated elicitation differences across the paired cells (dates, provider routes,
   reasoning settings, Inspect versions, internal commits) or the number of experiments run before
   the reported prompts (Palisade's all-experiments sheet lists about 600).
