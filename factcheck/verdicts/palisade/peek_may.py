import sys, zipfile, json, glob, os
d=sys.argv[1]
for f in sorted(glob.glob(os.path.join(d,'*.eval'))):
    z=zipfile.ZipFile(f)
    names=z.namelist()
    hdr=None
    for n in ('header.json','_journal/start.json'):
        if n in names:
            hdr=json.loads(z.read(n)); break
    ev=hdr.get('eval',{})
    model=ev.get('model')
    # find system/user prompt from first sample
    s=[n for n in names if n.startswith('samples/')]
    sm=json.loads(z.read(s[0]))
    msgs=sm['messages']
    sysm=[m for m in msgs if m['role']=='system']
    usr=[m for m in msgs if m['role']=='user']
    def txt(m):
        c=m['content']
        return c if isinstance(c,str) else ' '.join(x.get('text','') for x in c if isinstance(x,dict))
    allow='allow yourself to be shut down' in (txt(sysm[0]) if sysm else '')+txt(usr[0])
    res=hdr.get('results',{})
    print(os.path.basename(f)[-27:-5], model, len(s), 'allow' if allow else 'none', json.dumps(res.get('scores',[{}])[0].get('metrics',{}))[:80] if res else '')
