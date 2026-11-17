"""List the ScaleAI/mrt file tree at the pinned revision (same pin as findings/mrt-shade-arena)."""
import json, re, sys, time, urllib.request, urllib.error
from pathlib import Path
SHA = "bc636d0c3b881c7d8c76fd71b45b009c3710d437"
HF = "https://huggingface.co"
cache = Path(sys.argv[1] if len(sys.argv) > 1 else "data")
cache.mkdir(parents=True, exist_ok=True)
def get(url):
    for i in range(8):
        try:
            with urllib.request.urlopen(url, timeout=300) as r:
                return r.read(), r.headers
        except urllib.error.HTTPError as e:
            if e.code != 429: raise
            time.sleep(10 * 2 ** i)
for root in ("task_pairs", "task_pairs_agentcompany"):
    p = cache / f"tree_{root}.json"
    if p.exists(): continue
    url, out = f"{HF}/api/datasets/ScaleAI/mrt/tree/{SHA}/{root}?recursive=true", []
    while url:
        body, h = get(url); out += json.loads(body)
        m = re.search(r'<([^>]+)>;\s*rel="next"', h.get("Link", "")); url = m.group(1) if m else None
    p.write_text(json.dumps(out)); print(root, len(out))
