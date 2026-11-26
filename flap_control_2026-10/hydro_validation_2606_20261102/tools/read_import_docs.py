from pathlib import Path
import re,html,json
root=Path('E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/doc')
for p in [root/'client/html/star/meshing/PartImportManager.html',root/'api/star/meshing/PartImportManager.html']:
 if p.exists():
  t=html.unescape(re.sub('<[^>]+>',' ',p.read_text(encoding='utf8',errors='ignore')));t=re.sub(r'\s+',' ',t)
  for m in list(re.finditer('importStlPart',t))[-12:]: print(json.dumps(t[m.start():m.start()+1200]))
  break
else:print('javadoc not found')
