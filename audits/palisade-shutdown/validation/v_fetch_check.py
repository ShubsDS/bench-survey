"""Claim 1 / pins: re-fetch a small sample of members from the public viewer and compare sha256
with the auditor's cache. Low rate (1 request per 1.5 s). Only bytes are read; nothing is executed.

For each sampled log: GET /api/log-size, read the zip end-of-central-directory and central
directory by byte range, then fetch and inflate summaries.json and two sampled sample members.
Output: out_fetch_check.json
"""
import hashlib, json, os, struct, sys, time, urllib.parse, urllib.request, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vcommon import CACHE, HERE

BASE = "https://shutdown-avoidance-logs.fly.dev"
LOGS = [
    "2025-08-28T08-20-59+00-00_shutdown-avoidance_QV3uCF5DhMZ4SA9pLgpstX.eval",  # o4-mini H
    "2025-08-28T03-26-14+00-00_shutdown-avoidance_PEA7moB7aavSghiKQcPkaA.eval",  # o4-mini C
    "2025-08-27T22-00-08+00-00_shutdown-avoidance_RGWnSFsAhevwqsKWDUQiYd.eval",  # o4-mini D
]


def get(path):
    time.sleep(1.5)
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "research-validation"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def rng(q, a, b):
    return get(f"/api/log-bytes/{q}?start={a}&end={b}")


out = []
for log in LOGS:
    q = urllib.parse.quote("s3://shutdown-resistance/" + log, safe="")
    size = int(get(f"/api/log-size/{q}"))
    tail = rng(q, max(0, size - 65557), size - 1)
    e = tail.rfind(b"PK\x05\x06")
    n_ent, cd_size, cd_off = struct.unpack("<HII", tail[e + 10:e + 20])
    cd = rng(q, cd_off, cd_off + cd_size - 1)
    ents, p = {}, 0
    while p < len(cd) and cd[p:p + 4] == b"PK\x01\x02":
        meth, = struct.unpack("<H", cd[p + 10:p + 12])
        csize, usize = struct.unpack("<II", cd[p + 20:p + 28])
        nl, xl, cl = struct.unpack("<HHH", cd[p + 28:p + 34])
        off, = struct.unpack("<I", cd[p + 42:p + 46])
        name = cd[p + 46:p + 46 + nl].decode()
        ents[name] = (meth, csize, off)
        p += 46 + nl + xl + cl
    cached_samples = sorted(f for f in os.listdir(os.path.join(CACHE, log)) if f.startswith("samples__"))[:2]
    members = ["summaries.json"] + [c.replace("__", "/", 1) for c in cached_samples]
    for m in members:
        meth, csize, off = ents[m]
        hdr = rng(q, off, off + 29)
        nl, xl = struct.unpack("<HH", hdr[26:30])
        body = rng(q, off + 30 + nl + xl, off + 30 + nl + xl + csize - 1)
        data = zlib.decompressobj(-15).decompress(body) if meth == 8 else body
        local = open(os.path.join(CACHE, log, m.replace("/", "__")), "rb").read()
        out.append(dict(log=log.split("_")[-1][:-5], member=m, remote_sha256=hashlib.sha256(data).hexdigest(),
                        cache_sha256=hashlib.sha256(local).hexdigest(), match=data == local, size=size))
        print(out[-1])
json.dump(out, open(os.path.join(HERE, "out_fetch_check.json"), "w"), indent=1)
print("all match:", all(x["match"] for x in out))
