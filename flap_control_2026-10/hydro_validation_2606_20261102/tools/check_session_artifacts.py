from pathlib import Path
from html.parser import HTMLParser
import json,re
from PIL import Image
H=Path(__file__).resolve().parents[1]
report=H/'reports/RESUME_AND_MOTION_20261103.html'
class LinkCheck(HTMLParser):
 def __init__(self,base):super().__init__();self.base=base;self.links=[]
 def handle_starttag(self,tag,attrs):
  for key,value in attrs:
   if key in ('href','src') and value and not value.startswith(('http:','https:','#')):
    p=(self.base/value).resolve();assert p.exists(),p;self.links.append(str(p))
class PolishSpacing(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=False);self.parts=[]
 def handle_starttag(self,tag,attrs):self.parts.append(self.get_starttag_text())
 def handle_endtag(self,tag):self.parts.append('</'+tag+'>')
 def handle_decl(self,data):self.parts.append('<!'+data+'>')
 def handle_entityref(self,name):self.parts.append('&'+name+';')
 def handle_charref(self,name):self.parts.append('&#'+name+';')
 def handle_data(self,data):
  if re.fullmatch(r'[a-f0-9]{64}',data.strip()):self.parts.append(data);return
  data=re.sub(r'([,;])(?=[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż0-9])',r'\1 ',data)
  for a,b in {'333939komórek':'333 939 komórek','100kroków':'100 kroków','100położeniach':'100 położeniach','100 położeniach':'100 położeniach','40 iteracji':'40 iteracji','8CPU':'8 CPU','10kroków':'10 kroków','25kroków':'25 kroków','dt0.002':'dt = 0.002','okres0.2s':'okres 0.2 s','zapisany0.850s':'zapisany 0.850 s','C0t0.650':'C0 t = 0.650','B0t0.500':'B0 t = 0.500','iter11560':'iter. 11560','iter6250':'iter. 6250','iter11570':'iter. 11570','czasowy0.020':'czasowy 0.020','t0.670':'t = 0.670','t0.720':'t = 0.720','do0.720s':'do 0.720 s','klapki0':'klapki 0','Kroki0':'Kroki 0','STAR2606':'STAR 2606','STAR2602':'STAR 2602','x/c0.80':'x/c = 0.80','położeniu+2':'położeniu +2','końcowo+2':'końcowo +2','Końcowo+2':'Końcowo +2','40inner':'40 iteracji wewnętrznych','Y-momentum':'składowej Y pędu','95percentyl':'95. percentyl','bez GPU; checkpointy':'bez GPU; checkpointy'}.items():data=data.replace(a,b)
  self.parts.append(data)
fmt=PolishSpacing();fmt.feed(report.read_text(encoding='utf8'));report.write_text(''.join(fmt.parts),encoding='utf8')
checks=[]
for p in [report,H/'NIGHT_DASHBOARD.html']:
 check=LinkCheck(p.parent);check.feed(p.read_text(encoding='utf8'));checks.append(dict(path=str(p),links_checked=len(check.links)))
motion=json.loads((H/'audit/KINEMATIC_POC_REVIEW_20261103.json').read_text())
with Image.open(motion['animation']) as im:
 assert im.n_frames==21 and im.size==(1100,800)
 pixels=[]
 for i in [0,5,15]:im.seek(i);pixels.append(im.convert('RGB').tobytes())
 assert pixels[0]!=pixels[1] and pixels[1]!=pixels[2]
 print(json.dumps(dict(html=checks,animation_frames=im.n_frames,animation_size=im.size,distinct_0_plus5_minus5=True),indent=2))
