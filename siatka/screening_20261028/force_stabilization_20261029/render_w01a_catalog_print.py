from pathlib import Path
from pypdf import PdfReader
import json,subprocess
R=Path(__file__).resolve().parent;D=R/'w01a_transition_qa_20261030'
poppler=Path('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe')
out={}
for surface in ('operational','professor'):
 p=D/(surface+'_catalog_print_first8.pdf');doc=PdfReader(p);pages=[]
 for i,page in enumerate(doc.pages,1):
  text=page.extract_text()
  if 'Wave cases and parameters' in text:
   pages.append({'page':i,'contains_W01a':'W01a' in text,'contains_W08':'W08' in text,'contains_3lambda':'W01_3lambda' in text})
   subprocess.run([str(poppler),'-f',str(i),'-singlefile','-scale-to','1600','-png',str(p),str(D/(surface+'_catalog_print_'+str(i)))],check=True,capture_output=True)
 out[surface]=pages
(D/'catalog_print_review.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out))
