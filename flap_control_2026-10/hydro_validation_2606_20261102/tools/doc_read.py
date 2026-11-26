from pathlib import Path
import sys,re,html,json
R=Path('E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/doc/en/online/STARCCMP')
O=Path('F:/ntnu/flap_control/hydro_validation_2606_20261102/audit')
for name in sys.argv[1:]:
 raw=(R/(name+'.html')).read_text(encoding='utf8')
 m=re.search(r'<main\b.*?</main>',raw,re.S);m=m.group(0) if m else raw
 t=html.unescape(re.sub('<[^>]+>',' ',m));t=re.sub(r'\s+',' ',t)
 print(name+'\n'+json.dumps(t));(O/('doc_'+name+'.txt')).write_text(t,encoding='utf8')
 links=re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',m,re.S)
 print(json.dumps([(re.sub('<[^>]+>',' ',label),href) for href,label in links][:30]))
