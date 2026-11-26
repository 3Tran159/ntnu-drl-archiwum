from pathlib import Path
import re,html,json
r=Path(r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\doc\en\online\STARCCMP')
hits=[]
for p in r.glob('*.html'):
 t=p.read_text(encoding='utf8',errors='ignore')
 if not all(v in t for v in ['Prism','Layer','Number']):continue
 raw=html.unescape(re.sub('<[^>]+>',' ',t));raw=re.sub(r'\s+',' ',raw)
 for m in re.finditer('Prism Layer Number',raw):
  hits.append(dict(path=str(p),text=raw[max(0,m.start()-180):m.end()+1600]))
print(json.dumps(hits[:8],indent=2))
