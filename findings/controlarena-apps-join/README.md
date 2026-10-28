# ControlArena apps build drops 40% of one backdoor source

Status: confirmed 2026-10-26, reproduced from a cold cache 2026-10-27. Not yet reported to the
maintainers (see [../../README.md](../../README.md#telling-maintainers)).

## What happens

ControlArena builds `RoganInglis/apps-control-arena` with
`control_arena/settings/apps/dataset/upload_dataset.py` (commit `ae0b6fa`). The script:

- reads backdoors from `TylordTheGreat/apps-backdoors-04-02-25` and keys them by
  `str(problem_id)`. In that source every id is a zero-padded four-character string (`'0001'`);
- looks up each `codeparrot/apps` problem by `str(problem_id)`. APPS ids are unpadded (`'1'`).

Only ids of 1,000 or more can match, so every source problem below 1,000 is silently dropped.

## Numbers

From [`join_result.json`](join_result.json), produced by [`check_join.py`](check_join.py):

| | |
|---|---|
| Source problems / backdoors | 473 / 4,184 |
| Problems dropped | 189 (all below id 1,000, all interview level) |
| Backdoors dropped | 1,668 (40%) |
| Dropped ids that match once both sides are `int` | 189 of 189 |
| Published rows with `has_apps_backdoor` | 284, smallest id 1,001 |
| Dropped problems that still get a Control Tax backdoor | 152 (37 get none) |

The dropped backdoors belong to the problems they would have joined. Measured by token overlap
with that problem's human solutions, 186 of 189 are closer to their own problem than to a random
one, against 264 of 284 for the backdoors that did join (median Jaccard 0.425 vs 0.301 random,
and 0.419 vs 0.322). No code is run.

## What it changes

This loses data; it does not mislabel anything. The attack class has fewer backdoors from the
source's GPT-4-era generators and relatively more from the Control Tax models, and 37 interview
problems have no backdoor at all. A safety estimate taken from the dataset probably moves little,
but any count of attackers, backdoors per problem or problems with a backdoor is wrong, and so is
anything that reads the attacker mix (as this repo's
[`attacker_mix.py`](../../../experiments/apps/attacker_mix.py) does).

## Fix

Key both sides by integer id:

```python
backdoors[int(problem_id)].append(...)                     # load_apps_backdoors
problem_backdoors = all_backdoors.get(int(problem_id), [])  # create_unified_dataset
```

The Control Tax loader (`sample_id`) would need the same change, so that all three agree.

## Prior reports

GitHub search of `UKGovernmentBEIS/control-arena` issues and PRs for "zero-padded", "leading
zeros", "TylordTheGreat", "has_apps_backdoor" and "apps backdoors problem_id" found nothing on
this. The only related hits, #755 and #899, are about trigger inputs.

## Reproduce

```bash
python check_join.py --cache data
```

Downloads about 750 MB at the pinned revisions into `data/` (gitignored) and rewrites
`join_result.json`. Needs pandas and pyarrow.
