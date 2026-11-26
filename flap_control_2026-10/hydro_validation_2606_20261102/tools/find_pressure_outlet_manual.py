from pathlib import Path
import re,html,json
base=Path('E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/doc/en/online/STARCCMP')
hits=[]
for p in base.glob('*.html'):
 s=p.read_text(encoding='utf8',errors='replace')
 if 'backflow' not in s.lower() or 'extrapolated' not in s.lower():continue
 t=html.unescape(re.sub('<[^>]+>',' ',s));t=re.sub(r'\s+',' ',t)
 pos=[m.start() for m in re.finditer(r'backflow|extrapolated',t,re.I)]
 title=re.search(r'<title>(.*?)</title>',s,re.S)
 hits.append(dict(path=str(p),title=html.unescape(title.group(1)) if title else '',snippets=[t[max(0,i-120):i+700] for i in pos[:8]]))
h=Path(__file__).resolve().parents[1];(h/'audit/pressure_outlet_local_manual_search.json').write_text(json.dumps(hits,indent=2),encoding='utf8')
print(json.dumps(hits,indent=2))
