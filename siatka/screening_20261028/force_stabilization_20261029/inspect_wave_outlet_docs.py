from pathlib import Path
import re,html,json
root=Path('E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/doc/en/online/STARCCMP')
out=[]
for p in root.glob('*.html'):
 raw=p.read_text(encoding='utf-8',errors='replace')
 low=raw.lower()
 if 'wave' not in low or 'hydrostatic' not in low:continue
 text=html.unescape(re.sub('<[^>]+>',' ',raw));text=' '.join(text.split())
 if not any(x in text.lower() for x in ['backflow','boundary conditions','pressure outlet']):continue
 snippets=[]
 for m in list(re.finditer('backflow|pressure outlet|hydrostatic pressure',text,re.I))[:8]:
  snippets.append(text[max(0,m.start()-160):m.end()+1000])
 if snippets:out.append({'path':str(p),'title':re.search('<title[^>]*>(.*?)</title>',raw,re.S).group(1) if '<title' in raw else '', 'snippets':snippets})
Path('F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/wave_outlet_local_documentation.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out[:10],indent=2))
