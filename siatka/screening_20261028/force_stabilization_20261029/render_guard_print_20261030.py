import subprocess,json
from pathlib import Path
from pypdf import PdfReader
r=Path('F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/wave_live_final_qa_20261030')
pop='C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
result=[]
for name in ['operational','professor']:
 p=r/(name+'_guard_print_first7.pdf');pages=PdfReader(p).pages
 hits=[i+1 for i,x in enumerate(pages) if 'Stopped by physical stability guard' in (x.extract_text() or '')]
 for n in hits:subprocess.run([pop,'-f',str(n),'-l',str(n),'-scale-to','1500','-png','-singlefile',str(p),str(r/(name+'_guard_print_'+str(n)))],check=True,capture_output=True)
 result.append({'name':name,'failure_pages':hits})
(r/'guard_print_review.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
