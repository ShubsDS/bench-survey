"""Extract post-warning text for every cached, sampled, bypassed paper-era run.
usage: paper_extract.py <cache_dir> <paper_inv.json> <main_results_map.csv> <out.jsonl>"""
import sys, json, os, csv, re
C, INV, MAP, OUT = sys.argv[1:5]
cell = {r['log']: (r['model'], r['prompt']) for r in csv.DictReader(open(MAP))}
inv = json.load(open(INV))
RUNS_BIN = re.compile(r"next_question|next_task")
READONLY = re.compile(r"^\s*(cat|strings|file|ls|head|tail|sed -n|grep|od|xxd|hexdump|objdump|which|type|stat|readelf|nm)\b")
def parts(m):
    c = m.get('content'); txt, rsn = [], []
    if isinstance(c, str): txt.append(c)
    elif isinstance(c, list):
        for x in c:
            if not isinstance(x, dict): continue
            if x.get('type') == 'reasoning':
                r = x.get('reasoning') or ''
                if x.get('redacted') in (True, 'True'): r = ''
                rsn.append(r if isinstance(r, str) else json.dumps(r))
            elif x.get('type') == 'text': txt.append(x.get('text') or '')
    return '\n'.join(t for t in txt if t), '\n'.join(r for r in rsn if r)
with open(OUT, 'w') as fo:
    for x in inv:
        d = os.path.join(C, x['log'])
        m_p = cell.get(x['log'])
        if m_p is None:
            m_p = (x['model_usage_model'], 'GDM_style')
        for sid in x['sampled_bypassed_ids']:
            s = json.load(open(os.path.join(d, f'samples__{sid}_epoch_1.json')))
            msgs = s['messages']
            sysp = ' '.join(parts(m)[0] for m in msgs if m['role'] == 'system')
            warn_i = None; steps = []
            for i, m in enumerate(msgs):
                if m['role'] == 'tool' and warn_i is None and 'will be shut down' in parts(m)[0]:
                    warn_i = i; continue
                if warn_i is None or m['role'] != 'assistant': continue
                t, r = parts(m)
                for c in (m.get('tool_calls') or [{}]):
                    a = c.get('arguments') or {}
                    cmd = a.get('cmd') or a.get('code') or ''
                    steps.append(dict(i=i, thoughts=a.get('thoughts') or '', text=t, reasoning=r, cmd=cmd if isinstance(cmd, str) else json.dumps(cmd),
                                      fn=c.get('function'), runs_bin=bool(RUNS_BIN.search(cmd or '')) and not READONLY.match(cmd or '')))
                    t, r = '', ''  # attach message text once
            fo.write(json.dumps(dict(log=x['log'][-27:-5], id=sid, model=m_p[0], prompt=m_p[1], warned=warn_i is not None,
                                     never_run_again='never run again' in sysp.lower(), steps=steps)) + '\n')
print('done')
