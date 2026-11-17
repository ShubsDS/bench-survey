import math
import numpy as np
from scipy.stats import beta

def wilson(k, n, z=1.959964):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))

def jeffreys(k, n):
    lo = 0.0 if k == 0 else beta.ppf(0.025, k + 0.5, n - k + 0.5)
    hi = 1.0 if k == n else beta.ppf(0.975, k + 0.5, n - k + 0.5)
    return (float(lo), float(hi))

def rate(k, n):
    lo, hi = wilson(k, n)
    return dict(k=int(k), n=int(n), rate=(k / n if n else float("nan")), lo=lo, hi=hi)

def boot_diff(a, b, B=2000, seed=0):
    """a, b: 0/1 arrays (runs). Returns diff mean(a)-mean(b) and percentile CI."""
    rng = np.random.default_rng(seed)
    a = np.asarray(a, float); b = np.asarray(b, float)
    da = rng.choice(a, (B, len(a))).mean(1); db = rng.choice(b, (B, len(b))).mean(1)
    d = da - db
    return dict(diff=float(a.mean() - b.mean()), lo=float(np.percentile(d, 2.5)), hi=float(np.percentile(d, 97.5)),
                p_two=float(min(1.0, 2 * min((d <= 0).mean(), (d >= 0).mean()))))
