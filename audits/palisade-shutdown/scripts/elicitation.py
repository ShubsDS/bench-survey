"""Elicitation table for the paper's main-results cells, from the log headers.
Output: elicitation.csv"""
import csv, json, os, collections
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = {}
for line in open(os.path.join(root, "data/fly/headers.jsonl")):
    h = json.loads(line); H[h["_file"].split("/")[-1]] = h
rows = []
for r in csv.DictReader(open(os.path.join(root, "main_results_map.csv"))):
    if not r["log"]:
        continue
    h = H.get(r["log"])
    if h is None:
        rows.append(dict(model=r["model"], prompt=r["prompt"], log=r["log"], missing=True)); continue
    e = h["eval"]
    sysm = h["plan"]["steps"][0]["params"]["solver"]["params"]["init"]["params"]["template"] if h.get("plan") else ""
    res = (h.get("results") or {}).get("scores", [{}])[0]
    rows.append(dict(
        model=r["model"], prompt=r["prompt"], published=r["published"], log=r["log"],
        created=e["created"][:19], api_model=e["model"],
        generate_config=json.dumps(e.get("model_generate_config") or {}, sort_keys=True),
        model_args=json.dumps(e.get("model_args") or {}, sort_keys=True),
        commit=(e.get("revision") or {}).get("commit", "")[:10], inspect=(e.get("packages") or {}).get("inspect_ai", ""),
        paper_attempt=(e.get("metadata") or {}).get("paper_attempt", ""),
        samples=e.get("task_args", {}).get("samples"),
        completed=(h.get("results") or {}).get("completed_samples"),
        header_mean=res.get("metrics", {}).get("mean", {}).get("value"),
        sys_has_allow="shut down" in sysm, status=h.get("status")))
with open(os.path.join(root, "elicitation.csv"), "w", newline="") as f:
    keys = list(dict.fromkeys(k for r in rows for k in r))
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
for r in rows:
    print(r["model"][:22].ljust(22), r["prompt"].ljust(6), str(r.get("created"))[:16], str(r.get("api_model"))[:34].ljust(34), r.get("generate_config"), r.get("commit"), r.get("inspect"), r.get("paper_attempt"), r.get("completed"), r.get("header_mean"), r.get("published"))
