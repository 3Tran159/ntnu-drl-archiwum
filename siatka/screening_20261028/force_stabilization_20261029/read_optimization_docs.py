from pathlib import Path
from html.parser import HTMLParser
import json,re
R=Path(__file__).resolve().parent
class P(HTMLParser):
 def __init__(self):super().__init__();self.parts=[];self.skip=0
 def handle_starttag(self,t,a):
  if t in ['script','style']:self.skip+=1
  if t in ['p','div','li','h1','h2','h3','tr']:self.parts.append('\n')
 def handle_endtag(self,t):
  if t in ['script','style']:self.skip-=1
 def handle_data(self,s):
  if not self.skip:self.parts.append(s)
docs=json.loads((R/'local_optimization_docs.json').read_text())
out=[]
for d in docs:
 if d['title'] not in ['Solution Interpolation Model Reference','Solution Data Interpolation','Anisotropic Meshing for Lifting Surfaces']:continue
 p=P();p.feed(Path(d['file']).read_text(errors='replace'));t=''.join(p.parts);t=re.sub(r'[ \t]+',' ',t);t=re.sub(r'\n\s*\n','\n',t)
 out.append(d['title']+'\n'+d['file']+'\n'+t)
(R/'local_optimization_reference_extracts.txt').write_text('\n\n'.join(out))
for a in out:print(a[:10000]+'\n')
