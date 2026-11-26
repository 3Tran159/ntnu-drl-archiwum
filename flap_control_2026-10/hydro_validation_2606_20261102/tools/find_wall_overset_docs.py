from pathlib import Path
import re,html,json
root=Path('E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/doc/en/online/STARCCMP');out=[]
for p in root.glob('GUID-*.html'):
 raw=p.read_text(encoding='utf8',errors='ignore')
 if 'overset' not in raw.lower() or 'wall distance' not in raw.lower():continue
 title=re.search(r'<title>(.*?)</title>',raw,re.S).group(1)
 plain=html.unescape(re.sub(r'\s+',' ',re.sub('<[^>]*>',' ',raw)))
 snippets=[plain[max(0,m.start()-260):m.end()+750] for m in re.finditer('wall distance',plain,re.I)]
 snippets=[x for x in snippets if 'overset' in x.lower()]
 if snippets:out.append(dict(file=p.name,title=title,snippets=snippets[:4]))
print(json.dumps(out,indent=2))
