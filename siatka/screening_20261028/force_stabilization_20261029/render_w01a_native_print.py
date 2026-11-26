from pathlib import Path
from pypdf import PdfReader
import json,subprocess
R=Path(__file__).resolve().parent;D=R/'w01a_native_fields_qa_20261030'
poppler=Path('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe')
out={}
for surface in ('operational','professor'):
 p=D/(surface+'_print_first8.pdf');doc=PdfReader(p);pages=[]
 for i,page in enumerate(doc.pages,1):
  text=page.extract_text()
  if 'Vorticity' in text or 'Native signed' in text:
   pages.append({'page':i,'summary':'Vorticity' in text,'caption':'Native signed' in text})
   subprocess.run([str(poppler),'-f',str(i),'-singlefile','-scale-to','1600','-png',str(p),str(D/(surface+'_vorticity_print_'+str(i)))],check=True,capture_output=True)
 out[surface]=pages
(D/'print_review.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out))
