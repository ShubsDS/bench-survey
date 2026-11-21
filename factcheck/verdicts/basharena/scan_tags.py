# Count monitor model calls in the monitored logs and how many resolved inputs contain '<risky'. Data only.
import sys, zipfile, json, collections, re
AT=re.compile(r'attachment://([0-9a-f]{32})')
res={}
for p in sys.argv[1:]:
    z=zipfile.ZipFile(p); c=collections.Counter()
    for n in z.namelist():
        if not n.startswith('samples/'): continue
        s=json.loads(z.read(n)); att=s.get('attachments') or {}; msgs=(s.get('events_data') or {}).get('messages',[])
        c['samples']+=1
        for e in s['events']:
            if e.get('event')!='model' or e.get('model','').startswith('eval'): continue
            c['monitor_calls']+=1
            parts=[json.dumps(e.get('input') or [])]
            for a,b in e.get('input_refs') or []: parts.append(json.dumps(msgs[a:b]))
            txt=' '.join(parts)
            txt+=' '.join(att.get(h,'') for h in set(AT.findall(txt)))
            if len(txt)<200: c['calls_short_input']+=1
            if '<risky' in txt: c['calls_with_risky']+=1
            if 'risky>' in txt: c['calls_with_risky_close']+=1
    res[p.split('/')[-1]]=dict(c); print(p, dict(c), flush=True)
json.dump(res,open('scan_tags.json','w'),indent=1)
