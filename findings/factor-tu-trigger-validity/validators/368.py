"""Blind input validator for problem 368 (LeetCode), written from the statement only."""

import json

# Shared helpers (LeetCode). The argument JSON may be an object of keyword
# arguments or a list of positional arguments (the form the unit-test examples
# use). String arguments may arrive JSON-encoded a second time ("\"abc\""),
# as in the examples; those are decoded once.

def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)

def _args(inp, names):
    try:
        obj = json.loads(inp)
    except Exception as e:
        raise ValueError("not valid JSON: %s" % e)
    if isinstance(obj, dict):
        keys = list(obj)
        if set(keys) == set(names):
            return [obj[n] for n in names]
        if len(keys) == len(names):
            # parameter names differ from the statement's; map by position
            return [obj[k] for k in keys]
        raise ValueError("expected arguments %s, got keys %s" % (names, keys))
    if isinstance(obj, list):
        if len(obj) != len(names):
            raise ValueError("expected %d positional arguments, got %d" % (len(names), len(obj)))
        return obj
    raise ValueError("arguments must be a JSON object or list")

def _str(x, what):
    if not isinstance(x, str):
        raise ValueError("%s must be a string" % what)
    if len(x) >= 2 and x[0] == '"' and x[-1] == '"':
        try:
            y = json.loads(x)
        except Exception:
            y = None
        if isinstance(y, str):
            return y
    return x

def _int(x, what, lo=None, hi=None):
    if not _is_int(x):
        raise ValueError("%s must be an integer" % what)
    if lo is not None and x < lo:
        raise ValueError("%s=%d below %d" % (what, x, lo))
    if hi is not None and x > hi:
        raise ValueError("%s=%d above %d" % (what, x, hi))
    return x

def _list(x, what, lmin=None, lmax=None):
    if not isinstance(x, list):
        raise ValueError("%s must be a list" % what)
    if lmin is not None and len(x) < lmin:
        raise ValueError("len(%s)=%d below %d" % (what, len(x), lmin))
    if lmax is not None and len(x) > lmax:
        raise ValueError("len(%s)=%d above %d" % (what, len(x), lmax))
    return x

def _intlist(x, what, lmin=None, lmax=None, lo=None, hi=None):
    _list(x, what, lmin, lmax)
    for i, v in enumerate(x):
        _int(v, "%s[%d]" % (what, i), lo, hi)
    return x

def _charset(s, what, allowed):
    for c in s:
        if c not in allowed:
            raise ValueError("%s contains disallowed character %r" % (what, c))

LOWER = set("abcdefghijklmnopqrstuvwxyz")

CONSTRAINTS_STATED = True
UNCHECKED = []
PARAM_NAMES = ['satisfaction']

def validate(inp: str) -> None:
    (s,) = _args(inp, ["satisfaction"])
    _intlist(s, "satisfaction", 1, 500, -1000, 1000)
