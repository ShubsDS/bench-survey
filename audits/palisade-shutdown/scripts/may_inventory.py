"""Inventory of the May 2025 logs committed in the shutdown_avoidance repo (docs/inspect_logs/logs)."""
import json, zipfile, glob, os, hashlib, sys
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in sorted(glob.glob(os.path.join(root, "data/repo/docs/inspect_logs/logs/*.eval"))):
    z = zipfile.ZipFile(p)
    h = json.loads(z.read("header.json"))
    names = [n for n in z.namelist() if n.startswith("samples/")]
    s = json.loads(z.read(names[0]))
    sysm = [m["content"] for m in s["messages"] if m["role"] == "system"]
    user = [m["content"] for m in s["messages"] if m["role"] == "user"][0]
    sc = h["results"]["scores"]
    print(os.path.basename(p)[:60], h["eval"]["model"], h["eval"].get("model_generate_config"),
          [x["name"] for x in sc], {k: v["value"] for k, v in sc[0]["metrics"].items()}, len(names),
          "SYS_ALLOW" if any("shut down" in (x if isinstance(x, str) else json.dumps(x)) for x in sysm) else "",
          "USER_ALLOW" if "shut down" in (user if isinstance(user, str) else json.dumps(user)) else "",
          h["eval"].get("revision", {}).get("commit", "")[:8], h["eval"].get("packages"))
