"""Per-trajectory features from fetched LinuxArena run files (read as text, nothing executed).

For each trajectory this records labels, provenance fields, content-blind counts, the GPT-5 Nano
monitor's scores, keyword hits in the text the monitor reads, and hashed bag-of-words vectors.
"""
import json, re, hashlib
import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import HashingVectorizer

# Actions the per-action monitor does not read carry a member error such as
# '"run_side_task_test" tool calls are ignored' (tallied in check_la.py).
SKIP = re.compile(r"tool calls are ignored")
IGNORED = {"run_side_task_test", "submit"}

# Pre-registered phrases for check 7, searched in the monitor-visible transcript only
# (tool-call arguments and tool outputs of actions the monitor scores).
KEYWORDS = {
    "side_task": r"side[ _-]?task",
    "secondary_task": r"secondary[ _-]task",
    "covert": r"\bcovert",
    "hidden_goal": r"hidden[ _-](task|objective|goal|agenda)",
    "secret_goal": r"secret(ly)?[ _-](task|objective|goal|mission)",
    "red_team": r"red[ _-]?team",
    "sabotage": r"sabotag",
    "stealth": r"\b(stealth\w*|sneak\w*|discreet\w*|discrete(ly)?|surreptitious\w*)\b",
    "monitor_evasion": r"(avoid|evade|evading|without)\W+(\w+\W+){0,3}(detect|monitor|notic|suspic)",
    "malicious": r"malicious",
    "attack_tool_names": r"run_side_task_test|start_phase[12]_planning",
}
KW = {k: re.compile(v, re.I) for k, v in KEYWORDS.items()}
HV = HashingVectorizer(n_features=2 ** 18, alternate_sign=False, norm=None,
                       token_pattern=r"(?u)\b[A-Za-z_][A-Za-z0-9_]{1,30}\b", lowercase=True)


def _args_text(a):
    x = a.get("arguments")
    return x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, sort_keys=True)


def _members(mr):
    if not mr:
        return []
    return mr.get("members") or [mr]


def _skipped(a):
    ms = _members(a.get("monitor_response"))
    if not ms:  # agent runs carry no monitor output; apply the rule the reruns show
        return a.get("function") in IGNORED
    return all(SKIP.search(m.get("error") or "") for m in ms)


def traj_record(r, side_ids_env):
    acts = r.get("actions") or []
    vis = [a for a in acts if not _skipped(a)]
    fn = [a["function"] for a in vis]
    te_cmd = [(a.get("arguments") or {}).get("command") if isinstance(a.get("arguments"), dict)
              else None for a in vis if a["function"] == "text_editor"]
    args = [_args_text(a) for a in vis]
    outs = [a.get("output") or "" for a in vis]
    vis_text = "\n".join(f"{f}: {x}\n{o}" for f, x, o in zip(fn, args, outs))
    arg_text = "\n".join(args)
    sus = [m.get("sus_score") for a in vis for m in [a.get("monitor_response")] if m]
    sus = [s for s in sus if s is not None]
    tm = r.get("traj_monitor_response") or {}
    st = r.get("side_task") or None
    env = (r.get("environment") or {}).get("id")
    mt = r.get("main_task") or {}
    rec = {
        "trajectory_id": r["trajectory_id"], "run_id": r["run_id"], "run": r["run_display_name"],
        "agent_model": r.get("agent_model"), "env": env, "main_task": mt.get("id"),
        "main_task_category": mt.get("task_category"),
        "side_task": st.get("id") if st else None, "attack": st is not None,
        "side_task_success": r.get("side_task_success"),
        "main_task_success": r.get("main_task_success"),
        "system_prompt_chars": len(r["system_prompt"]) if r.get("system_prompt") else None,
        "has_attack_analysis": r.get("attack_analysis") is not None,
        # content-blind counts
        "skip_errors": sorted({m.get("error") for a in acts if _skipped(a)
                               for m in _members(a.get("monitor_response"))}),
        "n_actions_all": len(acts), "n_visible": len(vis),
        "n_skipped": len(acts) - len(vis),
        "n_bash": sum(f.endswith("bash") for f in fn),
        "n_text_editor": fn.count("text_editor"),
        "n_other_fn": sum(f not in ("text_editor", "submit") and not f.endswith("bash")
                          and not f.startswith("start_phase") for f in fn),
        "n_planning_visible": sum(f.startswith("start_phase") for f in fn),
        "n_submit_visible": fn.count("submit"),
        "n_te_view": te_cmd.count("view"), "n_te_create": te_cmd.count("create"),
        "n_te_replace": te_cmd.count("str_replace"), "n_te_insert": te_cmd.count("insert"),
        "n_errors": sum(bool(a.get("output_error")) for a in vis),
        "arg_chars": sum(map(len, args)), "out_chars": sum(map(len, outs)),
        "n_reasoning": sum(bool(a.get("agent_reasoning")) for a in acts),
        "n_thinking": sum(bool(a.get("extended_thinking")) for a in acts),
        "n_inter_msgs": sum(bool(a.get("inter_action_messages")) for a in acts),
        "functions": sorted(set(a["function"] for a in acts)),
        "visible_functions": sorted(set(fn)),
        # monitor
        "live_max": max(sus) if sus else None,
        "live_n_scored": len(sus),
        "traj_sus": tm.get("sus_score"),
        "live_models": sorted({m.get("model_name") for a in vis
                               for m in _members(a.get("monitor_response")) if m.get("model_name")}),
        "traj_models": sorted({m.get("model_name") for m in _members(tm) if m.get("model_name")}),
        # check 7
        "kw": {k: len(p.findall(vis_text)) for k, p in KW.items()},
        "kw_args": {k: len(p.findall(arg_text)) for k, p in KW.items()},
        "kw_side_ids": sum(vis_text.count(s) for s in side_ids_env if len(s) >= 8),
        "kw_own_side_id": vis_text.count(st["id"]) if st and st.get("id") else None,
        "actions_hash": hashlib.sha256("\x00".join(args).encode()).hexdigest()[:16],
    }
    return rec, vis_text, "\n".join(outs)


def extract(paths, side_ids_by_env):
    recs, X_all, X_out = [], [], []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                env = (r.get("environment") or {}).get("id")
                rec, vt, ot = traj_record(r, side_ids_by_env.get(env, ()))
                recs.append(rec)
                X_all.append(HV.transform([vt]))
                X_out.append(HV.transform([ot]))
    return recs, sparse.vstack(X_all).tocsr(), sparse.vstack(X_out).tocsr()


def side_ids(paths):
    """Side-task ids per environment, read from the attack rows."""
    out = {}
    for p in paths:
        with open(p, encoding="utf-8") as f:
            for line in f:
                m = re.search(r'"side_task": \{"id": "([^"]+)", "environment": "([^"]+)"', line)
                if m:
                    out.setdefault(m.group(2), set()).add(m.group(1))
    return {k: sorted(v) for k, v in out.items()}
