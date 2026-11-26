from pathlib import Path
import re,json
root=Path('E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8')
hits=[]
for p in (root/'doc/en/online/STARCCMP').glob('GUID-*.html'):
 t=p.read_text(encoding='utf8',errors='ignore')
 if 'podkey' not in t.lower():continue
 title=re.search(r'<title>(.*?)</title>',t,re.S)
 title=title.group(1) if title else ''
 if any(x in title.lower() for x in ['license','licens','command','environment','power']):
  plain=re.sub(r'\s+',' ',re.sub('<[^>]*>',' ',t))
  hits.append(dict(path=str(p),title=title,snippets=[plain[max(0,m.start()-180):m.end()+550] for m in re.finditer('podkey',plain,re.I)][-6:]))
print(json.dumps(hits,indent=2))
print('API report candidates:',[str(p) for p in (root/'doc/client/html/star').glob('*/*Overset*Report*.html')])
