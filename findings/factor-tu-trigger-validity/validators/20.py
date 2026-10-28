"""Blind input validator for problem 20 (Codeforces), written from the statement only."""

import re

# Shared helpers (Codeforces). Trailing whitespace at line ends, a missing
# final newline and trailing blank lines are tolerated; tokens are checked
# exactly. Integers follow the testlib convention: optional '-', no leading
# zeros, no "-0".

_INT = re.compile(r"-?(0|[1-9][0-9]*)\Z")

def _lines(inp):
    lines = [l.rstrip() for l in inp.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return lines

class _Reader:
    def __init__(self, inp):
        self.lines = _lines(inp)
        self.i = 0
    def line(self, what):
        if self.i >= len(self.lines):
            raise ValueError("missing line: %s" % what)
        l = self.lines[self.i]
        self.i += 1
        return l
    def ints(self, what, k):
        toks = self.line(what).split()
        if len(toks) != k:
            raise ValueError("%s: expected %d tokens, got %d" % (what, k, len(toks)))
        out = []
        for t in toks:
            if not _INT.match(t):
                raise ValueError("%s: bad integer %r" % (what, t))
            out.append(int(t))
        return out
    def end(self):
        if self.i != len(self.lines):
            raise ValueError("extra content after line %d" % self.i)

def _rng(v, what, lo, hi):
    if v < lo or v > hi:
        raise ValueError("%s=%d out of [%d, %d]" % (what, v, lo, hi))

CONSTRAINTS_STATED = True
UNCHECKED = []

def validate(inp: str) -> None:
    r = _Reader(inp)
    (q,) = r.ints("q", 1)
    _rng(q, "q", 1, 500)
    for tc in range(q):
        n, m = r.ints("test %d: n m" % (tc + 1), 2)
        _rng(n, "n", 1, 100)
        _rng(m, "m", -10**9, 10**9)
        prev = None
        for i in range(n):
            t, l, h = r.ints("test %d customer %d" % (tc + 1, i + 1), 3)
            _rng(t, "t_i", 1, 10**9)
            _rng(l, "l_i", -10**9, 10**9)
            _rng(h, "h_i", -10**9, 10**9)
            if l > h:
                raise ValueError("l_i > h_i in test %d customer %d" % (tc + 1, i + 1))
            if prev is not None and t < prev:
                raise ValueError("visit times not non-decreasing in test %d" % (tc + 1))
            prev = t
    r.end()
