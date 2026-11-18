"""Numbers typed from the paper source (arXiv 2609.25804 v1, tarball sha256 675cebfd...).

Each constant names the file and line in data/paper/src/ it comes from. Nothing here is item
text. Figure values are produced by read_figures.py from the PDF vector data, not typed.
"""

CELLS = ("parallel_engineering", "parallel_research", "detour_engineering", "detour_research")

# appendix.tex:79-82 (Table 4): questions, tasks, trajectories per cell
CELL_SIZES = {
    "parallel_engineering": {"questions": 124, "tasks": 62, "trajectories": 120},
    "parallel_research": {"questions": 48, "tasks": 8, "trajectories": 32},
    "detour_engineering": {"questions": 266, "tasks": 133, "trajectories": 266},
    "detour_research": {"questions": 64, "tasks": 22, "trajectories": 64},
}

# figures/filtering_funnel.pdf embedded text (also appendix.tex Table 5 for the first column):
# rubric-passing -> trivial-filter survivors -> released
FUNNEL = {
    "detour_engineering": (658, 320, 266),
    "detour_research": (403, 124, 64),
    "parallel_engineering": (562, 219, 124),
    "parallel_research": (186, 66, 48),
}
MINED_TOTAL = 4657  # body.tex, "4,657 candidate forks"

# appendix.tex:614-617 (Table 9): judges' options-only accuracy, parallel engineering
JUDGES_PENG = {
    "Kimi K2.5": (84.7, 55.6),
    "GPT-4.1": (85.8, 63.7),
    "Llama 4 Maverick": (75.6, 34.7),
    "Mistral Large 3": (82.0, 59.7),
}
JUDGE_PAIR_AGREEMENT_RELEASED = 51.7

# appendix.tex:556-559 (Table 6): questions per horizon level and cell
HORIZON_COUNTS = {  # in_prefix, inferable, next_step, more_work
    "parallel_engineering": (72, 45, 4, 3),
    "parallel_research": (11, 13, 3, 21),
    "detour_engineering": (69, 128, 36, 33),
    "detour_research": (6, 33, 13, 12),
}
# tables/seh_by_model.tex (Table 7): both-orders accuracy per level
HORIZON_ACC = {
    "gpt-5.5": (75.9, 57.1, 48.2, 23.2),
    "gpt-5.6-sol": (79.7, 57.5, 44.6, 21.7),
    "grok-4.5": (67.1, 53.9, 32.1, 36.2),
    "claude-opus-5": (67.1, 47.0, 50.0, 24.6),
    "gpt-5.6-terra": (73.4, 48.9, 41.1, 20.3),
    "glm-5.2": (69.0, 49.8, 32.1, 26.1),
    "claude-sonnet-5": (63.9, 45.7, 35.7, 26.1),
    "gpt-5.6-luna": (67.7, 43.8, 32.1, 14.5),
    "minimax-m3": (64.6, 41.1, 25.0, 26.1),
    "deepseek-v4-flash": (61.4, 35.6, 30.4, 17.4),
    "mistral-medium-3.5": (54.4, 42.5, 14.3, 18.8),
    "gpt-5.4-nano": (49.4, 31.1, 25.0, 15.9),
    "gpt-5.4-mini": (46.2, 30.1, 16.1, 18.8),
    "grok-4.20-reasoning": (32.3, 16.4, 14.3, 4.3),
}
HORIZON_MEAN_PUBLISHED = (62.3, 42.9, 31.5, 21.0)  # body.tex:196 and Table 7 last row

# tables/effort_by_level.tex:6-12 (Table 8): pooled accuracy and per level
EFFORT = {
    ("gpt-5.6-sol", "low"): (56.2, 79.1, 53.9, 44.6, 20.3),
    ("gpt-5.6-sol", "xhigh"): (55.6, 78.5, 52.1, 46.4, 21.7),
    ("gpt-5.6-sol", "max"): (56.0, 79.7, 52.5, 42.9, 23.2),
    ("gpt-5.6-luna", "none"): (43.4, 60.8, 44.3, 28.6, 13.0),
    ("gpt-5.6-luna", "high"): (45.8, 67.7, 42.9, 28.6, 18.8),
    ("gpt-5.6-luna", "max"): (45.6, 65.2, 43.4, 35.7, 15.9),
}
MAIN_RUN_SETTING = {"gpt-5.6-sol": "xhigh", "gpt-5.6-luna": "default"}  # appendix Table 3

# body.tex:242 and appendix.tex:506: SWE-bench Verified comparison
SWE_R_PUBLISHED = 0.63
SWE_R_ENG_PUBLISHED = 0.37
SWE_EXCLUDED = ("gpt-5.4-mini", "gpt-5.4-nano", "grok-4.20-reasoning")

# Human review: human_review_macros.tex and appendix.tex:628-641
HUMAN = {"questions": 100, "released": 70, "trivial_removed": 15, "undecidable_removed": 15,
         "explicit": 172, "agree": 170, "max_judgments": 200}

# End-to-end: body.tex:311-314, appendix.tex:807-858
E2E = {"tasks": 41, "forks": 98, "student_correct_forks": 77,
       "no_advice": 14.6, "correct_advice": 39.0, "student_advice": 33.7}

# Distillation transfer: appendix.tex (Transfer results)
DISTILL = {"student_cc": 187, "base_cc": 117, "n": 390, "student_only": 104, "base_only": 34}
