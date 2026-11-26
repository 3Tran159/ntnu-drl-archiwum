"""Read-only lifecycle routing, verified history lineage and persistent case archives."""
import datetime, hashlib, html, json, os, re
from pathlib import Path
R=Path(__file__).resolve().parent
W=Path('E:/ntnu/quasi2d_waves_20261029')
TERMINAL=('guard','fail','error','needs_review','completed','stopped','paused','saved','cancelled','finished')
def read(path):
 try:return json.loads(Path(path).read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return {}
def esc(value):return html.escape(str(value),quote=True)
def is_active(state,root=R):
 """Only current explicit activity can activate Live; a terminal receipt always wins."""
 if state.get('computation_active') is not True:return False
 raw=state.get('directory')
 if not raw or not Path(raw).is_absolute():return False
 if read(Path(raw)/'completed.json') or (state.get('result') or {}).get('completed'):return False
 statuses=[state.get('status',''),(state.get('progress') or {}).get('status','')]
 return not any(word in str(status).lower() for status in statuses for word in TERMINAL)
def _digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def history_sources(state,folder,wave_root=W):
 """Return current history plus only a verified, explicitly resumed same-mode lineage."""
 folder=Path(folder);identity=read(folder/'source_identity.json');warnings=[]
 current=[{'path':str(folder/name)} for name in ('startup_history.csv','history.csv') if (folder/name).is_file()]
 inherited=identity.get('history_files') or state.get('history_sources') or []
 if not inherited:return current,warnings
 mode=identity.get('continuation_mode')
 wave=state.get('computation_stage')=='inlet_wave_full_amplitude'
 permitted=(mode=='wave' and identity.get('resume_wave') is True) if wave else (state.get('computation_stage')=='calm_settling' and mode=='calm')
 if not permitted:return current,['Inherited history excluded: this is not an explicit same-mode resume.']
 if not identity.get('source_sha256') or identity.get('source_sha256')!=identity.get('input_sha256') or identity.get('source_is_guard_failed') is True:
  return current,['Inherited history excluded: source/input identity is not verified.']
 hashes=identity.get('history_sha256') or state.get('history_source_sha256') or {}
 if not isinstance(hashes,dict):return current,['Inherited history excluded: recorded hashes are unavailable.']
 verified=[]
 try:
  anchor=Path(wave_root).resolve()
  for entry in inherited:
   raw=entry.get('path') if isinstance(entry,dict) else entry
   path=Path(raw)
   if not path.is_absolute() or not path.resolve().is_relative_to(anchor):raise ValueError('history is outside the campaign folder')
   if not path.is_file():raise ValueError('history file is missing')
   expected=hashes.get(str(path)) or hashes.get(path.as_posix()) or (entry.get('sha256') if isinstance(entry,dict) else None)
   if not expected or _digest(path).lower()!=str(expected).lower():raise ValueError('history checksum differs')
   if path.resolve()!= (folder/'history.csv').resolve():verified.append({'path':str(path)})
 except (OSError,ValueError,TypeError) as error:return current,['Inherited history excluded: '+str(error)+'.']
 return verified+current,warnings
STYLE="""<style>
.live-analysis,.case-archive{border:1px solid #cbd7df;padding:20px;margin:20px 0;color:#153243;background:#fff}
.live-analysis h2,.case-archive h2{margin:0 0 14px}.live-analysis p,.case-archive p{line-height:1.5}
.live-empty-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.live-empty-grid>section{margin:0!important;border:1px solid #dce4e9;background:#f7f9fa;padding:16px;min-width:0}
.live-empty-grid h3{font-size:16px;margin:0 0 8px}.live-empty-grid p{margin:0;color:#526570}
.archive-run{border-top:1px solid #d6dfe5;padding:12px 0}.archive-run summary{cursor:pointer;overflow-wrap:anywhere}
.archive-run iframe{width:100%;height:900px;border:1px solid #ced9df;background:white}
.archive-links{display:flex;flex-wrap:wrap;gap:14px;margin:12px 0}.archive-state{font-size:13px;color:#526570}
.live-only-diagnostic{padding:12px;border-left:3px solid #b77615;overflow-wrap:anywhere}
@media(max-width:700px){.live-analysis,.case-archive{padding:14px}.live-empty-grid{grid-template-columns:1fr}.archive-run iframe{height:850px}}
@media print{.live-analysis{break-inside:avoid}.live-empty-grid{grid-template-columns:1fr 1fr}.archive-run iframe,.archive-screen-only{display:none!important}.archive-run{break-inside:avoid}.archive-run>div{display:block!important}.live-analysis .wave-cycle-panel{break-before:auto}}
</style>"""
def _atomic(path,text):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 tmp=path.with_name(path.name+'.'+str(os.getpid())+'.tmp')
 tmp.write_text(text,encoding='utf8');os.replace(tmp,path)
def current_diagnostic(state):
 folder=Path(state.get('directory',''));data=read(folder/'diagnostic_summary.json')
 if data.get('case') not in (None,state.get('case')):data={}
 error=data.get('error_type') or data.get('message')
 return '<section class="live-only-diagnostic"><h3>Current diagnostics</h3><p>'+esc(error or 'No current-case stop diagnostic recorded. Numerical quality and accuracy checks remain separate.')+'</p></section>'
def _archive(state,body,root,destinations):
 case=str(state.get('case') or '')
 if not re.fullmatch(r'[A-Za-z0-9_-]+',case) or not state.get('directory'):return None
 folder=Path(state['directory'])
 if not folder.is_absolute() or not folder.is_dir():return None
 done=read(folder/'completed.json')
 # Archive preserves the exact read-only chart state, embedded field images and provenance.
 status=str(done.get('status') or state.get('status') or 'saved snapshot')
 # Snapshots retain local chart interaction but never poll a live status endpoint.
 body=re.sub(r'<script\b[^>]*>.*?</script>',lambda m:'' if '/api/' in m.group(0) else m.group(0),body,flags=re.S|re.I)
 body=body.replace('GPU calculation active','Saved snapshot — inactive')
 stamp=datetime.datetime.now().astimezone().isoformat()
 record={'case':case,'file':case+'.html','directory':str(folder),'status':status,'snapshot_at':stamp,'time_s':done.get('time_s',state.get('progress',{}).get('time_s')),'active_at_snapshot':is_active(state,root)}
 page='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(case)+' — saved analysis</title><style>body{font:15px system-ui,sans-serif;color:#173043;margin:0 auto;padding:24px;max-width:1440px}a{color:#006ca3}header{border-bottom:1px solid #b9cbd6;padding-bottom:16px;margin-bottom:18px}code{overflow-wrap:anywhere}img{max-width:100%}@media print{body{padding:0;font-size:10pt}}</style></head><body><header><h1>Archived calculation</h1><p><b>'+esc(case)+'</b> · '+esc(status)+'</p><p>Read-only saved analysis. Opening this page never loads or starts a solver. Snapshot: '+esc(stamp)+'.</p><p><a href="../local_campaign_results.html">Compare saved calculations</a></p></header>'+body+'</body></html>'
 for destination in destinations:_atomic(Path(destination)/'archive_runs'/record['file'],page)
 return record
def panels(state,current_html='',diagnostics_html='',files_html='',root=R,destinations=None):
 root=Path(root);destinations=destinations or [root.parent,root.parent/'dashboard_work_20261030']
 active=is_active(state,root);hold=read(root/'campaign_hold.json')
 index=read(root/'archive_run_index.json')
 records={item['case']:item for item in index.get('runs',[]) if isinstance(item,dict) and item.get('case')}
 record=_archive(state,current_html+diagnostics_html+files_html,root,destinations) if current_html else None
 if record:records[record['case']]=record
 _atomic(root/'archive_run_index.json',json.dumps({'updated_at':datetime.datetime.now().astimezone().isoformat(),'runs':list(records.values())},indent=2))
 live=STYLE+'<section id="live-analysis" class="live-analysis" data-active="'+str(active).lower()+'"><h2>Live analysis</h2>'
 if active:
  live+='<p><b>'+esc(state.get('case'))+'</b> · active calculation</p>'+current_html+current_diagnostic(state)
 else:
  live+='<p><b>No active calculation.</b> '+('Campaign paused while mesh convergence and optimization are reviewed.' if hold.get('active') is True else 'Start or resume an inspected case using the local controls.')+'</p>'
  buckets=[('Time estimate','Available during an active wave run; ten periods is an indicative target.'),
   ('CD and CL history','Current-case force coefficients will appear here.'),
   ('Convergence','Adjacent calm windows or complete wave-cycle criteria, as applicable.'),
   ('Wave-cycle overlap','Fixed-phase complete cycles from the active case.'),
   ('Foil and free surface','An actual saved field from the active case, with its timestamp.'),
   ('Errors and diagnostics','Current-case diagnostics will appear here. Saved errors remain in the archive.')]
  live+='<div class="live-empty-grid">'+''.join('<section><h3>'+a+'</h3><p>'+b+'</p></section>' for a,b in buckets)+'</div>'
 live+='</section>'
 archive='<section id="case-archive" class="case-archive"><h2>Archive and comparisons</h2><p>Saved calculations are read-only. Choose a record to inspect its charts, fields and diagnostics.</p><p><a href="local_campaign_results.html">Open aggregate comparison report</a></p>'
 saved=sorted(records.values(),key=lambda x:x.get('snapshot_at',''),reverse=True)
 for item in saved:
  if active and item['case']==state.get('case'):continue
  url='archive_runs/'+item['file']
  archive+='<details class="archive-run"><summary><b>'+esc(item['case'])+'</b> <span class="archive-state">— '+esc(item.get('status','saved'))+'</span></summary><div><div class="archive-links"><a target="_blank" rel="noopener" href="'+esc(url)+'">Open archived view</a><a href="local_campaign_results.html">Compare this record</a></div><p class="archive-state">Saved snapshot '+esc(item.get('snapshot_at',''))+'. Archived values are not live readings.</p><iframe class="archive-screen-only" title="Read-only archive '+esc(item['case'])+'" data-archive-src="'+esc(url)+'" loading="lazy"></iframe></div></details>'
 if not saved:archive+='<p>No saved calculation has been archived yet.</p>'
 archive+='</section><script>document.querySelectorAll(".archive-run").forEach(function(d){d.addEventListener("toggle",function(){var f=d.querySelector("iframe");if(d.open&&f&&!f.src)f.src=f.dataset.archiveSrc;});});</script>'
 return live,archive
