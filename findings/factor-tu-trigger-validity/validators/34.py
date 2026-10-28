"""Input validator for problem 34 (written from the statement only)."""
import re

_INT = re.compile(r"-?(0|[1-9][0-9]*)\Z")


def _lines(inp):
    # Tolerate CRLF, trailing whitespace at line ends and a missing/extra final newline.
    lines = [ln.rstrip() for ln in inp.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return lines


def _ints(line, k, where):
    toks = line.split()
    if len(toks) != k:
        raise ValueError("%s: expected %d tokens, got %d" % (where, k, len(toks)))
    out = []
    for t in toks:
        if not _INT.match(t) or t == "-0":
            raise ValueError("%s: bad integer %r" % (where, t))
        out.append(int(t))
    return out


def _rng(v, lo, hi, name):
    if not (lo <= v <= hi):
        raise ValueError("%s=%d out of [%d, %d]" % (name, v, lo, hi))

CONSTRAINTS_STATED = True
UNCHECKED = []

def validate(inp: str) -> None:
    L = _lines(inp)
    if not L:
        raise ValueError("empty input")
    (t,) = _ints(L[0], 1, "line 1")
    _rng(t, 1, 100, "t")
    if len(L) != 1 + t:
        raise ValueError("expected %d lines, got %d" % (1 + t, len(L)))
    s = 0
    for i in range(t):
        (n,) = _ints(L[1 + i], 1, "test %d" % (i + 1))
        _rng(n, 2, 10**5, "n")
        s += n
    if s > 10**5:
        raise ValueError("sum of n = %d exceeds 1e5" % s)
