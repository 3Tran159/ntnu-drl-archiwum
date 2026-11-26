import json,subprocess
from pathlib import Path
from pypdf import PdfReader
root=Path('F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/wave_live_final_qa_20261030')
pop='C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
out={}
for name in ['operational','professor']:
 p=root/(name+'.pdf');reader=PdfReader(p);texts=[x.extract_text() or '' for x in reader.pages]
 selected=[i+1 for i,t in enumerate(texts) if any(s in t for s in ['Wave forces','Cycle overlap','Foil and wave','Deviation from the last full','Fundamental amplitude'])]
 selected=[i for i in selected if i<10]
 out[name]={'pages':len(texts),'selected':selected,'text':[(i,texts[i-1]) for i in selected]}
 for i in selected:subprocess.run([pop,'-f',str(i),'-l',str(i),'-scale-to','1500','-png','-singlefile',str(p),str(root/(name+'_print_'+str(i)))],check=True,capture_output=True)
(root/'print_review.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({k:{'pages':v['pages'],'selected':v['selected']} for k,v in out.items()}))
