from pathlib import Path
import sys,re,html
root=Path('E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/doc/en/online/STARCCMP')
for name in sys.argv[1:]:
 assert re.fullmatch(r'GUID-[A-F0-9-]+',name)
 s=(root/(name+'.html')).read_text(encoding='utf8')
 text=html.unescape(re.sub('<[^>]+>',' ',s[s.rfind('<h1'):]))
 text=re.sub(r'\s+',' ',text)
 print(name+'\n'+text[:18000]+'\n')
