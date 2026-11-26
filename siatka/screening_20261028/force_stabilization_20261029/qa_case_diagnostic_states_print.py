import sys,json,subprocess
from pathlib import Path
from unittest.mock import patch
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029');D=R/'case_diagnostic_ui_qa_20261030';sys.path.insert(0,str(R));import case_diagnostic_panel as m
actual_read=m._read
guard=actual_read(R/'c01_calm_r2_guard_review.json');review=actual_read(R/'c01_calm_r2_next_diagnostic_review.json');build=actual_read(R/'c01_halfdt_probe_r3_build_receipt.json')
base={'c01_calm_r2_guard_review.json':guard,'c01_calm_r2_next_diagnostic_review.json':review,'c01_halfdt_probe_r3_build_receipt.json':build}
checks=[]
for state,done,result,want in [
 ({'case':'Other_case','computation_active':True},{},{},'Prepared - not launched'),
 ({'case':m.PROBE,'directory':'E:/ntnu/quasi2d_waves_20261029/'+m.PROBE,'computation_active':True,'status':'running','progress':{'time_s':2.01}},{},{},'Running - time-step diagnostic'),
 ({'case':m.PROBE,'directory':'E:/ntnu/quasi2d_waves_20261029/'+m.PROBE,'computation_active':False,'status':'needs_review'},{'time_s':2.5,'status':'stability_guard'},{},'Stopped - diagnostic review required'),
 ({'case':m.PROBE,'directory':'E:/ntnu/quasi2d_waves_20261029/'+m.PROBE,'computation_active':False,'status':'completed'},{'time_s':2.9,'status':'completed'},{'case':'Wrong_case','status':'accepted'},'Completed - diagnostic review pending'),
 ({'case':m.PROBE,'directory':'E:/ntnu/quasi2d_waves_20261029/'+m.PROBE,'computation_active':False,'status':'completed'},{'time_s':2.9,'status':'completed'},{'case':m.PROBE,'status':'diagnostic_review_only'},'Completed - diagnostic review recorded')]:
 values=dict(base,**{'wave_foil_run_state.json':state,'completed.json':done,'c01_halfdt_probe_r3_review.json':result})
 with patch.object(m,'_read',side_effect=lambda p:values.get(Path(p).name,{})):h=m.panel()
 ok=want in h and guard['case'] in h and 'Physical-speed guard exceeded' in h and 'Diagnostic only.' in h and 'accepted</p>' not in h
 checks.append({'expected_status':want,'pass':ok})
assert all(x['pass'] for x in checks)
sys.path.insert(0,r'C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/Lib/site-packages')
from pypdf import PdfReader
exe=r'C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
printing=[]
for surface in ['operational','professor']:
 pdf=D/(surface+'_print.pdf');reader=PdfReader(str(pdf));matches=[]
 for i,page in enumerate(reader.pages):
  text=page.extract_text() or ''
  if 'Errors and diagnostics' in text and 'Physical-speed guard exceeded' in text:
   prefix=D/(surface+'_print_diagnostics_page_'+str(i+1))
   subprocess.run([exe,'-f',str(i+1),'-l',str(i+1),'-scale-to','1800','-singlefile','-png',str(pdf),str(prefix)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   matches.append({'page':i+1,'image':str(prefix)+'.png','both_cards':m.PROBE in text and 'Diagnostic only.' in text,'source_and_failure_distinct':'2.777' in text and '1.837' in text,'mass_cause_separate':'not the guard' in text})
 printing.append({'surface':surface,'pages':len(reader.pages),'diagnostic_pages':matches})
assert all(len(x['diagnostic_pages'])==1 and all(v['both_cards'] and v['source_and_failure_distinct'] and v['mass_cause_separate'] for v in x['diagnostic_pages']) for x in printing),printing
(D/'print_and_state_tests.json').write_text(json.dumps({'state_tests':checks,'print':printing},indent=2),encoding='utf8')
print(json.dumps({'state_tests':checks,'print':printing},indent=2))
