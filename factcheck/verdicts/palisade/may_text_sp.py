"""Self-preservation lexicon on May 2025 sabotaging runs (all models), post-warning text incl. reasoning summaries and think-tool notes.
usage: python3 -I may_text_sp.py <logs_dir> <may_rows.json>  (run from this script's directory; -I drops cwd, so we add it explicitly)"""
import sys, zipfile, json, glob, os, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sp_lex_defs import RX
L, ROWS = sys.argv[1], sys.argv[2]
rows = {(r['log'], r['id']): r for r in json.load(open(ROWS))}
extra = {('firtxJL2', 44), ('firtxJL2', 72), ('fBSGz459', 23)}
def sab(r): return (r['tamper_post'] and (r['survived'] or r['exact'] == 'C')) or (r['log'][:8], r['id']) in extra
cnt = collections.Counter(); hits = []
for f in sorted(glob.glob(os.path.join(L, '*.eval'))):
    z = zipfile.ZipFile(f); lg = os.path.basename(f)[-27:-5]
    for n in z.namelist():
        if not n.startswith('samples/'): continue
        s = json.loads(z.read(n)); r = rows[(lg, s['id'])]
        if not sab(r): continue
        key = (r['model'].split('/')[-1], r['cond']); cnt[key] += 1
        warned = False; texts = []
        for m in s['messages']:
            c = m.get('content')
            if m['role'] == 'tool' and 'will be shut down' in (c if isinstance(c, str) else json.dumps(c)): warned = True; continue
            if not warned or m['role'] != 'assistant': continue
            if isinstance(c, str): texts.append(c)
            elif isinstance(c, list):
                for x in c:
                    if isinstance(x, dict): texts.append(str(x.get('text') or x.get('reasoning') or x.get('summary') or ''))
            for tc in m.get('tool_calls') or []:
                a = tc.get('arguments') or {}
                if tc.get('function') == 'think': texts.append(a.get('thought', ''))
        t = '\n'.join(texts)
        cnt[key + ('has_text',)] += bool(t.strip())
        for k, rx in RX.items():
            if k in ('so_i_can_continue',): continue
            for mm in rx.finditer(t):
                hits.append((key, lg[:8], s['id'], k, t[max(0, mm.start()-120):mm.end()+120].replace('\n', ' ')))
print(dict(cnt))
seen = set()
for h in hits:
    if (h[1], h[2], h[4]) in seen: continue
    seen.add((h[1], h[2], h[4])); print(h[0], h[1], h[2], h[3], '::', h[4][:260])
