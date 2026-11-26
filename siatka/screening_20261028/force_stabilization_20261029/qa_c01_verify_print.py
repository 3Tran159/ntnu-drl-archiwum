from pathlib import Path
import csv,json,math,subprocess
from pypdf import PdfReader
R=Path(__file__).resolve().parent;D=R/'c01_calm_dashboard_qa_20261030'
a=json.loads((D/'integrated_review.json').read_text(encoding='utf8'))
folder=Path('E:/ntnu/quasi2d_waves_20261029/C01_W20L4_M10_calm_settle_r2')
with (folder/'history.csv').open(encoding='utf-8-sig',newline='') as f:hist=list(csv.DictReader(f))
rows=[{k:float(r[k]) for k in ('time_s','CD','CL_total')} for r in hist]
checks=[]
for view in a['rows']:
 assert view['case']==folder.name and view['start']==.587 and view['period'] is None and view['arrivalCount']==0
 assert set(view['keys'])=={'CD','CL_total','CD_window_pct','CL_window_pct'}
 assert not view['errors'] and not view['overflow'] and not view['catalog']['violations']
 assert not any(p['nonfinite'] for p in view['plots'])
 assert 'per-step' not in view['text'].lower() and 'preceding physical step' not in view['text'].lower()
 for key,coeff in (('CD_window_pct','CD'),('CL_window_pct','CL_total')):
  t,val=view['latest'][key];old=[r[coeff] for r in rows if t-.4<r['time_s']<=t-.2];new=[r[coeff] for r in rows if t-.2<r['time_s']<=t]
  assert len(old)>=199 and len(new)>=199
  mean_old=math.fsum(old)/len(old);mean_new=math.fsum(new)/len(new);expected=100*(mean_new-mean_old)/abs(mean_new)
  assert abs(val-expected)<1e-10,(key,t,val,expected)
  checks.append({'surface':view['surface'],'width':view['width'],'key':key,'time_s':t,'display_pct':val,'independent_pct':expected,'counts':[len(old),len(new)]})
 inter=view['interaction']
 if 'manual' in inter:assert inter['manual']==inter['reloaded']
 ticks=[tuple(x['ticks']) for x in inter['follow'] if x['ticks']];assert len(set(ticks))==1 and len(ticks)==4
 if view['width']==390:assert all(x['remaining']<=1 for x in inter['scrolls'])
printreview=[]
exe=r'C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
for name in ('operational','professor'):
 p=D/(name+'_print.pdf');pdf=PdfReader(p);matches=[]
 for i,page in enumerate(pdf.pages):
  text=page.extract_text() or ''
  if 'C01 — matched calm reference' in text or 'Rolling change between adjacent 0.2' in text or ('Wave cases and parameters' in text and 'settle C01' in text):
   matches.append(i+1);subprocess.run([exe,'-f',str(i+1),'-singlefile','-r','90','-png',str(p),str(D/(name+'_print_page_'+str(i+1)))],check=True,capture_output=True)
 printreview.append({'surface':name,'pages':len(pdf.pages),'target_pages':matches})
(D/'numeric_interaction_print_review.json').write_text(json.dumps({'status':'PASS_CHECKS_PENDING_PRINT_VISUAL','numeric':checks,'interactions':'Manual pan/reload persisted; all4Followaxes synchronized; mobile latest edge visible.','print':printreview},indent=2),encoding='utf8')
print(json.dumps({'status':'PASS_CHECKS_PENDING_PRINT_VISUAL','comparisons':len(checks),'print':printreview}))
