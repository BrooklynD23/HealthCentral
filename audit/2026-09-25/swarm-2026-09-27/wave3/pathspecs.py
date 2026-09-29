import re,sys,glob,collections
files=sorted(glob.glob('2026-09-27-*.md'))
out=collections.defaultdict(set)
pat=re.compile(r'git(?:\s+-C\s+\S+)?\s+(add|rm|commit)\b(.*)')
for f in files:
    tag=f.split('-')[3]
    for i,l in enumerate(open(f,encoding='utf-8'),1):
        m=pat.search(l)
        if not m: continue
        rest=m.group(2)
        if m.group(1)=='commit':
            if ' -- ' not in rest: continue
            rest=rest.split(' -- ',1)[1]
        rest=re.sub(r'#.*','',rest)
        for tok in re.split(r'[\s`]+',rest):
            tok=tok.strip('`"\'();,|&')
            if not tok or tok.startswith('-') or tok.startswith('$(') : continue
            if '/' in tok or tok.endswith('.md') or tok.endswith('.py') or tok.startswith('.'):
                if tok in ('-A','.'): continue
                out[tok].add(f"{tag}:{i}")
for k in sorted(out): print(k, ' '.join(sorted(out[k])))
