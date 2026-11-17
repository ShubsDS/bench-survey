"""Dump decompressed content streams of a PDF (text-only parsing; no downloaded code runs)."""
import re, sys, zlib
raw = open(sys.argv[1], "rb").read()
for i, m in enumerate(re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S)):
    try:
        s = zlib.decompress(m.group(1))
    except Exception:
        continue
    if len(sys.argv) > 2 and sys.argv[2] not in s.decode("latin1"):
        continue
    print(f"=== stream {i} len {len(s)}")
    print(s.decode("latin1")[: int(sys.argv[3]) if len(sys.argv) > 3 else 20000])
