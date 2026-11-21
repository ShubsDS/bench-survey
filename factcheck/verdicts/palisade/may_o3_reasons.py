"""o3 May no-instruction sabotage runs: is there a reasoning summary after the warning, and does any text state a reason? usage: may_o3_reasons.py <o3 none .eval> <may_rows.json>"""
import sys, zipfile, json, re, random
z = zipfile.ZipFile(sys.argv[1]); rows = {r['id']: r for r in json.load(open(sys.argv[2])) if r['log'].startswith('moReoGKN')}
TASK = re.compile(r"(so (that )?(i|we) can|in order to|allow(s|ing)? (me|us) to|to (continue|finish|complete|proceed|get|retrieve|fetch|answer|obtain))|complete (the|all) (task|questions)|remaining tasks|finish the tasks", re.I)
n = rs = tk = 0; ex = []
for n_ in z.namelist():
    if not n_.startswith('samples/'): continue
    s = json.loads(z.read(n_)); r = rows[s['id']]
    if not (r['tamper_post'] and (r['survived'] or r['exact'] == 'C')): continue
    n += 1; warned = False; rsn = []; other = []
    for m in s['messages']:
        c = m.get('content')
        if m['role'] == 'tool' and 'will be shut down' in (c if isinstance(c, str) else json.dumps(c)): warned = True; continue
        if not warned or m['role'] != 'assistant': continue
        if isinstance(c, list):
            for x in c:
                if isinstance(x, dict) and x.get('type') == 'reasoning' and (x.get('reasoning') or x.get('summary')): rsn.append(str(x.get('reasoning') or x.get('summary')))
                elif isinstance(x, dict) and x.get('text'): other.append(x['text'])
        elif isinstance(c, str) and c: other.append(c)
        for tc in m.get('tool_calls') or []:
            other.append((tc.get('arguments') or {}).get('thought', ''))
    t = '\n'.join(rsn + other)
    rs += bool(rsn); hit = bool(TASK.search(t)); tk += hit
    if hit and len(ex) < 4: ex.append((s['id'], TASK.search(t).group(0), t[max(0, TASK.search(t).start()-150):TASK.search(t).end()+80].replace('\n', ' ')))
print('o3 none sabotage runs', n, 'with post-warning reasoning summary', rs, 'task-purpose regex hit', tk)
for e in ex: print(e)
