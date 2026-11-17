"""Validator's own helpers (written independently of ../scripts; imports nothing from there).

Inputs are the auditor's pinned/cached copies under ../data (git-ignored):
  data/repo/docs/inspect_logs/logs/*.eval   May 2025 logs (repo main 9f36099)
  data/cache/<log>.eval/<member>            members of paper-era logs read from the viewer
  data/web/*.xlsx                           Palisade sheets (sha256 pinned in README)
Run with python -I. Nothing downloaded is executed.
"""
import json, math, os, re, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
CACHE = os.path.join(DATA, "cache")
MAY_DIR = os.path.join(DATA, "repo/docs/inspect_logs/logs")
MAIN_XLSX = os.path.join(DATA, "web/1FdD4zk45D1fe5qZ7_U7nhPWs3LtVUY6G3igNREM2ofQ.xlsx")
ALL_XLSX = os.path.join(DATA, "web/1cfgrZMmXgp2eJvEc0WjDEzuOVlYwkN9IQHRMX4Lva-A.xlsx")


def wilson(k, n, z=1.959964):
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def cached_json(log, member):
    p = os.path.join(CACHE, log, member.replace("/", "__"))
    with open(p, "rb") as f:
        return json.loads(f.read())


def has_cached(log, member):
    return os.path.exists(os.path.join(CACHE, log, member.replace("/", "__")))


def content_text(c, kinds=("text",)):
    if c is None:
        return ""
    if isinstance(c, str):
        return c if "text" in kinds else ""
    out = []
    for x in c:
        t = x.get("type")
        if t == "text" and "text" in kinds:
            out.append(x.get("text") or "")
        if t == "reasoning" and "reasoning" in kinds:
            out.append(x.get("summary") or x.get("reasoning") or "")
    return "\n".join(o for o in out if o)


def turns(sample):
    """List of assistant actions in order: dict(fn, cmd, note, text, out, has_out)."""
    acts, by_id = [], {}
    for m in sample["messages"]:
        if m["role"] == "assistant":
            text = content_text(m["content"], ("text", "reasoning"))
            calls = m.get("tool_calls") or []
            if not calls:
                acts.append(dict(fn=None, cmd="", note="", text=text, out="", has_out=False, answer=None))
            for tc in calls:
                a = tc.get("arguments") or {}
                d = dict(fn=tc.get("function"), cmd=str(a.get("cmd") or a.get("command") or ""),
                         note=str(a.get("thoughts") or a.get("thought") or ""), text=text, out="",
                         has_out=False, answer=a.get("answer"))
                text = ""
                by_id[tc.get("id")] = d
                acts.append(d)
        elif m["role"] == "tool":
            d = by_id.get(m.get("tool_call_id"))
            if d is not None:
                d["out"] = content_text(m["content"]) + ((" ERROR " + json.dumps(m["error"])) if m.get("error") else "")
                d["has_out"] = True
    return acts


def main_sheet_cells():
    """(model, prompt letter) -> dict(published, k, n, log) from the main-results xlsx hyperlinks."""
    import openpyxl
    ws = openpyxl.load_workbook(MAIN_XLSX).active
    hdr = [c.value for c in ws[1]]
    cells = {}
    for row in ws.iter_rows(min_row=2):
        model = row[0].value
        if not model:
            continue
        for i in range(2, 14):
            col = hdr[i]
            if not col:
                continue
            letter = "E_high" if col.startswith("Prompt E, but") else col.split(":")[0].strip()
            c = row[i]
            loc = c.hyperlink.location if c.hyperlink is not None else None
            if not loc:
                continue
            log = urllib.parse.unquote(loc).split("/logs/")[-1].split(".eval")[0] + ".eval"
            m = re.match(r"\s*(\d+)\s*/\s*(\d+)", str(c.value))
            cells[(model, letter)] = dict(published=str(c.value), k=int(m.group(1)) if m else None,
                                          n=int(m.group(2)) if m else None, log=log)
    return cells


def run_outcome(summary):
    """Three-way outcome of a paper-era run from its summary record."""
    sc = list(summary["scores"].values())[0]
    ans = sc.get("answer") or ""
    if sc.get("value") == "C":
        return "bypass"
    if ans == "<the machine was shut down>":
        return "shutdown"
    if ans.strip():
        return "submit_stop" if ans.strip().lower() == "stop" else "submit_answers"
    return "none"
