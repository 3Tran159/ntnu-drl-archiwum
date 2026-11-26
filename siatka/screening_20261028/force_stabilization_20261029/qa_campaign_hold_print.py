import json,sys,subprocess
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029');D=R/'campaign_hold_ui_qa_20261030'
sys.path.insert(0,str(R));import case_diagnostic_panel as m
original=m._read;hold=original(R/'campaign_hold.json')
active=m.hold_notice();assert 'Campaign paused' in active and 'No automatic C01 or wave launch' in active
with patch.object(m,'_read',return_value={}):assert m.hold_notice()==''
with patch.object(m,'_read',return_value={'active':True,'reason':'<script>unsafe</script>'}):assert '&lt;script&gt;' in m.hold_notice() and '<script>unsafe' not in m.hold_notice()
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
   matches.append({'page':i+1,'image':str(prefix)+'.png','pause_and_deferred':('Campaign paused' in text and 'not launched' in text and 'If approved after mesh review' in text),'prior_error_retained':'50.162' in text and '0.025137%' in text})
 printing.append({'surface':surface,'pages':len(reader.pages),'diagnostic_pages':matches})
assert all(len(x['diagnostic_pages'])==1 and all(v['pause_and_deferred'] and v['prior_error_retained'] for v in x['diagnostic_pages']) for x in printing),printing
browser=json.loads((D/'browser_review.json').read_text(encoding='utf8'));assert browser['pass']
report={'status':'PASS','at':datetime.now().astimezone().isoformat(),'scope':'Dynamic campaign_hold.json pause presentation only. No CFD, service, locks, STOP or control actions. Other agent mesh work untouched.','sources_changed':[str(R/'case_diagnostic_panel.py'),str(R/'build_manual_dashboard_copy.py')],'widths_px':[1920,1360,390],'surfaces':['operational','professor'],'browser_pass':browser['pass'],'workflow':browser['workflow'],'mock_checks':['active hold visible','absent hold hidden','hold reason HTML escaped'],'print':printing,'visual_review':'Pending image inspection','artifact_directory':str(D),'hold_record':hold,'no_automatic_launch_claim':True,'probe_label':'Deferred — not launched','prior_error_evidence_preserved':True}
(R/'campaign_hold_ui_review_20261030.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({'status':report['status'],'print':printing},indent=2))
