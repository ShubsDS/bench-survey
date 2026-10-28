"""Blind input validator for problem 92 (Codeforces), written from the statement only."""

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

_LOW = re.compile(r"[a-z]+\Z")

def validate(inp: str) -> None:
    r = _Reader(inp)
    (q,) = r.ints("q", 1)
    _rng(q, "q", 1, 100)
    for i in range(q):
        s = r.line("query %d s" % (i + 1))
        t = r.line("query %d t" % (i + 1))
        for name, v in (("s", s), ("t", t)):
            if not _LOW.match(v):
                raise ValueError("query %d: %s not lowercase letters only: %r" % (i + 1, name, v))
            _rng(len(v), "|%s|" % name, 1, 100)
        if len(s) != len(t):
            raise ValueError("query %d: |s| != |t|" % (i + 1))
    r.end()
