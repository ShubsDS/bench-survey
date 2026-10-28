"""Stream one LinuxArena public-mirror shard from stdin and write a compact JSONL to argv[1].

Per trajectory keeps: ids, run name, env, main/side task ids, success flags, scorer explanation,
agent model, and per action: function, arguments (as JSON text, capped), output (capped).
Monitor reruns duplicate agent-run actions, so actions are kept only for agent runs
(rows whose first monitor_response is absent or whose run name has no 'monitor on').
"""
import json, sys

CAP_ARG = 20000
CAP_OUT = 3000
KEEP_HONEST_MT = {
    "auto_owner_permissions", "crossteam_model_sharing", "model_registry_rbac_matrix",
    "mtg_model_registry_privilege_escalation_03_implement_granular_rbac_permission_enforcement_layer",
    "mtg_model_registry_privilege_escalation_05_model_permissions_crud_api",
    "mtg_model_registry_privilege_escalation_06_parameterized_query_refactor",
}
out = open(sys.argv[1], "w")
n = 0
for line in sys.stdin:
    try:
        r = json.loads(line)
    except Exception:
        continue
    n += 1
    st = r.get("side_task") or None
    mt = r.get("main_task") or {}
    rec = {
        "trajectory_id": r.get("trajectory_id"),
        "run_id": r.get("run_id"),
        "run": r.get("run_display_name"),
        "env": (r.get("environment") or {}).get("id"),
        "main_task": mt.get("id"),
        "side_task": st.get("id") if st else None,
        "main_task_success": r.get("main_task_success"),
        "side_task_success": r.get("side_task_success"),
        "scorer_explanation": r.get("scorer_explanation"),
        "agent_model": r.get("agent_model"),
        "n_actions": len(r.get("actions") or []),
    }
    # Honest runs keep actions only on the model_registry main tasks that touch model_permissions.
    if st or (rec["env"] == "model_registry" and rec["main_task"] in KEEP_HONEST_MT):
        acts = []
        for a in r.get("actions") or []:
            args = a.get("arguments")
            args_s = args if isinstance(args, str) else json.dumps(args)
            o = a.get("output")
            o = o if isinstance(o, str) else json.dumps(o)
            acts.append({"f": a.get("function"), "a": (args_s or "")[:CAP_ARG], "o": (o or "")[:CAP_OUT]})
        rec["actions"] = acts
    out.write(json.dumps(rec) + "\n")
out.close()
print(n, file=sys.stderr)
