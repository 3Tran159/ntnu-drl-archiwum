from pathlib import Path
import py_compile
R=Path(__file__).resolve().parent
p=R/'build_manual_dashboard_copy.py';s=p.read_text(encoding='utf8')
start=s.index('def build():')
s=s[:start]+'''def build():
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
 controls='<details id="local-controls" class="dashboard-disclosure"><summary><b>Local calculation controls</b> — inspect a mesh, prepare a queue and start explicitly</summary>'+(R/'manual_control_panel.html').read_text(encoding='utf8')+'</details>'
 mesh_panel=''
 try:
  import importlib.util
  candidates=[Path(r'C:\\\\Users\\\\ThinkPad\\\\Documents\\\\ChatGPT\\\\ntnu science\\\\mobile-dashboard\\\\local_mesh_dashboard.py'),Path(r'C:\\\\Users\\\\ThinkPad\\\\Documents\\\\ChatGPT\\\\ntnu science\\\\mobile-dashboard-mesh-gci\\\\local_mesh_dashboard.py')]
  bridge=next((p for p in candidates if p.is_file()),None)
  if bridge:
   spec=importlib.util.spec_from_file_location('ntnu_local_mesh_dashboard',bridge);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
   mesh_panel=module.panel()
 except (ImportError,OSError):pass
 style='<style>.dashboard-disclosure{border:1px solid #cbd7df;margin:16px 0;padding:16px;background:#fff}.dashboard-disclosure>summary{cursor:pointer;line-height:1.5}.dashboard-disclosure[open]>summary{margin-bottom:16px}.dashboard-stage-tabs{display:flex;gap:8px;margin:16px 0;flex-wrap:wrap}.dashboard-stage-tabs button{font:inherit;padding:10px 18px;background:white;border:1px solid #9ab1c0;cursor:pointer}.dashboard-stage-tabs button[aria-pressed="true"]{background:#143d54;color:white}.stage-panel[hidden]{display:none}.dashboard-disclosure .manual-control-panel{margin-top:16px}@media print{.dashboard-stage-tabs,.local-controls-wrapper{display:none}.dashboard-disclosure{break-inside:avoid}.stage-panel[hidden]{display:none}}</style>'
 tabs='<div class="dashboard-stage-tabs" role="group" aria-label="Analysis stage"><button type="button" data-stage="waves" aria-pressed="true">Waves</button><button type="button" data-stage="mesh" aria-pressed="false">Mesh assessment</button></div>'
 stage='<div class="stage-panel" data-stage-panel="waves">'+live_html+'</div><div class="stage-panel" data-stage-panel="mesh" hidden>'+mesh_panel+'</div>'
 stage_js='<script>document.querySelectorAll("[data-stage]").forEach(function(b){b.addEventListener("click",function(){document.querySelectorAll("[data-stage]").forEach(function(x){x.setAttribute("aria-pressed",x===b?"true":"false")});document.querySelectorAll("[data-stage-panel]").forEach(function(p){p.hidden=p.dataset.stagePanel!==b.dataset.stage});try{localStorage.setItem("ntnu-analysis-stage",b.dataset.stage)}catch(e){}})});try{var stage=localStorage.getItem("ntnu-analysis-stage");if(stage==="mesh")document.querySelector(\'[data-stage="mesh"]\').click()}catch(e){}</script>'
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
  page=page.replace('if(enabled&&!document.hidden)','if(enabled&&!document.hidden&&!document.activeElement.closest("#manual-control-panel"))')
  page=page.replace('<b>Last saved wave calculation:</b>','<b>Historical no-foil diagnostic (R14):</b>').replace('<b>Case-matched review:</b>','<b>Review of that historical no-foil diagnostic:</b>')
  if name=='professor_dashboard.html':
   page=page.replace('<article class="print-report">','<article class="print-report"><section class="print-page">'+technical+live_html+archive_html+'</section>',1)
  for destination in ([B,D] if publish else [D]):
   tmp=destination/(name+'.'+str(os.getpid())+'.tmp');tmp.write_text(page,encoding='utf8');os.replace(tmp,destination/name)
 (D/'build.json').write_text(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),originals_unchanged=not publish,lifecycle='active_only_live_persistent_archive')),encoding='utf8')
if __name__=='__main__':build();print('Built lifecycle dashboard views.')
'''
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
print('Builder updated.')
