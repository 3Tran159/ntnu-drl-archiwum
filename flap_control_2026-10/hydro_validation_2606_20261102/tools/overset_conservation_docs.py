from pathlib import Path
import re,json
root=Path('E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/doc/en/online/STARCCMP')
hits=[]
for p in root.glob('GUID-*.html'):
 text=p.read_text(encoding='utf8',errors='ignore')
 if re.search(r'overset',text,re.I) and re.search(r'(mass conservation|mass imbalance|flux correction|conservative interpolation|conservation correction)',text,re.I):
  plain=re.sub('<[^>]*>',' ',text);plain=re.sub(r'\s+',' ',plain)
  snippets=[plain[max(0,m.start()-300):m.end()+600] for m in re.finditer(r'(mass conservation|mass imbalance|flux correction|conservative interpolation|conservation correction)',plain,re.I)]
  hits.append(dict(path=str(p),title=re.search(r'<title>(.*?)</title>',text,re.S).group(1) if '<title>' in text else '',snippets=snippets))
h=Path(__file__).resolve().parents[1];(h/'audit/overset_conservation_docs.json').write_text(json.dumps(hits,indent=2),encoding='utf8')
print(json.dumps(hits,indent=2)[:24000])
