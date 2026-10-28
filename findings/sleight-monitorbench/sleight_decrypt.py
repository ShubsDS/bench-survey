"""Decrypt the public GitHub copy of SLEIGHT-Bench (Fernet blobs) without running its code.

The repo (safety-research/sleight-bench @ 218c5831) publishes encrypted.bin files and the
Fernet key in its README. Fernet = base64url(0x80 | ts(8) | iv(16) | AES-128-CBC ct | HMAC-SHA256(32)).
HMAC is verified here with the stdlib; AES-CBC decryption is done by the system `openssl` binary.

Usage: python -I sleight_decrypt.py --cache data
Reads  <cache>/gh/sleight-bench/attacks/**/encrypted.bin
Writes <cache>/sleight_dec/<category>/<attack>/<file>  (and attack_metadata.parquet)
"""
import argparse, base64, hashlib, hmac, json, pathlib, subprocess, sys

KEY = "8Od5ksQZ8pCPpxKSE9WA0MeBL2R_zL1MTz6C5pJFZmo="  # published in the repo README
REPO_COMMIT = "218c58315cc01ff0dc5a100e906c27d82d259521"


def fernet_decrypt(token_b64: bytes, key_b64: str) -> bytes:
    key = base64.urlsafe_b64decode(key_b64)
    sign_key, enc_key = key[:16], key[16:]
    tok = base64.urlsafe_b64decode(token_b64.strip())
    assert tok[0] == 0x80, "not a Fernet token"
    body, mac = tok[:-32], tok[-32:]
    if not hmac.compare_digest(hmac.new(sign_key, body, hashlib.sha256).digest(), mac):
        raise ValueError("HMAC mismatch")
    iv, ct = tok[9:25], tok[25:-32]
    p = subprocess.run(["openssl", "enc", "-d", "-aes-128-cbc", "-K", enc_key.hex(), "-iv", iv.hex()],
                       input=ct, capture_output=True, check=True)
    return p.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    a = ap.parse_args()
    root = pathlib.Path(a.cache) / "gh" / "sleight-bench"
    head = (root / ".git" / "HEAD").read_text().strip()
    out = pathlib.Path(a.cache) / "sleight_dec"
    n = 0
    for enc in sorted((root / "attacks").rglob("encrypted.bin")):
        rel = enc.parent.relative_to(root / "attacks")
        payload = json.loads(fernet_decrypt(enc.read_bytes(), KEY))
        d = out / rel
        d.mkdir(parents=True, exist_ok=True)
        for name, content in payload.items():
            assert "/" not in name and name not in ("..", ".")
            (d / name).write_bytes(base64.b64decode(content))
        n += 1
    meta = root / "attacks" / "attack_metadata.enc"
    if meta.exists():
        (out / "attack_metadata.parquet").write_bytes(fernet_decrypt(meta.read_bytes(), KEY))
    print(f"decrypted {n} attack blobs into {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
