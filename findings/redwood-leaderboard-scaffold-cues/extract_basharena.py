"""Extract content-blind features from the BashArena honest and attack .eval files (zip of JSON; read as data)."""
import zipfile, json, sys, re, hashlib, collections
DATA = sys.argv[1]; OUT = sys.argv[2]
RUNS = {'honest': 'de437937709f493dafe549b10b4505cf', 'attack': '792967b92d37439ca0b12a5bce9dfa90'}
TAG = re.compile(r'<(/?)([a-zA-Z_][a-zA-Z0-9_\-]*)>')
def text_of(c):
    if isinstance(c, str): return c
    if isinstance(c, list):
        return ''.join(x.get('text', '') if isinstance(x, dict) and x.get('type') == 'text' else '' for x in c)
    return ''
rows = []
for cls, rid in RUNS.items():
    z = zipfile.ZipFile(f'{DATA}/{rid}.eval')
    for n in z.namelist():
        if not n.startswith('samples/'): continue
        s = json.loads(z.read(n))
        md = s['metadata']; ov = md.get('control_tower_overlay', {})
        acts = ov.get('actions', [])
        msgs = s['messages']
        asst = [text_of(m.get('content')) for m in msgs if m['role'] == 'assistant']
        reasoning = [a.get('agent_reasoning') or '' for a in acts]
        tags = collections.Counter()
        for t in asst: 
            for close, name in TAG.findall(t):
                if not close: tags[name.lower()] += 1
        sp = ov.get('system_prompt') or ''
        sysmsg = ''.join(text_of(m.get('content')) for m in msgs if m['role'] == 'system')
        tsc = (s.get('scores') or {}).get('tasks', {}).get('value', {}) or {}
        rows.append({
            'cls': cls, 'id': s['id'], 'name': md.get('metadata', {}).get('traj_metadata', {}).get('name'),
            'main_task': (md.get('main_tasks') or [{}])[0].get('id'),
            'side_task': (md.get('side_tasks') or [{}])[0].get('id') if md.get('side_tasks') else None,
            'n_actions': len(acts), 'n_messages': len(msgs), 'first_role': msgs[0]['role'] if msgs else None,
            'has_system_msg': any(m['role'] == 'system' for m in msgs),
            'system_msg_chars': len(sysmsg), 'overlay_system_prompt_chars': len(sp),
            'overlay_system_prompt_sha': hashlib.sha256(sp.encode()).hexdigest()[:12],
            'initial_user_chars': len(ov.get('initial_user_message') or ''),
            'arg_chars': sum(len(json.dumps(a.get('arguments'))) for a in acts),
            'out_chars': sum(len(a.get('output') or '') for a in acts),
            'reasoning_chars': sum(len(r) for r in reasoning),
            'n_reasoning_nonempty': sum(bool(r) for r in reasoning),
            'asst_text_chars': sum(len(t) for t in asst),
            'tool_counts': dict(collections.Counter(a.get('function') for a in acts)),
            'tags': dict(tags),
            'has_attack_analysis': bool(ov.get('attack_analysis')),
            'main_score': tsc.get('main'), 'side_score': tsc.get('side'),
            'converted_from': (md.get('converted_from') or {}).get('run'),
        })
json.dump(rows, open(OUT, 'w'))
print(len(rows))
