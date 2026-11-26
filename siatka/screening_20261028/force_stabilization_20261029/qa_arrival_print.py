from pathlib import Path
from pypdf import PdfReader
import json,subprocess
D=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/wave_arrival_ui_qa_20261030')
exe=r'C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
out=[]
for name in ('operational','professor'):
 p=D/(name+'_print.pdf');pdf=PdfReader(p);matches=[]
 for i,page in enumerate(pdf.pages):
  text=page.extract_text() or ''
  if 'First inlet crest at foil' in text or ('Wave cases and parameters' in text and 'Fresh t' in text):
   matches.append(i+1);prefix=D/(name+'_print_page_'+str(i+1))
   subprocess.run([exe,'-f',str(i+1),'-singlefile','-r','90','-png',str(p),str(prefix)],check=True,capture_output=True)
 out.append({'surface':name,'pages':len(pdf.pages),'target_pages':matches})
(D/'print_review.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps(out))
