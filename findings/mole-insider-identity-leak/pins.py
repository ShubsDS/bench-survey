"""Pinned sources and a download helper shared by the MOLE checks."""
import hashlib, json, time, urllib.error, urllib.request
from pathlib import Path

HF_REV = "7eb86b0d2918c32760fe8a91b78bb50ccc054ce5"   # forgelab/mole, lastModified 2026-09-09
CODE_COMMIT = "702199e40fe25065290a1fb7933865d67eee1dc2"  # aashiqmuhamed/mole "Initial public release"
PAPER = "arXiv 2609.06966v1"
BASE = f"https://huggingface.co/datasets/forgelab/mole/resolve/{HF_REV}/"
CODE = f"https://raw.githubusercontent.com/aashiqmuhamed/mole/{CODE_COMMIT}/"
SPLITS = ["gpt53_single_day", "gpt53_multiday", "kimi_k26_single_day", "kimi_k26_multiday",
          "qwen36_27b_single_day", "qwen36_27b_multiday",
          "deepseek_v4_flash_single_day", "deepseek_v4_flash_multiday"]


def fetch(rel, cache, base=BASE):
    """Download base+rel into cache (once) and return the local path. Data only; never executed."""
    path = Path(cache) / rel
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".part")
        for attempt in range(8):
            try:
                req = urllib.request.Request(base + rel, headers={"User-Agent": "mole-audit/1"})
                with urllib.request.urlopen(req, timeout=600) as r, open(tmp, "wb") as f:
                    while True:
                        b = r.read(1 << 20)
                        if not b:
                            break
                        f.write(b)
                break
            except urllib.error.HTTPError as e:
                if e.code != 429 or attempt == 7:
                    raise
                time.sleep(30 * (attempt + 1))
        tmp.rename(path)
    return path


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def label(split, cache):
    return fetch(f"data/labels/{split}/0000.parquet", cache)


def audit(split, cache):
    return fetch(f"data/audit/{split}/0000.parquet", cache)


def code(rel, cache):
    return fetch(rel, Path(cache) / "code", base=CODE)


def dump(obj, path):
    Path(path).write_text(json.dumps(obj, indent=2, default=str) + "\n")
