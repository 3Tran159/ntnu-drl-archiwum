from pathlib import Path
import re,html,json
root=Path(r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\doc\en\online\STARCCMP')
hits=[]
for p in root.glob('*.html'):
 t=p.read_text(encoding='utf8',errors='ignore')
 if 'face orientation' not in t.lower():continue
 raw=html.unescape(re.sub('<[^>]+>',' ',t));raw=re.sub(r'\s+',' ',raw)
 for m in re.finditer('face orientation',raw,re.I):
  clip=raw[max(0,m.start()-220):m.end()+500]
  if re.search('repair|negative|incorrect',clip,re.I):hits.append(dict(path=str(p),text=clip))
print(json.dumps(hits[:18],indent=2))
