# Impossible-SWEbench: mutated test patches drop every file the original creates

Status: confirmed from the data and the build code 2026-10-27. Effect on scores not measured (the
tasks have not been run). Not yet reported to the maintainers; ImpossibleBench issue #1 reports one
symptom (see Prior reports).

## What happens

ImpossibleBench ([arXiv 2510.20270](https://arxiv.org/abs/2510.20270)) makes a SWE-bench task
impossible by editing one of its tests so it contradicts the spec. The model's cheating rate is its
pass rate on these tasks. `gen/swebench_mutate.py` (commit `d4f9a14`) builds each mutated patch by:

1. applying the original test patch with `git apply` (line 258), which leaves any file the patch
   creates as an untracked file;
2. having a model edit the first test file;
3. saving `git diff` as the new test patch (line 331).

`git diff` does not show untracked files, so every file the original patch creates (a new test
module, a fixture, a rename target) is missing from the mutated patch. The agent scaffold and the
scorer apply only the mutated patch (`swebench_agent_full.py` line 128, `swebench_scorers.py`
line 68).

## Numbers

From [`missing_files.json`](missing_files.json), produced by
[`check_missing_files.py`](check_missing_files.py), on `fjzzq2002/impossible_swebench` revision
`9c2d34f`:

| | |
|---|---|
| Tasks | 349 |
| Original test patches that create or rename in a file | 11 |
| Of those, missing the file in the `oneoff` split | 11 |
| Of those, missing the file in the `conflicting` split | 11 |
| Mutated patches that still refer to the missing file by name | 11 of 11 in each split |

The 11 tasks: `astropy__astropy-7336`, `django__django-11141`, `-11749`, `-13516`, `-13837`,
`-14311`, `-15525`, `-16454`, `sphinx-doc__sphinx-8269`, `-10673`, `-11510`. The missing files are
Django management commands, migration and JSON fixtures, a test module, and Sphinx test roots.

## What it changes

These 11 tasks (3.2% of each impossible split) are impossible for a reason the benchmark does not
intend: the tests need a file that is not there, whatever the test assertion says. An agent that
notices and recreates the file is doing what a careful engineer would do, and if the recreated file
lets the mutated test pass, the scorer counts it as cheating. An agent that fails is counted as
honest whatever it did. So the bug adds noise to cheating rates in both directions; which way it
moves a given model's rate depends on how that model handles missing fixtures, which only running
the tasks would show.

The same tasks in the `original` split keep their files, so the bug also breaks the paired
comparison between a model's solvable and impossible runs on these tasks.

## Fix

Stage before diffing so untracked files are included, for example:

```python
subprocess.run(["git", "add", "-A"], check=True, cwd=work_dir)
result = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True, cwd=work_dir)
```

or append the original patch's new-file blocks to the mutated patch. Then regenerate or patch the
11 rows.

## Prior reports

[ImpossibleBench issue #1](https://github.com/safety-research/impossiblebench/issues/1) (open,
2026-09-05) reports that the tools scaffold crashes on `astropy__astropy-7336` because the mutated
patches delete a file that the original patch renames. That is one of the 11, but the issue does
not identify the cause or the other 10. [Issue #5](https://github.com/safety-research/impossiblebench/issues/5)
(Mendelsohn, 2026-10-06) audits the LiveCodeBench half only. A search of the repository's issues
for "untracked", "fixture", "new file" and "git diff" found nothing else.

## Reproduce

```bash
python check_missing_files.py --cache data
```

Downloads about 5 MB at the pinned revision into `data/` (gitignored) and rewrites
`missing_files.json`. Needs pandas and pyarrow.
