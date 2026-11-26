import json, subprocess
from pathlib import Path
from pypdf import PdfReader
root=Path('F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/wave_cycle_integrated_qa_20261030')
pop='C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
r={}
for name in ['operational','professor']:
 p=root/(name+'.pdf')
 reader=PdfReader(p)
 texts=[x.extract_text() or '' for x in reader.pages]
 selected=[i+1 for i,t in enumerate(texts) if 'Wave forces' in t or 'Last four complete cycles' in t]
 r[name]={'pages':len(texts),'cycle_pages':selected,'cycle_text':[(i,texts[i-1]) for i in selected]}
 for i in selected:
  subprocess.run([pop,'-f',str(i),'-l',str(i),'-scale-to','1500','-png','-singlefile',str(p),str(root/(name+'_cycle_print_'+str(i)))],check=True,capture_output=True)
(root/'print_review.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
qa=json.loads((root/'qa.json').read_text())
print(json.dumps({'print':{k:{'pages':v['pages'],'cycle_pages':v['cycle_pages']} for k,v in r.items()},'first_panel':qa['views'][0]['initial']['panelText'],'last_panel':qa['laterSnapshot']['panelText']},ensure_ascii=True))
