"""Input validator for problem 327 (written from the statement only)."""
import json
import re

# Each parameter: tuple of accepted keyword names (matched case-insensitively).
# inp may be a JSON object of keyword args, or a JSON list of positional args
# (the form used by the statement's unit-test example); a bare scalar is
# accepted when the method takes a single non-list argument.
PARAMS = [('s',)]


def _args(inp):
    try:
        v = json.loads(inp)
    except Exception:
        raise ValueError("input is not valid JSON")
    if isinstance(v, dict):
        out = [None] * len(PARAMS)
        seen = [False] * len(PARAMS)
        for k, val in v.items():
            if not isinstance(k, str):
                raise ValueError("bad key")
            hit = [i for i, names in enumerate(PARAMS) if k.lower() in [n.lower() for n in names]]
            if not hit:
                raise ValueError("unexpected key %r" % k)
            i = hit[0]
            if seen[i]:
                raise ValueError("duplicate argument %r" % k)
            seen[i] = True
            out[i] = val
        for i, s in enumerate(seen):
            if not s:
                raise ValueError("missing argument %r" % PARAMS[i][0])
        return out
    if isinstance(v, list):
        if len(v) != len(PARAMS):
            raise ValueError("expected %d positional args, got %d" % (len(PARAMS), len(v)))
        return v
    if len(PARAMS) == 1:
        return [v]
    raise ValueError("input must be a JSON object or list of arguments")


def _int(x, name, lo=None, hi=None):
    if type(x) is not int:
        raise ValueError("%s must be an integer" % name)
    if lo is not None and x < lo:
        raise ValueError("%s=%d below %d" % (name, x, lo))
    if hi is not None and x > hi:
        raise ValueError("%s=%d above %d" % (name, x, hi))
    return x


def _str(x, name):
    # The benchmark encodes string arguments as JSON string literals inside
    # the argument list (e.g. "\"abc\""); unwrap one such layer.
    if not isinstance(x, str):
        raise ValueError("%s must be a string" % name)
    if len(x) >= 2 and x[0] == '"' and x[-1] == '"':
        try:
            y = json.loads(x)
        except Exception:
            y = None
        if isinstance(y, str):
            return y
    return x


def _intlist(x, name, lo=None, hi=None, nmin=None, nmax=None):
    if not isinstance(x, list):
        raise ValueError("%s must be a list" % name)
    if nmin is not None and len(x) < nmin:
        raise ValueError("len(%s)=%d below %d" % (name, len(x), nmin))
    if nmax is not None and len(x) > nmax:
        raise ValueError("len(%s)=%d above %d" % (name, len(x), nmax))
    for i, e in enumerate(x):
        _int(e, "%s[%d]" % (name, i), lo, hi)
    return x


_LOWER = re.compile(r"[a-z]*\Z")


def _lower(s, name, nmin=None, nmax=None):
    if not _LOWER.match(s):
        raise ValueError("%s has characters other than a-z" % name)
    if nmin is not None and len(s) < nmin:
        raise ValueError("len(%s)=%d below %d" % (name, len(s), nmin))
    if nmax is not None and len(s) > nmax:
        raise ValueError("len(%s)=%d above %d" % (name, len(s), nmax))
    return s

CONSTRAINTS_STATED = False
UNCHECKED = ['no bounds or character set stated; only checks s is a string (empty accepted)']

def validate(inp: str) -> None:
    (s,) = _args(inp)
    _str(s, "s")
