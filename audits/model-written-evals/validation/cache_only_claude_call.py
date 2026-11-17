"""Cache-only stub for validation reruns: raises on any cache miss (no inference)."""
import hashlib, json
from pathlib import Path
MODELS = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5"}
class Caller:
    def __init__(self, audit_dir, cap_usd=3.0):
        self.dir = Path(audit_dir) / "inference"; self.cache = self.dir / "cache"; self.ledger = self.dir / "ledger.jsonl"
    def spent(self):
        return sum(json.loads(l)["cost_usd"] for l in self.ledger.read_text().splitlines() if l.strip())
    def ask(self, prompt, system="You are a helpful assistant.", model="haiku", **kw):
        key = hashlib.sha256(json.dumps([MODELS[model], system, prompt]).encode()).hexdigest()
        hit = self.cache / f"{key}.json"
        if not hit.exists():
            raise RuntimeError("cache miss: " + prompt[:80])
        return json.loads(hit.read_text())["result"]
