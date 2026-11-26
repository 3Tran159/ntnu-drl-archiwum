from pathlib import Path
from pypdf import PdfReader
import subprocess,json
R=Path(__file__).resolve().parent/'manual_panel_qa_20261030'
POP=Path('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe')
result=[]
for kind in ['operational','professor']:
 p=R/(kind+'.pdf')
 if not p.exists():continue
 d=PdfReader(p);texts=[x.extract_text() or '' for x in d.pages]
 selected=[i+1 for i,t in enumerate(texts) if any(s in t.lower() for s in ['manual control','local control','computer &','current case','last saved wave'])]
 selected=sorted(set([1]+selected))
 for i in selected:
  subprocess.run([str(POP),'-f',str(i),'-l',str(i),'-scale-to','1500','-png','-singlefile',str(p),str(R/(kind+'_print_'+str(i)))],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 result.append({'kind':kind,'pages':len(d.pages),'text_chars':[len(t) for t in texts],'rendered_pages':selected,'first_text':[t[:120] for t in texts]})
(R/'print_review_data.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result,indent=2))
