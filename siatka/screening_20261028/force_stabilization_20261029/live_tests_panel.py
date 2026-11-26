"""Visible, separate progress for temporal experiments and CPU mesh preparation."""
import json,datetime,time,html
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029';T=R/'temporal_order_20261029'
def read(p,default=None):
 try:return json.loads(p.read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return default
def snapshot():
 from temporal_reference_panel import comparison
 original_comparison=comparison()
 state=read(R/'temporal_validation_state.json',{});cases=[]
 for j in read(R/'temporal_validation_plan.json',{}).get('jobs',[]):
  out=T/j['id'];progress=read(out/'progress.json',{});done=read(out/'experiment_result.json',{});proc=read(out/'process.json',{})
  t=progress.get('time_s',j['start']);pct=max(0,min(100,100*(t-j['start'])/(j['target']-j['start'])))
  status='Completed' if done else ('Stopped for review' if state.get('status')=='needs_review' and state.get('active')==j['id'] else ('Running' if progress else 'Loading model') if state.get('active')==j['id'] else 'Queued')
  if done:pct=100;t=done['end_s']
  age=time.time()-(out/'progress.json').stat().st_mtime if (out/'progress.json').exists() else None
  cases.append({'id':j['id'],'short':j['id'].split('_')[0],'order':j['order'],'dt_ms':j['dt']*1000,'inner':j['inner'],'status':status,'time_s':t,'start_s':j['start'],'target_s':j['target'],'progress_pct':pct,'latest_CD':progress.get('CD'),'latest_CL':progress.get('CL_total'),'elapsed_wall_s':time.time()-proc['start_unix'] if proc and not done else read(out/'controller_result.json',{}).get('elapsed_wall_s'),'last_sample_age_s':age,'result':done})
 builds=[]
 for n in range(2,16):
  mesh=f'M{n:02d}';control=read(R/(mesh+'_build_controller.json'),{});result=read(R/(mesh+'_build_result.json'),{});st=read(Q/(mesh+'_build')/'build_status.json',{})
  if not control:continue
  active=control.get('status') in ['waiting_for_small_wave_audit','building_on_two_CPU','building']
  if not active and control.get('status')!='verified_ready_pending_temporal_review':continue
  stage={'meshing':'Generating source mesh','exact_extrusion':'Exact extrusion and mesh audit','verified':'Mesh audit finished'}.get(st.get('status'),'Preparing')
  if control.get('status')=='waiting_for_small_wave_audit':stage='Waiting for the small wave-reference audit'
  if result.get('status')=='needs_review':stage='Stopped for review'
  if control.get('status')=='verified_ready_pending_temporal_review':stage='Mesh ready; awaiting temporal review'
  start=control.get('started_at',st.get('started_at'));elapsed=None
  if start:
   try:elapsed=(datetime.datetime.now().astimezone()-datetime.datetime.fromisoformat(start)).total_seconds()
   except ValueError:pass
  builds.append({'mesh':mesh,'stage':stage,'workers':2 if active else 0,'elapsed_wall_s':elapsed,'cells':result.get('cells',st.get('cells')),'error':result.get('error')})
 return {'conservation_probe':read(R/'conservation_probe_state.json',{}),'original_comparison':original_comparison,'updated_at':datetime.datetime.now().astimezone().isoformat(),'temporal_state':state.get('status'),'active_temporal':state.get('active'),'temporal_cases':cases,'cpu_builds':builds,'maximum_mesh_number':read(R/'mesh_selection_plan.json',{}).get('maximum_mesh_number',15)}
def f(x,n=3):return '—' if x is None else f'{x:.{n}f}'
def elapsed(x):return '—' if x is None else f'{x/60:.1f} min'
def panel(data):
 from temporal_reference_panel import brief
 cases=data['temporal_cases'];active=next((c for c in cases if c['id']==data['active_temporal'] and c['status']!='Completed'),None)
 s='<div class="card" id="live-tests"><h3>Live tests</h3><p><b>Night sequence:</b> 1. Calculation settings → 2. Mesh selection → 3. C01 / W01 / W02 waves.</p><p class="muted">Separate experiments continue after mesh-force settling. This panel refreshes with the report.</p><div class="live-test-grid">'
 if active:
  a=active;settings=('2nd' if a['order']=='SECOND_ORDER' else '1st')+' order · '+f(a['dt_ms'],1)+' ms · '+str(a['inner'])+' inner iterations'
  s+='<div class="live-test-box"><b>GPU · '+a['short']+' · '+a['status']+'</b><p>'+settings+'</p><progress aria-label="Temporal test progress" value="'+f(a['progress_pct'],2)+'" max="100"></progress><p><b>'+f(a['progress_pct'],1)+'%</b> · t = '+f(a['time_s'])+' / '+f(a['target_s'])+' s<br>Additional interval: '+f(a['time_s']-a['start_s'])+' / '+f(a['target_s']-a['start_s'])+' s</p><small>Elapsed including loading: '+elapsed(a['elapsed_wall_s'])+' · last sample '+f(a['last_sample_age_s'],0)+' s ago</small></div>'
 else:s+='<div class="live-test-box"><b>GPU · time-order comparison</b><p>'+html.escape(data.get('temporal_state') or 'Prepared')+'</p></div>'
 if data['cpu_builds'] and not (R/'calm_solver_configuration_decision.json').exists():
  for a in data['cpu_builds']:
   s+='<div class="live-test-box"><b>CPU · '+a['mesh']+' · '+a['stage']+'</b><p>'+('2 CPU workers · elapsed '+elapsed(a['elapsed_wall_s']) if a['workers'] else 'CPU build completed; GPU flow run not started')+'</p><p>Coarser remote domain; protected middle region and retained foil/prism controls.</p><small>'+('Cells: '+str(a['cells']) if a['cells'] else 'Cell count becomes available after mesh generation.')+'</small></div>'
 else:s+='<div class="live-test-box"><b>CPU · mesh preparation</b><p>Mesh construction is complete; current flow tests are shown above.</p></div>'
 s+='</div><div class="table-wrap"><table class="temporal-live-table"><thead><tr><th>Test</th><th>Time scheme / step</th><th>Inner iterations</th><th>Status</th><th>Progress</th><th>Latest CD</th><th>Latest CL</th></tr></thead><tbody>'
 for a in cases:
  scheme=('2nd' if a['order']=='SECOND_ORDER' else '1st')+' order / '+f(a['dt_ms'],1)+' ms'
  s+='<tr><td title="'+html.escape(a['id'])+'">'+a['short']+'</td><td>'+scheme+'</td><td>'+str(a['inner'])+'</td><td>'+a['status']+'</td><td>'+f(a['progress_pct'],1)+'%</td><td>'+f(a['latest_CD'],6)+'</td><td>'+f(a['latest_CL'],6)+'</td></tr>'
 s+='</tbody></table></div>'+conservation_note(data.get('conservation_probe',{}))+brief(data.get('original_comparison'))+'<p class="muted">T01 → T02 tests time order; T02 → T03 tests the time step; T02 → T04 tests 10 versus 20 inner iterations. All use the same M04 starting state and additional 0.6 s. Values above are the latest samples; <a href="#temporal-validation">accepted window means and comparisons appear below</a>.</p><p>Next design study: local LE/TE refinement with a coarser middle chord. Campaign limit: <b>M'+str(data['maximum_mesh_number'])+'</b>.</p></div>'
 return '<style>#live-tests{scroll-margin-top:90px;border-left:4px solid #0072b2}.live-test-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:16px 0}.live-test-box{border:1px solid #d7e1e6;padding:16px}.live-test-box p{margin:10px 0}.live-test-box progress{width:100%;height:13px;accent-color:#0072b2}.temporal-live-table th{text-transform:none;letter-spacing:0}@media(max-width:650px){.live-test-grid{grid-template-columns:1fr}}</style>'+s

def conservation_note(state):
 if not state:return ''
 labels={'waiting_for_temporal_tests':'Queued after T01–T04','starting':'Loading copied checkpoint','running':'Running','completed_pending_review':'Completed; calm-screen settings selected' if (R/'calm_solver_configuration_decision.json').exists() else 'Completed; reviewing balance','needs_review':'Reviewing diagnostics','waiting_for_temporal_review':'Waiting for temporal review','paused_by_marker':'Paused'}
 label=labels.get(state.get('status'),state.get('status','Prepared'));active=state.get('active')
 s='<p class="conservation-note"><b>Mass-conservation check · '+html.escape(label)+'</b><br>Two matched 40-step continuations record boundary mass flux and mass accumulation: 20 versus 10 inner iterations. GPU tests run sequentially.'
 if active:
  p=read(R/'conservation_probe_20261029'/active/'progress.json',{})
  if p:s+='<br>'+html.escape(active)+': '+f(min(100,100*p.get('steps',0)/40),1)+'% · t = '+f(p.get('time_s'))+' s.'
 return s+'</p>'
