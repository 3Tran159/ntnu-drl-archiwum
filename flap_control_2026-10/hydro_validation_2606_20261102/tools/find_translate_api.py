from pathlib import Path
import re
d=Path(r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\doc\client\html')
for p in d.glob('index-all.html'):
 t=p.read_text(encoding='utf8',errors='ignore')
 for m in re.finditer(r'href="([^"]+(?:translateMesh|translateRegions|transformMesh)[^"]*)"',t,re.I): print(m.group(1))
