from pathlib import Path
import json,subprocess,datetime,sys
sys.path.insert(0,r'C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/Lib/site-packages')
from pypdf import PdfReader
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029');D=R/'local_workflow_ui_qa_20261030'
bin=Path(r'C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin')
review=[]
for name in ('operational','professor'):
 pdf=D/(name+'_print.pdf')
 pages=[page.extract_text() or '' for page in PdfReader(pdf).pages]
 matches=[]
 for i,t in enumerate(pages):
  reasons=[label for label,needle in [('current_calm','C01 — matched calm reference'),('rolling_means','Rolling change between adjacent 0.2'),('local_controls','LOCAL SIMULATION CONTROL'),('catalog','Wave cases and parameters')] if needle in t]
  if reasons:
   out=D/(name+'_print_page_'+str(i+1))
   subprocess.run([str(bin/'pdftoppm.exe'),'-f',str(i+1),'-singlefile','-r','100','-png',str(pdf),str(out)],check=True,capture_output=True)
   matches.append(dict(page=i+1,reasons=reasons,image=str(out)+'.png',text_characters=len(t.strip())))
 review.append(dict(surface=name,pages=len(pages),targets=matches))
(D/'print_review.json').write_text(json.dumps({'at':datetime.datetime.now().astimezone().isoformat(),'status':'rendered_pending_visual','surfaces':review},indent=2),encoding='utf8')
print(json.dumps(review,indent=2))
