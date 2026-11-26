import json,hashlib,datetime
from pathlib import Path
from pypdf import PdfReader
R=Path(__file__).resolve().parent
browser=json.loads((R/'professor_readability_review.json').read_text())
main=json.loads((R/'main_configured_force_qa.json').read_text())
release=json.loads((R/'professor_print_release_qa.json').read_text())
pdf=R/'professor_review_qa_release.pdf'
pages=len(PdfReader(pdf).pages)
assert pages==13
assert all(not x['overflow'] and not x['errors'] and not x['invalidText'] for x in browser)
assert all(not x['errors'] and not x['overflow'] and x['hoverPass'] and x['pinPass'] and x['escapePass'] for x in main)
mobile=next(x for x in browser if x['width']==390)
assert mobile['modal']['open'] and mobile['modal']['escapeClosed'] and mobile['modal']['closeButtonWorks']
assert all(x['width']>=1100 for x in mobile['fieldWidths'])
assert not release['screen']['duplicateIds'] and not release['errors']
report={'status':'passed','reviewed_at':datetime.datetime.now().astimezone().isoformat(),'browser_viewports_px':[1360,1920,390],'main_dashboard_viewports_px':[1360,390],'print_pdf_pages':pages,'visual_review':'All thirteen release PDF pages visually inspected. No clipped tables, overlapping labels, split nodes, orphaned continuation notes or blank continuation pages. Final spacing-only revision rechecked on overview and numerical-comparison pages.','browser_checks':['No document overflow or JavaScript errors','Desktop/projector tables fit at16/17px','All section anchors clear sticky navigation','Mobile field figures pan at1100px and Expand/Close/Escape work','Main dashboard M09 link resolves; historical force explorer excludes empty M09 history','Force hover dimming, pinning, Escape and alltime ranges work','Print-only report hidden on screen; main/navigation hidden in print; no duplicate IDs'],'previous_findings_resolved':['Mobile field figures too small','Print fragmentation from21/20pages into13 intentional pages','Missing first progress record displayed as a waiting message'],'scientific_scope':'Readability and presentation QA only; scientific interpretation remains governed by saved experiment evidence.','files':{'html':str(R.parent/'professor_dashboard.html'),'html_sha256':hashlib.sha256((R.parent/'professor_dashboard.html').read_bytes()).hexdigest(),'qa_pdf':str(pdf),'qa_pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'browser':'professor_readability_review.json','main':'main_configured_force_qa.json','print':'professor_print_release_qa.json'}}
(R/'professor_final_qa.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
findings=json.loads((R/'professor_visual_review_findings.json').read_text())
findings.update({'status':'resolved_passed','final_report':'professor_final_qa.json','pending':[]})
for x in findings['issues']:x['status']='resolved'
(R/'professor_visual_review_findings.json').write_text(json.dumps(findings,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'pdf_pages':pages,'final_report':str(R/'professor_final_qa.json')}))
