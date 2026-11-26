"""Publish authorized live views and working copies from the preserved meeting archive."""
import csv,datetime,hashlib,html,json,os,re,math
from pathlib import Path
import manual_control_common as c
R=c.R;B=R.parent;D=B/'dashboard_work_20261030';D.mkdir(exist_ok=True)
import operational_dashboard_layout as layout
import importlib
def case_panel():
 s=c.read(R/'wave_foil_run_state.json');case=s.get('case','');folder=s.get('directory','')
 try:p=c.safe_case(folder)
 except ValueError:return ''
 done=c.read(p/'completed.json');cp=c.read(p/'latest_checkpoint.json');st=c.read(p/'startup_acceptance.json');rows=[]
 if done.get('time_s',0)>0:rows.append(('final.sim',done['time_s'],'Saved computed state — '+str(done.get('status'))))
 if cp.get('completed_save'):rows.append((Path(cp['file']).name,cp.get('time_s',0),'Completed flow checkpoint'))
 if st.get('status')=='guarded_startup_completed':rows.append(('checkpoint_startup_t0.020.sim',.02,'Completed startup checkpoint'))
 held=c.read(R/'campaign_hold.json').get('active') is True
 status='Campaign paused — waiting for mesh review' if held else 'Saved computed state — calculation inactive' if s.get('computation_active') is False else ('Exploratory calculation' if not done else 'Saved result — review pending')
 def esc(v):return html.escape(str(v))
 body='<section id="current-foil-case" style="border:1px solid #bccdd6;padding:18px;margin:0 0 20px;overflow-wrap:anywhere"><h2>'+esc(status)+'</h2><p><b>'+esc(case)+'</b></p><p>Case folder:</p><code style="display:block;white-space:normal;overflow-wrap:anywhere">'+esc(folder)+'</code>'
 for name,t,label in sorted(rows,key=lambda x:x[1],reverse=True):
  f=p/name
  if f.is_file():body+='<p><b>'+esc(label)+' · t = '+format(t,'.3f')+' s</b><br><a href="'+f.as_uri()+'">'+esc(str(f))+'</a></p>'
 try:
  with (p/'history.csv').open(encoding='utf8') as f:hist=list(csv.DictReader(f))
  last=hist[-1]
  body+='<p><b>Saved instantaneous sample:</b> t = '+format(float(last['time_s']),'.3f')+' s; CD = '+format(float(last['CD']),'.7f')+'; CL = '+format(float(last['CL_total']),'.7f')+'; maximum speed = '+format(float(last['max_speed_m_s']),'.3f')+' m/s. This short startup record is not a cycle-averaged wave result.</p>'
 except (OSError,IndexError,KeyError,ValueError):pass
 body+='<p>These files contain calculated fields and inspection scenes. The time-zero setup file is deliberately excluded from this result list.</p><p>Observed phase-mass deviation was accepted by the user for exploratory work. The historical 0.01% diagnostic flag remains recorded. This does not establish wave-force accuracy. Instantaneous force values during startup are not settled cycle means.</p></section>'
 return body
