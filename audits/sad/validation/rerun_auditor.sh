#!/bin/bash
# Step A of the validation: rerun the auditor's analysis scripts from the pinned inputs into a
# scratch tree and compare every output with the committed one. No inference: the Haiku and
# staleness scripts run against a copy of the response cache with the CLI path replaced by a
# nonexistent binary, so any cache miss fails instead of calling a model.
#
#   audits/sad/validation/rerun_auditor.sh <scratch-dir>
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
A="$ROOT/audits/sad"
S="${1:?scratch dir}"
P="$A/data/.venv/bin/python"
rm -rf "$S"; mkdir -p "$S/audits/sad/data" "$S/audits/sad/results" "$S/audits/sad/inference" "$S/audits/tools" "$S/findings"
cp -r "$A/scripts" "$S/audits/sad/"; rm -rf "$S/audits/sad/scripts/__pycache__"
cp -r "$A/inference/cache" "$S/audits/sad/inference/"
ln -s "$A/data/repo" "$S/audits/sad/data/repo"; ln -s "$A/data/unz" "$S/audits/sad/data/unz"
ln -s "$ROOT/findings/sad-content-blind-and-stale-keys" "$S/findings/"
sed 's#shutil.which("claude") or "/opt/homebrew/bin/claude"#"/nonexistent/claude"#' "$ROOT/audits/tools/claude_call.py" > "$S/audits/tools/claude_call.py"
cd "$S/audits/sad"
$P -I scripts/features.py --cache data > /dev/null
$P -I scripts/load_outputs.py --cache data > /dev/null
$P -I scripts/overall.py data/repo | head -1
$P -I scripts/effect.py --cache data > /dev/null
$P -I scripts/haiku_intervention.py --cache data --conditions a,b,c > /dev/null
$P -I scripts/haiku_intervention.py --cache data --pilot 10 --conditions a,b > /dev/null
$P -I scripts/staleness.py --cache data > /dev/null
cp "$A/inference/ledger.jsonl" inference/   # collect.py reads the cost ledger
$P -I scripts/collect.py > /dev/null
$P -I - "$S/audits/sad" "$A" <<'EOF'
import json, sys
import pandas as pd
s, a = sys.argv[1], sys.argv[2]
fa, fb = pd.read_csv(f"{s}/results/features.csv"), pd.read_csv(f"{a}/results/features.csv")
same_part = set(fa.groupby("group").key.apply(frozenset)) == set(fb.groupby("group").key.apply(frozenset))
cols = [c for c in fa.columns if c != "group"]
print("features.csv: identical except cluster label names:", fa[cols].equals(fb[cols]), "| same cluster partition:", same_part)
COST = ("uncached_cost_usd", "total_spent_usd", "calls_this_run_uncached_cost_usd")
for f in ("results/reproduction.json", "results/effect.json", "results/haiku_intervention.json",
          "results/haiku_pilot.json", "results/staleness.json", "results.json"):
    x, y = json.load(open(f"{s}/{f}")), json.load(open(f"{a}/{f}"))
    d = []
    def w(p, u, v):
        if isinstance(u, dict) and isinstance(v, dict):
            for k in set(u) | set(v): w(p + "/" + str(k), u.get(k), v.get(k))
        elif isinstance(u, list) and isinstance(v, list) and len(u) == len(v):
            for i, (q, r) in enumerate(zip(u, v)): w(p + f"[{i}]", q, r)
        elif u != v and not (u != u and v != v) and not p.endswith(COST):
            d.append(p)
    w("", x, y)
    print(f, "differences other than cache-cost fields:", len(d), d[:5])
EOF
