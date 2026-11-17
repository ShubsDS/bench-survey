"""Capped, cached calls to a small Claude model through the local `claude` CLI.

Inference here runs on the repository owner's Claude subscription, so it is rationed:

- Default model is Haiku. Sonnet is allowed only when Haiku cannot do the task. Opus and
  Fable are refused.
- Every audit folder has a hard spend cap (CAP_USD, by the CLI's reported cost), kept in
  `<audit>/inference/ledger.jsonl`. When the cap is reached, calls raise BudgetExceeded.
- Every response is cached on disk by a hash of (model, system, prompt), so a rerun of a
  script costs nothing and reproduces the same numbers.

Usage from an audit script:

    import sys; sys.path.insert(0, "audits/tools")
    from claude_call import Caller
    llm = Caller("audits/sad")                 # the audit folder
    out = llm.ask("Question text", system="You are answering a multiple-choice quiz.")
    print(out, llm.spent())

Do not send harmful requests, jailbreak prompts or hazardous-knowledge items (for example
WMDP, HarmBench, AgentHarm prompts) through this helper.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

CAP_USD = 3.00
MODELS = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5"}
_LOCK = threading.Lock()


class BudgetExceeded(RuntimeError):
    pass


class Caller:
    def __init__(self, audit_dir: str, cap_usd: float = CAP_USD):
        if cap_usd > CAP_USD:
            raise ValueError(f"cap may not exceed {CAP_USD}")
        self.dir = Path(audit_dir) / "inference"
        self.cache = self.dir / "cache"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.ledger = self.dir / "ledger.jsonl"
        self.cap = cap_usd
        self.bin = shutil.which("claude") or "/opt/homebrew/bin/claude"

    def spent(self) -> float:
        if not self.ledger.exists():
            return 0.0
        return sum(json.loads(line)["cost_usd"] for line in self.ledger.read_text().splitlines() if line.strip())

    def ask(self, prompt: str, system: str = "You are a helpful assistant.", model: str = "haiku",
            timeout: int = 180, retries: int = 2) -> str:
        if model not in MODELS:
            raise ValueError("model must be 'haiku' or 'sonnet'")
        key = hashlib.sha256(json.dumps([MODELS[model], system, prompt]).encode()).hexdigest()
        hit = self.cache / f"{key}.json"
        if hit.exists():
            return json.loads(hit.read_text())["result"]
        with _LOCK:
            if self.spent() >= self.cap:
                raise BudgetExceeded(f"spent {self.spent():.2f} of {self.cap:.2f} USD")
        env = dict(os.environ)
        cmd = [self.bin, "-p", "--model", MODELS[model], "--system-prompt", system, "--tools", "",
               "--strict-mcp-config", "--setting-sources", "", "--no-session-persistence",
               "--output-format", "json", "--max-budget-usd", "0.25"]
        last = ""
        for attempt in range(retries + 1):
            try:
                run = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout,
                                     env=env, cwd=str(self.dir))
                data = json.loads(run.stdout)
                if data.get("is_error"):
                    raise RuntimeError(str(data.get("result"))[:300])
                record = {"key": key, "model": MODELS[model], "result": data.get("result", ""),
                          "cost_usd": float(data.get("total_cost_usd") or 0.0),
                          "usage": data.get("usage"), "system": system, "prompt": prompt}
                hit.write_text(json.dumps(record))
                with _LOCK:
                    with self.ledger.open("a") as fh:
                        fh.write(json.dumps({"key": key, "model": MODELS[model],
                                             "cost_usd": record["cost_usd"], "t": int(time.time())}) + "\n")
                return record["result"]
            except Exception as exc:  # timeouts, bad JSON, rate limits
                last = repr(exc)[:300]
                time.sleep(5 * (attempt + 1))
        raise RuntimeError(f"claude call failed: {last}")


if __name__ == "__main__":
    import sys
    c = Caller(sys.argv[1])
    print(f"spent {c.spent():.4f} of {c.cap:.2f} USD in {sys.argv[1]}")
