"""Campaign-wide engineering parameter matrix and independent CFL review."""
import json,csv,datetime,html,base64
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
def read(path,default=None):
 try:return json.loads(path.read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return default
def f(v,n=3):return 'Pending' if v is None else f'{v:,.{n}f}'
def growth(h,N,T):
 lo,hi=1.,2.
 for _ in range(70):
  mid=(lo+hi)/2
  if h*(mid**N-1)/(mid-1)>T:hi=mid
  else:lo=mid
 return (lo+hi)/2
def builder_status(mesh):
 st=read(Q/(mesh+'_build')/'build_status.json',{});fail=read(R/(mesh+'_build_result.json'),{})
 if fail.get('status')=='needs_review':return 'Build needs review'
 if st.get('status') in ['meshing','exact_extrusion']:
  elapsed=''
  try:elapsed=f" · {(datetime.datetime.now().astimezone()-datetime.datetime.fromisoformat(st['started_at'])).total_seconds()/60:.0f} min"
  except (KeyError,ValueError):pass
  return ('Generating mesh'+elapsed) if st['status']=='meshing' else 'Extrusion / mesh audit'
 return 'Preparing'
def matrix(live):
 from mesh_definition import definitions,FIELDS,delta_panel
 defs=definitions()
 reg=sorted(read(R/'campaign_registry.json',{}).get('cases',[]),key=lambda c:c['id'])
 jobs=read(R/'queue.json',[]);pending=read(R/'mesh_selection_jobs.json',[]);ys=read(R/'yplus_summary.json',{})
 cost={a['id']:a for a in read(R/'mesh_convergence.json',{}).get('settled_results',[])}
 field=read(R/'mesh_budget_cfl.json',{}).get('cases',{});columns=[]
 for c in reg:
  m=c['id'];d=read(Q/m/'design.json',{});metric=read(Q/m/'measurement.json',{}).get('metrics',{})
  y=ys.get(m,{});last=live.get('meshes',{}).get(m,{}).get('last',{})
  matching=[j for j in jobs if j['id'].startswith(m+'_')];j=matching[-1] if matching else next((j for j in pending if j['id'].startswith(m+'_')),{})
  folder=R/j['id'] if j else None;setup=read(folder/'setup.json',{}) if folder else {}
  done=read(folder/'completed.json',{}) if folder else {}
  accepted=m in cost;active=live.get('queue',{}).get('active')==j.get('id') and live.get('queue',{}).get('status')=='running'
  status='Settled' if accepted else ('Running' if active else ('Ready for flow' if (Q/m/'mesh_build.exit.json').exists() else builder_status(m)))
  T=d.get('total_prism_m',.01546);h=c['first_layer_um'];N=c['layers']
  ci=last.get('interface_max_CFL');co=last.get('max_CFL');dt=last.get('dt_s',setup.get('dt_s',j.get('dt')))
  nsub=None
  if folder and (folder/'vof_substeps.csv').exists():
   with (folder/'vof_substeps.csv').open() as s:
    rr=list(csv.DictReader(s))
   if rr:nsub=float(rr[-1]['VOF_substeps'])
  check='No flow data' if ci is None else 'Test pending'
  if done.get('status')=='stability_guard':status='Stopped: startup guard'
  columns.append({'mesh':m,'values':[
   status, f"{metric['cell_count']:,}" if 'cell_count' in metric else 'Pending',
   'Low y+' if h<10 else 'Wall-function',
   f(h),str(N),f(growth(h*1e-6,N,T)),f(T*1000,2),
   f(y.get('area_weighted_p95')),f(y.get('area_fraction_pct',{}).get('<1'),2),
   f(y.get('snapshot_time_s')),f(dt*1000 if dt is not None else None),
   ('1st-order implicit' if setup.get('order',j.get('order'))=='FIRST_ORDER' else '2nd-order implicit' if setup.get('order',j.get('order'))=='SECOND_ORDER' else 'Pending'),
   f(co),f(ci),f(field.get(m,{}).get('cfl',{}).get('interface_cells',{}).get('p99')),
   f(nsub,0),check,f(cost.get(m,{}).get('wall_s_per_step_median'))]})
 labels=['Status','Cell count','Near-wall family','First full layer [µm]','Prism layers','Equivalent geometric growth*','Total prism thickness [mm]','Wall y+ · area p95','Wall area with y+ < 1 [%]','Accepted field time [s]','Flow time step [ms]','Temporal scheme','Global convective CFL · latest','Interface convective CFL · latest','Interface CFL p99 · saved field','VOF substeps · API-reported','Time-step accuracy','Median computing time / step [s]']
 extra_labels=[label for key,label in FIELDS]
 labels[3:3]=extra_labels
 for col in columns:
  spec=defs.get(col['mesh'],{})
  col['values'][3:3]=[f(spec.get(key)*1000 if spec.get(key) is not None else None) for key,label in FIELDS]
 css='<style>#mesh-parameters{scroll-margin-top:100px}#mesh-parameters table{min-width:1050px;width:100%;table-layout:fixed}#mesh-parameters thead th:first-child{width:205px}#mesh-parameters th,#mesh-parameters td{padding:9px 12px;text-transform:none;letter-spacing:0}#mesh-parameters tbody th{position:sticky;left:0;z-index:2;background:white;white-space:normal;font-size:12px;color:#263b48}#mesh-parameters td{text-align:right;white-space:normal;overflow-wrap:anywhere}@media(max-width:600px){#mesh-parameters table{min-width:1000px}#mesh-parameters thead th:first-child{width:160px}#mesh-parameters th,#mesh-parameters td{padding:8px!important}}#mesh-parameters thead th{text-align:right}#mesh-parameters tr.break-row>*{border-top:2px solid #aebcc5}.cfl-review{color:#8d4d0b;font-weight:600}</style>'
 css+='<style>#mesh-parameters table{min-width:'+str(max(1050,205+110*len(columns)))+'px}</style>'
 s=css+'<div class="card" id="mesh-parameters"><h3>Mesh parameters and time resolution</h3><p class="muted">Scroll the table horizontally on a narrow screen; the parameter column stays visible.</p><div class="table-wrap"><table><thead><tr><th>Parameter</th>'+''.join('<th>'+c['mesh']+'</th>' for c in columns)+'</tr></thead><tbody>'
 shared=[]
 for i,label in enumerate(labels):
  if label in ['Status','Time-step accuracy']:continue
  vals=[c['values'][i] for c in columns]
  if len(set(vals))==1:
   if vals[0]!='Pending':shared.append((label,vals[0]))
   continue
  s+='<tr'+(' class="break-row"' if label in ['Outer base size [mm]','First full layer [µm]','Wall y+ · area p95','Flow time step [ms]','Median computing time / step [s]'] else '')+'><th scope="row">'+html.escape(label)+'</th>'+''.join('<td>'+html.escape(c['values'][i])+'</td>' for c in columns)+'</tr>'
 s+='</tbody></table></div>'
 shared += [('Surface growth ratio','1.2'),('Span','20 mm; one cell through the span'),('Near-foil refinement box [m]','x: −0.6 to 3.0; z: −0.6 to 0.6'),('Free-surface refinement box [m]','x: −11.9 to 30.94; z: 1.6 to 2.4')]
 s+='<details id="shared-mesh-settings"><summary>Shared settings · shown once</summary><dl>'+''.join('<dt>'+html.escape(k)+'</dt><dd>'+html.escape(v)+'</dd>' for k,v in shared)+'</dl></details>'
 s+='<p class="muted">The matrix shows parameters that differ. Identical settings appear once below it. All current campaign meshes; new admitted variants appear automatically. Size controls are read from the actual build macros. Source hashes are recorded in the evidence snapshot. Prism settings are nominal. Wall y+ statistics use accepted saved fields; running-case CFL uses the latest recorded physical step. *Growth is the equivalent geometric-series ratio from first height, count and total thickness.</p>'
 s+='<p class="muted">Time-step and order comparisons are still in progress. Interface CFL &gt; 1 requires checking the VOF transport strategy and substeps. These CFL values use the full flow step and the mask 0.01 &lt; water volume fraction &lt; 0.99; they are not the solver-specific VOF substep criterion. A finite, settled force history alone does not establish time accuracy.</p></div>'
 return s+delta_panel(defs)
def optimization():
 from mesh_optimization_panel import panel
 return panel()

def temporal():
 from temporal_reference_panel import panel
 return panel()
