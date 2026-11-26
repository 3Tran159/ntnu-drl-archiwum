from pathlib import Path
import re,json
root=Path(r'E:\Program Files\Siemens\21.02.007-R8\STAR-CCM+21.02.007-R8\doc\en\online\STARCCMP')
found=[]
for p in root.glob('*.html'):
 text=p.read_text(encoding='utf-8',errors='ignore')
 title=re.search(r'<title>(.*?)</title>',text,re.S)
 name=re.sub('<.*?>','',title.group(1)) if title else ''
 if any(s.lower() in name.lower() for s in ['GPU','Prism Layer Mesher','Prism Layer Detection','Prism Layer Controls','Enhanced Quality Prism']):
  clean=re.sub(r'<(script|style).*?</\1>','',text,flags=re.S);clean=re.sub('<[^>]+>',' ',clean);clean=re.sub(r'\s+',' ',clean)
  found.append({'file':p.name,'title':name,'text':clean})
out=Path(r'F:\ntnu\mesh_screening_20261028\night_20261028\help_selected.json');out.write_text(json.dumps(found,indent=2),encoding='utf-8')
for x in found:print(x['file'],x['title'],len(x['text']))
