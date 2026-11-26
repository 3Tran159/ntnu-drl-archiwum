from pathlib import Path
import re,json,sys
root=Path('E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/doc/en/online')
res=[]
for p in root.rglob('*.html'):
 with p.open('r',encoding='utf8',errors='ignore') as f:s=f.read(12000)
 m=re.search(r'<title[^>]*>(.*?)</title>',s,re.S)
 if m and any(q.lower() in m.group(1).lower() for q in sys.argv[1:]):res.append(dict(path=str(p),title=re.sub('<[^>]+>','',m.group(1))))
print(json.dumps(res,indent=2))
Path('F:/ntnu/flap_control/hydro_validation_2606_20261102/audit/doc_titles.json').write_text(json.dumps(res,indent=2))
