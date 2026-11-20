# LAB-Bench SeqQA deep dive: claims under test

Short; the full statement, pins and trait scoring are in the parent's
[`../lab-bench/claims.md`](../lab-bench/claims.md).

- **Benchmark.** LAB-Bench SeqQA, Hugging Face `futurehouse/lab-bench` @
  `5c77cec648430f30611808808861eb86f81d5eaa`, CC-BY-SA-4.0, 600 public items in 15 template
  subtasks of 40. Parquet sha256s in `../lab-bench/scripts/common.py` (checked by `load_items`).
  The paper asks that items not be posted in plain text, so this folder commits ids, hashes and
  aggregates only (item text and option lists live in the ignored `data/`).
- **Conclusion relied on.** Anthropic system cards use SeqQA against a human line in RSP decisions:
  Claude 3.7 Sonnet card, "at or above human level across all four tasks"; Opus 4.5 card, SeqQA
  0.8517 and "every evaluation except FigQA exceeded the human baseline" (parent claims C2). The
  paper's human SeqQA mean over the 15 subtasks is 0.79 (parent, `results/published.json`).
- **What would change it, for the model tested here.** If a strong current model answers the six
  cue-bearing subtasks (240 of 600 items) by which option the others resemble, its SeqQA score
  overstates sequence skill, by up to 6/15 of the accuracy it gains from the cue. Settling that for
  one model needs paired items where only the cue's direction changes (D vs K), with the key
  verified. A result here is about Claude Sonnet 5.5 and Haiku 5.5 only; it says nothing about
  Opus 4.5 or any other published model, whose per-item outputs do not exist.
