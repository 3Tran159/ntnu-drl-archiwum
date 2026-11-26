from pathlib import Path
import re,html,sys,json
R=Path('E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/doc/en/online/STARCCMP')
raw=(R/(sys.argv[1]+'.html')).read_text(encoding='utf8')
m=re.search(r'<main\b.*?</main>',raw,re.S);t=html.unescape(re.sub('<[^>]+>',' ',m.group(0)));t=re.sub(r'\s+',' ',t)
for q in sys.argv[2:]:
 positions=[m.start() for m in re.finditer(re.escape(q),t,re.I)]
 print(json.dumps([t[max(0,i-300):i+1800] for i in positions[:3]]))
