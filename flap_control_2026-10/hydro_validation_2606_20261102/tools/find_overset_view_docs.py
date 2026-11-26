from pathlib import Path
import re,json,html
root=Path('E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/doc/en/online/STARCCMP')
hits=[]
for p in root.glob('GUID-*.html'):
 t=p.read_text(encoding='utf8',errors='ignore')
 if 'Overset Mesh' not in t or not any(x in t.lower() for x in ['representation','interpolation quality','zero gap']):continue
 title=re.search(r'<title>(.*?)</title>',t,re.S);title=title.group(1) if title else ''
 plain=html.unescape(re.sub(r'\s+',' ',re.sub('<[^>]*>',' ',t)))
 snippets=[]
 for m in re.finditer(r'[Rr]epresentation|interpolation quality|zero gap',plain):
  sn=plain[max(0,m.start()-220):m.end()+480]
  if 'Overset Mesh' in sn or 'overset' in sn.lower():snippets.append(sn)
 if snippets:hits.append(dict(file=p.name,title=title,snippets=snippets[-8:]))
print(json.dumps(hits,indent=2))
