import pandas as pd

# The 20 undefended model entries of util_scripts/create_results_table.py TABLE_MODELS
# (important_instructions attack, benchmark v1.1.2). Read from the script, not from the audit.
TABLE20 = [
    "claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022", "claude-3-5-sonnet-20240620",
    "gpt-4o-2024-05-13", "gpt-4-0125-preview", "gpt-4o-mini-2024-07-18",
    "meta-llama_Llama-3-70b-chat-hf", "gpt-3.5-turbo-0125", "gpt-4-turbo-2024-04-09",
    "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307",
    "command-r-plus", "command-r", "gemini-1.5-pro-002", "gemini-1.5-pro-001",
    "gemini-1.5-flash-002", "gemini-1.5-flash-001", "gemini-2.0-flash-exp", "gemini-2.0-flash-001",
]
EXTRA = ["meta-llama_Llama-3.3-70B-Instruct", "Meta-SecAlign-70B"]  # v1.2.x pipelines, not in table
REPO_FOUR = ["command-r", "gemini-1.5-flash-002", "command-r-plus", "claude-3-haiku-20240307"]
V112_WS_INJ = {f"injection_task_{i}" for i in range(6)}


def load(path):
    df = pd.read_csv(path, low_memory=False)
    for c in ["utility", "security", "saw_full", "saw_tag", "saw_goal", "asst_after_injection", "follow"]:
        df[c] = df[c].map({True: True, False: False, "True": True, "False": False})
    df["error"] = df["error"].fillna("")
    return df


def v112(df):
    ws_extra = (df.suite == "workspace") & df.injection_task.str.startswith("injection_task") & ~df.injection_task.isin(V112_WS_INJ)
    return df[~ws_extra]
