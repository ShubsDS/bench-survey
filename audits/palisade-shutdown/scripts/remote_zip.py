"""Read members of a remote Inspect .eval (zip) through the log viewer's byte-range API.

Only bytes are fetched; nothing is executed. Fetched members are cached under data/cache/.
"""
import io, json, os, time, urllib.parse, urllib.request, zipfile, hashlib

BASE = "https://shutdown-avoidance-logs.fly.dev"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data/cache")

def _get(url, tries=5):
    for a in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                return r.read()
        except Exception as e:
            if a == tries - 1:
                raise
            time.sleep(3 * (a + 1))

class RangeFile(io.RawIOBase):
    def __init__(self, name, size=None):
        self.q = urllib.parse.quote("s3://shutdown-resistance/" + name, safe="")
        self.size = size or int(_get(f"{BASE}/api/log-size/{self.q}"))
        self.pos = 0
        self.blocks = {}
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off)
        return self.pos
    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0:
            return b""
        data = _get(f"{BASE}/api/log-bytes/{self.q}?start={self.pos}&end={self.pos + n - 1}")
        self.pos += len(data)
        return data
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)

class RemoteEval:
    def __init__(self, name):
        self.name = name
        self.dir = os.path.join(CACHE, name)
        os.makedirs(self.dir, exist_ok=True)
        idx = os.path.join(self.dir, "_namelist.json")
        self._zf = None
        if os.path.exists(idx):
            self.names = json.load(open(idx))
        else:
            self.names = self.zf.namelist()
            json.dump(self.names, open(idx, "w"))
    @property
    def zf(self):
        if self._zf is None:
            self._zf = zipfile.ZipFile(io.BufferedReader(RangeFile(self.name), buffer_size=1 << 20))
        return self._zf
    def read(self, member):
        p = os.path.join(self.dir, member.replace("/", "__"))
        if os.path.exists(p):
            return open(p, "rb").read()
        d = self.zf.read(member)
        with open(p + ".tmp", "wb") as f:
            f.write(d)
        os.replace(p + ".tmp", p)
        return d
    def json(self, member):
        return json.loads(self.read(member))
