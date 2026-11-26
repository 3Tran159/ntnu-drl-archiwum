from pathlib import Path
import json,re,zipfile,html
R=Path(__file__).resolve().parent;root=Path(r'E:\Program Files\Siemens\21.02.007-R8\STAR-CCM+21.02.007-R8');hits=[]
for p in (root/'doc/en/online').rglob('*.html'):
 s=p.read_text(encoding='utf-8',errors='ignore')
 if 'First Wave Front' in s or 'Enable Theory Comparison' in s or 'first wave front' in s:
  t=html.unescape(re.sub('<[^>]+>',' ',s));t=re.sub(r'\s+',' ',t)
  hits.append({'path':str(p),'snippets':[t[max(0,m.start()-220):m.end()+1000] for m in re.finditer('First Wave Front|Enable Theory Comparison|first wave front',t)]})
out={'sources':hits,'meaning':'Installed source-version documentation; use to audit flat initial analytic gauges before changing wave settings.'}
(R/'wave_front_local_documentation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
