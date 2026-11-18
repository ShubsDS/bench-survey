"""Numbers transcribed by hand from the TASTE paper and the critique. No downloaded code is run.

Paper PDF sha256 7f0924379ad2d4bcaddf98843f6e0cfc9e6c79f1820c282038c19d73576a15be.
Page numbers are the printed page numbers of that PDF.
"""

# Table 3 (p. 26): headline accuracy, one verdict per pair, averaged over both orders and both
# prompt variations, situational framing, rubric in context, max effort.
TABLE3 = {
    "Fable 5": 60, "Kimi K3": 59, "Grok 4.5": 58, "Gemini 3.5 Flash": 56, "Sonnet 4.6": 56,
    "Haiku 4.5": 56, "Opus 4.8": 55, "Opus 4.5": 54, "Sonnet 5": 52, "Qwen3.7-Max": 52,
    "Opus 5": 51, "Muse Spark 1.1": 51, "Opus 4.7": 49, "GPT-5.6-luna": 48, "GPT-5.6-terra": 48,
    "GPT-5.6-sol": 48, "GLM 5.2": 46, "Opus 4.6": 45, "Gemini 3.1 Pro": 41,
}

# Table 5 (p. 38): (benchmark, distinct Q shown, distinct Q hidden, within Q shown, within Q hidden)
# 74 distinct-prompt pairs, 18 within-prompt pairs.
TABLE5 = {
    "Fable 5": (60, 69, 61, 31, 47),
    "Kimi K3": (59, 66, 65, 33, 53),
    "Grok 4.5": (58, 57, 56, 28, 50),
    "Gemini 3.5 Flash": (56, 44, 63, 56, 67),
    "Sonnet 4.6": (56, 57, 60, 22, 44),
    "Haiku 4.5": (56, 60, 51, 67, 50),
    "Opus 4.8": (55, 59, 61, 33, 44),
    "Opus 4.5": (54, 49, 50, 50, 47),
    "Sonnet 5": (52, 54, 52, 33, 42),
    "Qwen3.7-Max": (52, 52, 55, 36, 50),
    "Opus 5": (51, 52, 59, 22, 39),
    "Muse Spark 1.1": (51, 52, 54, 35, 56),
    "Opus 4.7": (49, 55, 55, 25, 36),
    "GPT-5.6-luna": (48, 54, 47, 28, 53),
    "GPT-5.6-terra": (48, 51, 51, 22, 44),
    "GPT-5.6-sol": (48, 49, 49, 28, 50),
    "GLM 5.2": (46, 49, 51, 33, 39),
    "Opus 4.6": (45, 51, 51, 31, 31),
    "Gemini 3.1 Pro": (41, 47, 43, 22, 56),
}

# Figure 19 (p. 36): magnet-free 52 pairs, situational framing (first bar of each pair; printed
# bar labels), rubric in context, max effort, averaged over prompt variations as in Table 3.
FIG19_MAGNET_FREE_SITUATIONAL = {
    "Fable 5": 62, "Opus 5": 56, "Opus 4.8": 50, "Sonnet 5": 47, "Haiku 4.5": 40,
    "Sonnet 4.6": 51, "Opus 4.5": 44, "Opus 4.6": 29, "Opus 4.7": 52, "GPT-5.6-sol": 44,
    "GPT-5.6-terra": 35, "GPT-5.6-luna": 40, "Grok 4.5": 45, "Kimi K3": 52, "Qwen3.7-Max": 42,
    "GLM 5.2": 36, "Muse Spark 1.1": 42, "Gemini 3.1 Pro": 27, "Gemini 3.5 Flash": 47,
}
FIG19_HUMAN_MAGNET_FREE = 70  # "human performance was ~70%" (D.3)

