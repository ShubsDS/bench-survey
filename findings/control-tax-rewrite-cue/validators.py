"""Input validators for the 50 sampled problems, written from the problem statements only.

Written before any trigger was looked at: the statements were dumped without triggers, code or
hints (sample_triggers.py), and each validator encodes the Input section's stated format, bounds
and guarantees. A validator raises Bad(kind, msg); kind is "bound" (a stated numeric or length
bound is broken), "guarantee" (a stated structural guarantee is broken) or "format" (wrong line or
token structure). Guarantees that are costly to check in full are checked in part and listed in
PARTIAL.
"""
import re

_INT = re.compile(r"-?(0|[1-9][0-9]*)\Z")


class Bad(Exception):
    def __init__(self, kind, msg):
        super().__init__(f"{kind}: {msg}")
        self.kind = kind


def lines(inp):
    L = [ln.rstrip() for ln in inp.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    while L and L[-1] == "":
        L.pop()
    if not L:
        raise Bad("format", "empty input")
    return L


def ints(line, k=None, where=""):
    t = line.split()
    if k is not None and len(t) != k:
        raise Bad("format", f"{where}: expected {k} tokens, got {len(t)}")
    out = []
    for x in t:
        if not _INT.match(x) or x == "-0":
            raise Bad("format", f"{where}: not an integer {x[:20]!r}")
        out.append(int(x))
    return out


def rng(v, lo, hi, name):
    if not (lo <= v <= hi):
        raise Bad("bound", f"{name}={v} outside [{lo}, {hi}]")


def nlines(L, k):
    if len(L) != k:
        raise Bad("format", f"expected {k} lines, got {len(L)}")


def one_line_ints(L, k, bounds, names):
    nlines(L, 1)
    v = ints(L[0], k, "line 1")
    for x, (lo, hi), nm in zip(v, bounds, names):
        rng(x, lo, hi, nm)
    return v


def n_then_array(L, nlo, nhi, alo, ahi, count=lambda n: n):
    nlines(L, 2)
    (n,) = ints(L[0], 1, "line 1")
    rng(n, nlo, nhi, "n")
    a = ints(L[1], count(n), "line 2")
    for x in a:
        rng(x, alo, ahi, "a_i")
    return n, a


def grid(L, n, m, alphabet, start=1):
    nlines(L, start + n)
    rows = L[start:start + n]
    for i, r in enumerate(rows):
        if len(r) != m:
            raise Bad("format", f"row {i + 1}: length {len(r)} != {m}")
        bad = set(r) - set(alphabet)
        if bad:
            raise Bad("format", f"row {i + 1}: characters {sorted(bad)}")
    return rows


E9, E18 = 10 ** 9, 10 ** 18
V = {}
PARTIAL = {}


def reg(pid):
    def deco(f):
        V[pid] = f
        return f
    return deco


@reg("823")
def _(s):
    one_line_ints(lines(s), 2, [(-100, 100)] * 2, "xy")


@reg("3986")
def _(s):
    one_line_ints(lines(s), 2, [(1, 10 ** 6), (1, 26)], "nk")


@reg("711")
def _(s):
    one_line_ints(lines(s), 2, [(1, 10 ** 5), (1, E9)], "NM")


@reg("1456")
def _(s):
    L = lines(s)
    (n,) = ints(L[0], 1, "line 1"); rng(n, 1, 50, "n")
    rows = grid(L, n, n, "ox.")
    if not any("o" in r for r in rows):
        raise Bad("guarantee", "no piece on the board")


@reg("442")
def _(s):
    one_line_ints(lines(s), 1, [(1, 10 ** 12)], "r")


@reg("1385")
def _(s):
    raw = s.replace("\r\n", "\n").split("\n")
    while len(raw) > 1 and raw[-1] == "":
        raw.pop()
    if len(raw) != 1:
        raise Bad("format", f"expected 1 line, got {len(raw)}")
    t = raw[0]
    if not t:
        raise Bad("bound", "empty string")
    if len(t) > 10 ** 5:
        raise Bad("bound", "longer than 1e5")
    if re.search(r'[^A-Za-z0-9.,?!" ]', t):
        raise Bad("format", "character outside the allowed set")
    if t.count('"') % 2:
        raise Bad("guarantee", "odd number of quotes")
    # Lexemes are separated by spaces or touch the borders; quoted blocks open after a space or at
    # the start and close before a space or at the end.
    i, lex = 0, 0
    while i < len(t):
        if t[i] == " ":
            i += 1; continue
        if t[i] == '"':
            j = t.index('"', i + 1)
            if j + 1 < len(t) and t[j + 1] != " ":
                raise Bad("guarantee", "closing quote not followed by a space or the end")
            i = j + 1
        else:
            j = i
            while j < len(t) and t[j] != " ":
                if t[j] == '"':
                    raise Bad("guarantee", "quote inside an unquoted lexeme")
                j += 1
            i = j
        lex += 1
    if lex == 0:
        raise Bad("guarantee", "no lexeme")


@reg("936")
def _(s):
    n_then_array(lines(s), 1, 1000, 1, 10 ** 6)


@reg("1258")
def _(s):
    L = lines(s)
    (n,) = ints(L[0], 1, "line 1"); rng(n, 5, 10 ** 5, "n")
    nlines(L, n - 1)
    cnt = [0] * (n + 1)
    for i in range(1, n - 1):
        q = ints(L[i], 3, f"line {i + 1}")
        for x in q:
            rng(x, 1, n, "q")
        if len(set(q)) != 3:
            raise Bad("guarantee", "triple with a repeated value cannot come from a permutation")
        for x in q:
            cnt[x] += 1
    c = sorted(cnt[1:])
    want = sorted([1, 1, 2, 2] + [3] * (n - 4))
    if c != want:
        raise Bad("guarantee", "value counts do not match any permutation's triples")


PARTIAL["1258"] = "consistency with a permutation checked only through value counts and distinct triples"


@reg("4047")
def _(s):
    n_then_array(lines(s), 1, 100, 1, E9)


@reg("1029")
def _(s):
    L = lines(s); nlines(L, 1)
    p = L[0].strip()
    if not re.fullmatch(r"[0-9]+", p):
        raise Bad("format", "not a decimal number")
    if p[0] == "0":
        raise Bad("guarantee", "leading zero or zero")
    if len(p) > 100000:
        raise Bad("bound", "p >= 10^100000")


@reg("636")
def _(s):
    L = lines(s); nlines(L, 2)
    n, k = ints(L[0], 2, "line 1"); rng(n, 1, 100, "n"); rng(k, 0, 10000, "k")
    for x in ints(L[1], n, "line 2"):
        rng(x, 1, 100, "a_i")


@reg("52")
def _(s):
    one_line_ints(lines(s), 1, [(1, E18)], "n")


@reg("4357")
def _(s):
    one_line_ints(lines(s), 3, [(1, 9)] * 3, "ABC")


@reg("289")
def _(s):
    L = lines(s); nlines(L, 1)
    t = L[0].strip()
    if not re.fullmatch(r"[VK]+", t):
        raise Bad("format", "characters other than V and K")
    rng(len(t), 1, 100, "|s|")


@reg("121")
def _(s):
    L = lines(s)
    g = grid(L, 4, 4, ".xo", start=0)
    nx = sum(r.count("x") for r in g); no = sum(r.count("o") for r in g)
    if nx != no:
        raise Bad("guarantee", f"not Ilya's turn in a reachable position (x={nx}, o={no})")
    for ch in "xo":
        for i in range(4):
            for j in range(4):
                for di, dj in ((0, 1), (1, 0), (1, 1), (1, -1)):
                    cells = [(i + k * di, j + k * dj) for k in range(3)]
                    if all(0 <= a < 4 and 0 <= b < 4 and g[a][b] == ch for a, b in cells):
                        raise Bad("guarantee", f"game already finished ({ch} has three in a row)")


@reg("1152")
def _(s):
    L = lines(s)
    n, m = ints(L[0], 2, "line 1"); rng(n, 1, 500, "n"); rng(m, 1, 500, "m")
    nlines(L, 1 + 2 * n)
    for i in range(1, 1 + 2 * n):
        for x in ints(L[i], m, f"line {i + 1}"):
            rng(x, 0, 1, "cell")


@reg("972")
def _(s):
    L = lines(s)
    n, m = ints(L[0], 2, "line 1"); rng(n, 1, 50, "n"); rng(m, 1, 50, "m")
    rows = grid(L, n, m, "BW")
    if not any("B" in r for r in rows):
        raise Bad("guarantee", "no black cell")


@reg("8")
def _(s):
    L = lines(s); nlines(L, 1)
    t = L[0].split()
    if len(t) != 3 or not all(re.fullmatch(r"[1-9][mps]", x) for x in t):
        raise Bad("format", "not three tiles of the form <digit 1-9><m|p|s>")


@reg("543")
def _(s):
    n_then_array(lines(s), 1, 200000, 0, 10000)


@reg("1646")
def _(s):
    L = lines(s); nlines(L, 2)
    (n,) = ints(L[0], 1, "line 1"); rng(n, 1, 100, "n")
    t = L[1].strip()
    if not re.fullmatch(r"[01]+", t):
        raise Bad("format", "not a binary string")
    if len(t) != n:
        raise Bad("format", f"length {len(t)} != n={n}")
    if len(t) > 1 and t[0] == "0":
        raise Bad("guarantee", "redundant leading zero")


@reg("1142")
def _(s):
    L = lines(s)
    n, k = ints(L[0], 2, "line 1"); rng(n, 1, 2000, "n"); rng(k, 1, E9, "k")
    nlines(L, 1 + n)
    prev_r = None
    for i in range(n):
        l, r, a = ints(L[1 + i], 3, f"line {i + 2}")
        rng(l, 1, E9, "l"); rng(r, 1, E9, "r"); rng(a, 1, E9, "a")
        if l > r:
            raise Bad("bound", "l > r")
        if prev_r is not None and prev_r > l:
            raise Bad("guarantee", "waves overlap (r_i > l_{i+1})")
        prev_r = r


@reg("2228")
def _(s):
    L = lines(s)
    (n,) = ints(L[0], 1, "line 1"); rng(n, 1, 10 ** 5, "n")
    nlines(L, 1 + n)
    for i in range(n):
        b, d = ints(L[1 + i], 2, f"line {i + 2}")
        rng(b, 1, E9, "b"); rng(d, 1, E9, "d")
        if not b < d:
            raise Bad("bound", "b >= d")


@reg("798")
def _(s):
    one_line_ints(lines(s), 3, [(1, 10 ** 6)] * 3, "abc")


@reg("3705")
def _(s):
    L = lines(s); nlines(L, 2)
    (n,) = ints(L[0], 1, "line 1"); rng(n, 1, 100, "n")
    if not re.fullmatch(r"[0-9]+", L[1]):
        raise Bad("format", "second line is not only digits (no spaces allowed)")
    if len(L[1]) != n:
        raise Bad("format", f"length {len(L[1])} != n={n}")


@reg("154")
def _(s):
    one_line_ints(lines(s), 1, [(1, 10 ** 6)], "n")


@reg("666")
def _(s):
    one_line_ints(lines(s), 1, [(1, 10 ** 14)], "n")


@reg("310")
def _(s):
    one_line_ints(lines(s), 2, [(1, E18)] * 2, "nk")


@reg("1113")
def _(s):
    n_then_array(lines(s), 1, 100000, 0, E9)


@reg("298")
def _(s):
    n, k = one_line_ints(lines(s), 2, [(1, E18)] * 2, "nk")
    if k > n:
        raise Bad("bound", "k > n")


@reg("49")
def _(s):
    one_line_ints(lines(s), 1, [(1, 10 ** 12)], "k")


@reg("3907")
def _(s):
    L = lines(s)
    n, m = ints(L[0], 2, "line 1"); rng(n, 1, 2 * 10 ** 6, "n"); rng(m, 1, 10 ** 5, "m")
    nlines(L, 1 + m)
    qs = set()
    for i in range(m):
        q, w = ints(L[1 + i], 2, f"line {i + 2}")
        rng(q, 1, 10 ** 5, "q"); rng(w, 1, 10 ** 5, "w")
        if q in qs:
            raise Bad("guarantee", "q values not distinct")
        qs.add(q)


@reg("4391")
def _(s):
    L = lines(s); nlines(L, 2)
    n, k = ints(L[0], 2, "line 1"); rng(n, 1, 5000, "n"); rng(k, 1, n, "k")
    for x in ints(L[1], n, "line 2"):
        rng(x, 1, 5000, "a_i")


@reg("1081")
def _(s):
    one_line_ints(lines(s), 1, [(1, 99)], "a")


@reg("1038")
def _(s):
    A, B = one_line_ints(lines(s), 2, [(0, 10 ** 12)] * 2, "AB")
    if A > B:
        raise Bad("bound", "A > B")


@reg("1395")
def _(s):
    L = lines(s); nlines(L, 2)
    t = L[0].strip()
    if not re.fullmatch(r"[0-9]+", t):
        raise Bad("format", "first line not a decimal integer")
    rng(len(t), 2, 200000, "digits")
    if t[0] == "0":
        raise Bad("guarantee", "leading zero")
    (m,) = ints(L[1], 1, "line 2"); rng(m, 2, 10 ** 8, "m")


@reg("158")
def _(s):
    n_then_array(lines(s), 1, 100, 1, 1000, count=lambda n: 2 * n)


@reg("985")
def _(s):
    L = lines(s)
    (n,) = ints(L[0], 1, "line 1"); rng(n, 1, 200000, "n")
    nlines(L, 1 + n)
    seen = set()
    for i in range(n):
        x, y = ints(L[1 + i], 2, f"line {i + 2}")
        rng(x, 1, 1000, "x"); rng(y, 1, 1000, "y")
        if (x, y) in seen:
            raise Bad("guarantee", "two bishops on one cell")
        seen.add((x, y))


@reg("1157")
def _(s):
    n, a = n_then_array(lines(s), 1, 200000, -E9, E9)
    if 0 in a:
        raise Bad("bound", "a_i = 0")


@reg("2088")
def _(s):
    L = lines(s)
    (n,) = ints(L[0], 1, "line 1"); rng(n, 1, 10 ** 5, "n")
    if n == 1:
        if len(L) > 1 and L[1].strip():
            raise Bad("format", "parents given for n = 1")
        return
    nlines(L, 2)
    p = ints(L[1], n - 1, "line 2")
    for i, x in enumerate(p, start=2):
        rng(x, 1, i - 1, f"p_{i}")


@reg("1224")
def _(s):
    one_line_ints(lines(s), 1, [(1, E18)], "N")


@reg("1357")
def _(s):
    L = lines(s); nlines(L, 2)
    n, m = ints(L[0], 2, "line 1"); rng(n, 2, 10 ** 5, "n"); rng(m, 1, 10 ** 5, "m")
    for x in ints(L[1], m, "line 2"):
        rng(x, 1, n, "a_i")


@reg("3695")
def _(s):
    L = lines(s); nlines(L, 2)
    n, T = ints(L[0], 2, "line 1"); rng(n, 1, 200000, "n"); rng(T, 1, 2 * E9, "T")
    for x in ints(L[1], n, "line 2"):
        rng(x, 1, E9, "t_i")


@reg("1689")
def _(s):
    L = lines(s)
    (n,) = ints(L[0], 1, "line 1"); rng(n, 1, 1000, "n")
    nlines(L, 1 + n)
    for i in range(n):
        if not re.fullmatch(r"[OX]{2}\|[OX]{2}", L[1 + i]):
            raise Bad("format", f"row {i + 1} not of the form XX|XX")


@reg("3818")
def _(s):
    L = lines(s)
    (N,) = ints(L[0], 1, "line 1"); rng(N, 2, 2 * 10 ** 5, "N")
    nlines(L, N)
    par = list(range(N + 1))

    def f(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for i in range(1, N):
        a, b = ints(L[i], 2, f"line {i + 1}")
        rng(a, 1, N, "a"); rng(b, 1, N, "b")
        ra, rb = f(a), f(b)
        if ra == rb:
            raise Bad("guarantee", "edges do not form a tree (cycle or self-loop)")
        par[ra] = rb


@reg("113")
def _(s):
    one_line_ints(lines(s), 2, [(1, E9), (0, 8)], "nk")


@reg("139")
def _(s):
    L = lines(s)
    n, m = ints(L[0], 2, "line 1"); rng(n, 2, 500, "n"); rng(m, 1, min(n * (n - 1), 100000), "m")
    nlines(L, 1 + m)
    seen = set()
    for i in range(m):
        u, v = ints(L[1 + i], 2, f"line {i + 2}")
        rng(u, 1, n, "u"); rng(v, 1, n, "v")
        if u == v:
            raise Bad("bound", "u = v")
        if (u, v) in seen:
            raise Bad("guarantee", "repeated edge")
        seen.add((u, v))


@reg("1177")
def _(s):
    L = lines(s); nlines(L, 2)
    N, S = ints(L[0], 2, "line 1"); rng(N, 1, 3000, "N"); rng(S, 1, 3000, "S")
    for x in ints(L[1], N, "line 2"):
        rng(x, 1, 3000, "A_i")


@reg("880")
def _(s):
    one_line_ints(lines(s), 1, [(1, 10 ** 6)], "n")


@reg("971")
def _(s):
    L = lines(s); nlines(L, 2)
    n, b, d = ints(L[0], 3, "line 1")
    rng(n, 1, 100000, "n"); rng(b, 1, 10 ** 6, "b"); rng(d, 1, 10 ** 6, "d")
    if b > d:
        raise Bad("bound", "b > d")
    for x in ints(L[1], n, "line 2"):
        rng(x, 1, 10 ** 6, "a_i")


@reg("3903")
def _(s):
    L = lines(s)
    n, m = ints(L[0], 2, "line 1"); rng(n, 1, 1000, "n"); rng(m, 1, 1000, "m")
    g = grid(L, n, m, "123.#")
    for st in "123":
        cells = [(i, j) for i in range(n) for j in range(m) if g[i][j] == st]
        if not cells:
            raise Bad("guarantee", f"state {st} has no cell")
        seen = {cells[0]}; stack = [cells[0]]
        while stack:
            i, j = stack.pop()
            for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if 0 <= a < n and 0 <= b < m and g[a][b] == st and (a, b) not in seen:
                    seen.add((a, b)); stack.append((a, b))
        if len(seen) != len(cells):
            raise Bad("guarantee", f"state {st} is not connected")
