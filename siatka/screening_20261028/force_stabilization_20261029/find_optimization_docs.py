import re,json
from pathlib import Path
root=Path('E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/doc/en/online/STARCCMP')
matches=[]
for p in root.glob('*.html'):
 try:
  with p.open(encoding='utf-8',errors='replace') as f:s=f.read(6000)
  m=re.search(r'<title>(.*?)</title>',s,re.S|re.I)
  title=re.sub('<[^>]+>','',m.group(1)) if m else ''
  if re.search(r'(interpolat|map).*solution|solution.*(interpolat|map)|anisotropic.*(mesh|refin)|mesh.*anisotropic',title,re.I):matches.append({'file':str(p),'title':title})
 except OSError:pass
out=Path('F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/local_optimization_docs.json')
out.write_text(json.dumps(matches,indent=2));print(json.dumps(matches[:35],indent=2))