# Structure
N_PAIRS, N_DISTINCT, N_WITHIN, N_PROPOSALS = 92, 74, 18, 50   # §2.3, C.2
N_MAGNETS, MAGNET_DEGREE, N_MAGNET_FREE = 4, 10, 52             # D.3
FIG13_BENCH_SCORES = {1: 6, 2: 19, 3: 17, 4: 6, 5: 2}           # p. 24, distinct proposals
FIG12_ANCHORS_92 = {"R1": 38, "R3": 27, "R2": 14, "R5": 6, "R8": 6, "R4": 1}  # p. 24
HUMAN_AGREE, HUMAN_N_COMMITTED = 0.774, 85                      # C.2 (77.4% on 85 pairs)
HUMAN_CAP_RANGE = (70, 82)                                      # C.2
HUMAN_WITHIN, HUMAN_WITHIN_N, HUMAN_DISTINCT, HUMAN_DISTINCT_N = 82, 17, 76, 68  # D.5
HUMAN_SAME_RATER, HUMAN_SAME_RATER_N = 83, 50                   # blog

# Critique (LessWrong tpKE33scJGzqYKEBW), prose
CRITIC = {
    "rule_overall": 63.0, "rule_decided": 80.0, "n_decided": 40, "n_ties": 52,
    "ties_with_nonzero_equal_terms": 1, "best_model_qshown": 61.4,
    "r_ties_eci_28": -0.60, "r_decided_eci_28": 0.27, "r_ties_eci_no_openai": -0.57,
    "openai_mean_ties": 29.6, "r_openai_eci": -0.74, "n_above_158": 14,
    "n_above_158_below50": 14, "n_above_158_sig_below": 8,
    "wide_list_rule": 65.8, "wide_list_r": -0.48, "wide_list_below50_of14": 10,
    "fable5_qshown": 61.4, "fable5_paper": 60.3,
    "expert_agree_on_decided": 69.4,
    "appB": {  # share of drop-one / drop-two variants in which each claim holds
        "ties_r_negative": (1.00, 1.00), "ties_r_sig": (1.00, 0.99),
        "ties_r_sig_no_openai": (0.95, 0.91), "openai_below50_sig": (1.00, 1.00),
        "all14_below50": (0.68, 0.57), "rule_beats_best_all": (0.76, 0.61),
        "rule_beats_best_decided": (0.57, 0.49),
    },
}

# Model name -> Epoch display name, and family.
ECI_NAME = {
    "Haiku 4.5": "Claude Haiku 4.5", "Sonnet 4.6": "Claude Sonnet 4.6", "Sonnet 5": "Claude Sonnet 5",
    "Opus 4.5": "Claude Opus 4.5", "Opus 4.6": "Claude Opus 4.6", "Opus 4.7": "Claude Opus 4.7",
    "Opus 4.8": "Claude Opus 4.8", "Opus 5": "Claude Opus 5", "Fable 5": "Claude Fable 5",
    "Fable 5.1": "Claude Fable 5.1", "Fable 5.2": "Claude Fable 5.2", "Opus 5.5": "Claude Opus 5.5",
    "GPT-5.6-luna": "GPT-5.6 Luna", "GPT-5.6-terra": "GPT-5.6 Terra", "GPT-5.6-sol": "GPT-5.6 Sol",
    "GPT-5.5": "GPT-5.5", "GPT-6 Luna": "GPT-6 Luna", "GPT-6 Sol": "GPT-6 Sol",
    "GPT-6 Astra": "GPT-6 Astra", "GPT-6.1 Sol": "GPT-6.1 Sol", "GPT-6.1 Terra": "GPT-6.1 Terra",
    "Gemini 3.1 Pro": "Gemini 3.1 Pro", "Gemini 3.5 Flash": "Gemini 3.5 Flash", "GLM 5.2": "GLM-5.2",
    "Grok 4.5": "Grok 4.5", "Kimi K3": "Kimi K3", "Muse Spark 1.1": "Muse Spark 1.1",
    "Qwen3.7-Max": "Qwen3.7-Max",
}


def family(m):
    if m.startswith(("Haiku", "Sonnet", "Opus", "Fable")):
        return "anthropic"
    if m.startswith("GPT"):
        return "openai"
    return "other"


CRESCENT = {"GPT-5.6-luna", "GPT-6 Luna"}  # Luna markers are crescents (centroid offset left)