def build():
 import importlib
 importlib.reload(layout)
 import wave_cycle_dashboard_panel, wave_case_catalog_panel, case_diagnostic_panel, live_analysis_panel
 for module in (wave_cycle_dashboard_panel,wave_case_catalog_panel,case_diagnostic_panel,live_analysis_panel):importlib.reload(module)
 freeze=c.read(R/'meeting_dashboard_freeze_20261030.json')
 publication=c.read(R/'dashboard_publication_20261030.json')
 publish=publication.get('status')=='live_updates_authorized_after_meeting'
 base=Path(publication['meeting_archive']) if publish else B
 state=c.read(R/'wave_foil_run_state.json')
 current_state={**state,'_live_context':True}
 cycles=wave_cycle_dashboard_panel.render(current_state,c.read(R/'wave_cycle_repeatability_current.json'),c.read(R/'wave_cycle_continuation_plan_r2.json'))
 catalog=wave_case_catalog_panel.panel()
 diagnostics=case_diagnostic_panel.panel()
 live_html,archive_html=live_analysis_panel.panels(state,cycles,diagnostics,case_panel(),root=R,destinations=[B,D])
 original_read=layout.read
 def live_read(key):
  return c.read(R/'control_computer_status.json') if key=='computer_status.json' else original_read(key)
 layout.read=live_read
 try:technical=layout.status_panel()
 finally:layout.read=original_read
 technical=re.sub(r'<p><b>Next useful work:</b>.*?</p>','<p><b>Current state:</b> no automatic solver launch. Saved calculations are available in the archive below.</p>',technical,flags=re.S)
 technical=technical.replace('Read-only monitor · no solver start controls','Computer and current calculation')
 technical=re.sub(r'(<p class="calculation-freshness"><b>GPU telemetry:</b>.*?</p>)',r'<details><summary>GPU temperature, clock and power</summary>\1</details>',technical,flags=re.S)
 external=[x for x in c.read(R/'control_computer_status.json').get('external_campaigns',[]) if x.get('state')=='running']
 if external:
  label=', '.join(str(x.get('label','Mesh study')) for x in external)
  technical=technical.replace('Paused — no campaign solve','Mesh study '+html.escape(label)+' active · our wave campaign paused')
  technical=technical.replace('<div class="status-grid">','<p><b>Independent mesh study:</b> '+html.escape(label)+' is active. These local wave controls do not control that calculation.</p><div class="status-grid">',1)

 if not live_analysis_panel.is_active(state):
  technical=re.sub(r'<div class="status-explanation">.*?</div>','<p><b>Our wave campaign:</b> paused; no active calculation. <a href="#case-archive">Last stopped run and saved diagnostics</a>.</p>',technical,flags=re.S)
 status_css=layout.CSS.split('#computer-status{',1)[1].split('.table-wrap,',1)[0]
 technical='<style>#computer-status{'+status_css+'@media(max-width:700px){.status-heading{display:block}.status-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.status-tile strong{font-size:17px}.status-tile:nth-child(even){border-right:0}#computer-status{padding:15px}}@media print{.status-grid{grid-template-columns:repeat(4,minmax(0,1fr))}.status-tile strong{font-size:12pt}.status-heading h2{font-size:15pt}.status-foot{display:none}}</style>'+technical
 import mesh_study_control_panel
 importlib.reload(mesh_study_control_panel)
 technical=technical+mesh_study_control_panel.panel()
 controls='<details id="local-controls" class="dashboard-disclosure"><summary><b>Local calculation controls</b> — inspect a mesh, prepare a queue and start explicitly</summary>'+(R/'manual_control_panel.html').read_text(encoding='utf8')+'</details>'
 mesh_panel=''
 try:
  import importlib.util
  candidates=[Path(r'C:\\Users\\ThinkPad\\Documents\\ChatGPT\\ntnu science\\mobile-dashboard\\local_mesh_dashboard.py'),Path(r'C:\\Users\\ThinkPad\\Documents\\ChatGPT\\ntnu science\\mobile-dashboard-mesh-gci\\local_mesh_dashboard.py')]
  bridge=next((p for p in candidates if p.is_file()),None)
  if bridge:
   spec=importlib.util.spec_from_file_location('ntnu_local_mesh_dashboard',bridge);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
   mesh_panel=module.panel()
 except (ImportError,OSError):pass
 import mesh_field_preview_panel
 importlib.reload(mesh_field_preview_panel)
 mesh_panel=mesh_panel+mesh_field_preview_panel.panel()
 style='<style>.dashboard-disclosure{border:1px solid #cbd7df;margin:16px 0;padding:16px;background:#fff}.dashboard-disclosure>summary{cursor:pointer;line-height:1.5}.dashboard-disclosure[open]>summary{margin-bottom:16px}.dashboard-stage-tabs{display:flex;gap:8px;margin:16px 0;flex-wrap:wrap}.dashboard-stage-tabs button{font:inherit;padding:10px 18px;background:white;border:1px solid #9ab1c0;cursor:pointer}.dashboard-stage-tabs button[aria-pressed="true"]{background:#143d54;color:white}.stage-panel[hidden]{display:none}.dashboard-disclosure .manual-control-panel{margin-top:16px}@media print{.dashboard-stage-tabs,.local-controls-wrapper{display:none}.dashboard-disclosure{break-inside:avoid}.stage-panel[hidden]{display:none}}</style>'
 tabs='<div class="dashboard-stage-tabs" role="group" aria-label="Analysis stage"><button type="button" data-stage="waves" aria-pressed="true">Waves</button><button type="button" data-stage="mesh" aria-pressed="false">Mesh assessment</button></div>'
 stage='<div class="stage-panel" data-stage-panel="waves">'+live_html+'</div><div class="stage-panel" data-stage-panel="mesh" hidden>'+mesh_panel+'</div>'
 stage_js='<script>document.querySelectorAll("[data-stage]").forEach(function(b){b.addEventListener("click",function(){document.querySelectorAll("[data-stage]").forEach(function(x){x.setAttribute("aria-pressed",x===b?"true":"false")});document.querySelectorAll("[data-stage-panel]").forEach(function(p){p.hidden=p.dataset.stagePanel!==b.dataset.stage});try{localStorage.setItem("ntnu-analysis-stage",b.dataset.stage)}catch(e){}})});try{var stage=localStorage.getItem("ntnu-analysis-stage");if(stage==="mesh")document.querySelectorAll("[data-stage]")[1].click()}catch(e){}</script>'
 stage_js=stage_js.replace('</script>','function showLinkedStage(){if([\"#computer-status\",\"#mesh-study-current\",\"#mesh-study-frame\",\"#mesh-field-preview\"].includes(location.hash)){document.querySelector(\"[data-stage=mesh]\").click()}}window.addEventListener(\"hashchange\",showLinkedStage);showLinkedStage();</script>')
 for name in ('dashboard.html','professor_dashboard.html'):
  if not publish and freeze.get('sha256',{}).get(name) and c.digest(B/name)!=freeze['sha256'][name]:raise RuntimeError('Meeting original changed; do not conceal the change.')
  page=(base/name).read_text(encoding='utf8')
  doc=layout.Document(page);main=next(n for n in doc.root.walk() if n.tag=='main')
  old_status=doc.find('computer-status')
  if old_status and old_status.parent:old_status.parent.children.remove(old_status)
  historical=''.join(child if isinstance(child,str) else child.render() for child in main.children)
  archived='<details class="dashboard-disclosure"><summary><b>Earlier mesh and numerical studies</b> — preserved evidence and definitions</summary>'+historical+'</details>'
  catalog_block='<details class="dashboard-disclosure"><summary><b>Wave cases and parameters</b></summary>'+catalog+'</details>'
  notice='' if publish else '<p><b>WORKING COPY</b> — meeting originals remain preserved.</p>'
  main.children=[style,notice,technical,'<div class="local-controls-wrapper">'+controls+'</div>',tabs,stage,archive_html,catalog_block,archived,stage_js]
  page=doc.root.render()
  stamp=datetime.datetime.now().astimezone().strftime('%d %b %Y · %H:%M:%S %Z')
  page=re.sub(r'Updated 30 Oct 2026[^<]*','Dashboard build '+stamp,page,count=1)
  page=re.sub(r'Research discussion · [^<]*','Dashboard build '+stamp+' · each saved field retains its own timestamp',page,count=1)
  page=page.replace('</head>','<style>.hero{padding:18px 28px!important}.hero h1{font-size:28px!important;line-height:1.2!important;margin:8px 0!important}.engineering-header{gap:20px!important}.section-schematic svg{max-height:180px!important}.hero .lead,.hero p{margin:8px 0!important}@media(max-width:700px){.hero{padding:14px!important}.hero h1{font-size:23px!important}.section-schematic svg{max-height:165px!important}}</style></head>',1)
  nav_script='<script>document.querySelectorAll("nav a").forEach(function(a){var t=a.textContent.toLowerCase();if(t.includes("mesh")){a.textContent="Mesh assessment";a.href="#mesh-field-preview";a.onclick=function(e){e.preventDefault();document.querySelectorAll("[data-stage]")[1].click();document.querySelector("[data-stage-panel=mesh]").scrollIntoView({behavior:"smooth"})}}else if(t.includes("wave")){a.textContent="Waves";a.href="#live-analysis";a.onclick=function(e){e.preventDefault();document.querySelectorAll("[data-stage]")[0].click();document.querySelector("#live-analysis").scrollIntoView({behavior:"smooth"})}}else if(t.includes("case definition")){a.textContent="Computer & controls";a.href="#computer-status"}else if(t.includes("sources")){a.textContent="Archive";a.href="#case-archive"}});</script>'
  page=page.replace('</body>',nav_script+'</body>',1)

  if name=='dashboard.html' and mesh_panel and hasattr(module,'correct_legacy_lift_display'):
   page=module.correct_legacy_lift_display(page)
  page=page.replace('if(enabled&&!document.hidden)','if(enabled&&!document.hidden&&!document.activeElement.closest("#manual-control-panel"))')
  page=page.replace('<b>Last saved wave calculation:</b>','<b>Historical no-foil diagnostic (R14):</b>').replace('<b>Case-matched review:</b>','<b>Review of that historical no-foil diagnostic:</b>')
  if name=='professor_dashboard.html':
   page=page.replace('<article class="print-report">','<article class="print-report"><section class="print-page">'+technical+'</section><section class="print-page">'+live_html+archive_html+'</section>',1)
  for destination in ([B,D] if publish else [D]):
   tmp=destination/(name+'.'+str(os.getpid())+'.tmp');tmp.write_text(page,encoding='utf8')
   import time
   for retry in range(20):
    try:os.replace(tmp,destination/name);break
    except PermissionError:
     if retry==19:raise
     time.sleep(.05)
 (D/'build.json').write_text(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),originals_unchanged=not publish,lifecycle='active_only_live_persistent_archive')),encoding='utf8')
if __name__=='__main__':build();print('Built lifecycle dashboard views.')
