"""Settled mesh comparisons. A passing time history alone never selects a mesh."""
import csv,json,math,statistics,datetime,html,base64,hashlib,os
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
def read(p,d=None):
 try:return json.loads(p.read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return d
def timing_summary(folder,window):
 result={'wall_s_per_step_median':None,'wall_s_per_step_mean':None,'solver_wall_s_per_physical_s':None,'timing_intervals':0,'timing_window_start_s':None,'timing_window_end_s':None,'observed_inner_iterations_per_step':None}
 try:
  with (folder/'history.csv').open(encoding='utf-8-sig',newline='') as stream:
   data=[{k:float(v) for k,v in r.items() if k and v is not None and v!=''} for r in csv.DictReader(stream)]
  spans=[]
  for a,b in zip(data,data[1:]):
   if a['physical_time_s']<window['start']-1e-8 or b['physical_time_s']>window['end']+1e-8:continue
   ds=b['step']-a['step'];dw=b['wall_seconds']-a['wall_seconds'];dt=b['physical_time_s']-a['physical_time_s']
   if ds!=1 or dt<=0 or dw<=0 or not all(math.isfinite(x) for x in (ds,dw,dt)):continue
   spans.append((dw,dt,a['physical_time_s'],b['physical_time_s'],(b['iteration']-a['iteration'])/ds))
  if len(spans)>=5:
   result.update(wall_s_per_step_median=statistics.median(x[0] for x in spans),
    wall_s_per_step_mean=statistics.mean(x[0] for x in spans),
    solver_wall_s_per_physical_s=sum(x[0] for x in spans)/sum(x[1] for x in spans),
    timing_intervals=len(spans),timing_window_start_s=spans[0][2],timing_window_end_s=spans[-1][3],
    observed_inner_iterations_per_step=statistics.median(x[4] for x in spans))
 except (OSError,ValueError,KeyError):pass
 return result

def plot_signature(rows):
 keys=['id','cells','family','time_s','window_start_s','Fx_pressure_N','Fx_viscous_N','Fx_total_N','wall_s_per_step_median','wall_s_per_step_mean']
 return hashlib.sha256(json.dumps([{k:r.get(k) for k in keys} for r in rows],sort_keys=True).encode()).hexdigest()

def assess(persist=True):
 live=read(R/'live_summary.json',{});registry=read(R/'campaign_registry.json',{});jobs=read(R/'queue.json',[]);yp=read(R/'yplus_summary.json',{})
 rows=[]
 for c in registry.get('cases',[]):
  m=c['id'];matching=[j for j in jobs if j['id'].startswith(m+'_')]
  if not matching:continue
  folder=R/matching[-1]['id'];done=read(folder/'completed.json',{});acc=read(folder/'acceptance.json',{})
  if done.get('status')!='stabilized' and acc.get('status')!='settled':continue
  a=live.get('meshes',{}).get(m,{});windows=a.get('windows',[])
  if not windows:continue
  w=windows[-1];met=read(Q/m/'measurement.json',{}).get('metrics',{})
  family='low_yplus' if c.get('first_layer_um',999)<10 else 'wall_function'
  timing=timing_summary(folder,w)
  dp=w.get('pressure_drag_N',{}).get('mean');dv=w.get('viscous_drag_N',{}).get('mean');total=3855.6*w['CD']['mean']
  rows.append({'id':m,'cells':met['cell_count'],'family':family,'CD':w['CD']['mean'],'CL_total':w['CL_total']['mean'],'CL_dynamic':w['CL_total']['mean']-22.718189111947265/3855.6,'time_s':w['end'],'window_start_s':w['start'],'Fx_pressure_N':dp,'Fx_viscous_N':dv,'Fx_total_N':total,'force_balance_error_N':None if dp is None or dv is None else total-dp-dv,'yplus':yp.get(m,{}),**timing})
 rows.sort(key=lambda r:r['cells']);pairs=[]
 for i,a in enumerate(rows):
  for b in rows[i+1:]:
   delta={k:100*(a[k]-b[k])/abs(b[k]) for k in ['CD','CL_total']}
   force_delta={k:None if a.get(k) is None or b.get(k) is None or abs(b[k])<1e-12 else 100*(a[k]-b[k])/abs(b[k]) for k in ['Fx_pressure_N','Fx_viscous_N']}
   pairs.append({'coarse':a['id'],'fine':b['id'],'same_family':a['family']==b['family'],'delta_pct':delta,'force_component_delta_pct':force_delta,'force_component_delta_N':{k:None if a.get(k) is None or b.get(k) is None else a[k]-b[k] for k in force_delta},'within_1pct':all(abs(v)<=1 for v in delta.values())})
 candidates=[]
 for a in rows:
  finer=[b for b in rows if b['cells']>a['cells'] and b['family']==a['family']]
  if len(finer)<2:continue
  group=[a]+finer
  consistent=all(abs(100*(x[k]-y[k])/y[k])<=1 for i,x in enumerate(group) for y in group[i+1:] for k in ['CD','CL_total'])
  if consistent:candidates.append({'id':a['id'],'cells':a['cells'],'family':a['family'],'confirmed_by':[b['id'] for b in finer]})
 low=[c for c in candidates if c['family']=='low_yplus'];recommended=min(low,key=lambda c:c['cells']) if low else None
 decision={'updated_at':datetime.datetime.now().astimezone().isoformat(),'time_settling_pct':.5,'mesh_agreement_pct':1,'max_mesh_id':'M10','settled_results':rows,'comparisons':pairs,'candidates':candidates,'recommended_candidate':recommended,'status':'candidate_requires_final_quality_review' if recommended else 'collecting_refinement_evidence','waves_allowed':False,'method':'Final 0.2 s means; both CL,total and CD within 1% across candidate and at least two finer meshes in the same near-wall family. Prefer the resolved low-y+ family when wall-model sensitivity is material. Final wall-field and geometry review remains required.'}
 decision['timing_method']='Median and mean elapsed wall seconds between consecutive physical steps in the accepted final 0.2 s window. Mean includes recorded checkpoint/report overhead; median reduces its influence. Initialization and final exports outside this window are excluded. Other CPU activity can affect the observed times.'
 if persist:
  p=R/'mesh_convergence.json';tmp=p.with_name(p.name+f'.{os.getpid()}.tmp');tmp.write_text(json.dumps(decision,indent=2),encoding='utf-8');tmp.replace(p)
 return decision
def fmt(v,n=4):return '—' if v is None else f'{v:,.{n}f}'
def plot(rows,key,label):
 if not rows:return '<p class="muted">Waiting for settled results.</p>'
 W,H=530,265;L,B,T,RR=70,45,28,48
 xs=[r['cells']/1000 for r in rows];ys=[r[key] for r in rows];xmin,xmax=min(xs),max(xs);pad=max((max(ys)-min(ys))*.18,abs(max(ys))*.015,1e-5);ymin,ymax=min(ys)-pad,max(ys)+pad
 X=lambda v:L+(v-xmin)/(xmax-xmin or 1)*(W-L-RR)
 Y=lambda v:H-B-(v-ymin)/(ymax-ymin)*(H-T-B)
 s=f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{label} versus mesh cells" style="width:100%;height:auto;background:white"><text x="{L}" y="18" font-size="14">{label} · settled means</text>'
 for i in range(5):
  v=ymin+(ymax-ymin)*i/4;y=Y(v)
  s+=f'<path d="M{L} {y:.2f}H{W-RR}" stroke="#e0e5e8"/><text x="{L-8}" y="{y+4:.2f}" text-anchor="end" font-size="11">{v:.4f}</text>'
 for family,color in [('wall_function','#596870'),('low_yplus','#5267ad')]:
  rr=[r for r in rows if r['family']==family]
  if rr:
   path=' '.join(('M' if i==0 else 'L')+f'{X(r["cells"]/1000):.2f},{Y(r[key]):.2f}' for i,r in enumerate(rr))
   s+=f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1.5"/>'
   for r in rr:
    x,y=X(r['cells']/1000),Y(r[key]);s+=f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="{color}"/><text x="{x+5:.2f}" y="{y-7:.2f}" font-size="11" fill="{color}">{r["id"]}</text>'
 for i in range(5):
  v=xmin+(xmax-xmin)*i/4;x=X(v);s+=f'<text x="{x:.2f}" y="{H-B+20}" text-anchor="middle" font-size="11">{v:.0f}</text>'
 return s+f'<text x="{W/2}" y="{H-6}" text-anchor="middle" font-size="12">Cells [thousands]</text></svg>'
def html_section():
 d=assess();rows=d['settled_results'];trs=[]
 for p in d['comparisons']:
  kind='Refinement' if p['same_family'] else 'Wall-resolution comparison'
  status=('Within 1%' if p['within_1pct'] else 'Above 1%') if p['same_family'] else 'Different near-wall mesh'
  cells=[p['coarse']+' / '+p['fine'],kind,fmt(p['delta_pct']['CD'],2)+'%',fmt(p['delta_pct']['CL_total'],2)+'%']
  cells += [('—' if p['force_component_delta_pct'][k] is None else fmt(p['force_component_delta_pct'][k],2)+'%') for k in ['Fx_pressure_N','Fx_viscous_N']]
  cells += [status]
  trs.append('<tr>'+''.join('<td>'+v+'</td>' for v in cells)+'</tr>')
 table_rows=[]
 for r in rows:
  values=[r['id'],f'{r["cells"]:,}',fmt(r['Fx_pressure_N'],3),fmt(r['Fx_viscous_N'],3),fmt(r['Fx_total_N'],3),fmt(r['wall_s_per_step_median'],3),fmt(r['wall_s_per_step_mean'],3),str(r['timing_intervals'])]
  table_rows.append('<tr>'+''.join('<td>'+v+'</td>' for v in values)+'</tr>')
 chosen=d['recommended_candidate']
 decision=('Candidate: '+chosen['id']+'; finer confirmations: '+', '.join(chosen['confirmed_by'])+'. Final field review pending.') if chosen else 'No mesh selected yet. Waiting for consistent finer-mesh results.'
 meta=read(R/'mesh_force_cost_provenance.json',{})
 if meta.get('signature')==plot_signature(rows) and (R/'mesh_force_cost.png').is_file():
  graphic='<figure id="mesh-force-cost"><img alt="Settled pressure and viscous drag components, and measured wall time per physical step versus mesh cell count" src="data:image/png;base64,'+base64.b64encode((R/'mesh_force_cost.png').read_bytes()).decode()+'"><figcaption>Final 0.2 s averages. Pressure and viscous forces act in +X on the 20 mm slice. Runtime points show the median elapsed seconds per physical step; the table also reports the mean. Click to enlarge.</figcaption></figure>'
  links=[]
  for ext,mime,label in [('csv','text/csv','Download comparison CSV'),('svg','image/svg+xml','Download figure SVG')]:
   asset=R/('mesh_force_cost.'+ext)
   if asset.is_file():links.append('<a class="btn" download="'+asset.name+'" href="data:'+mime+';base64,'+base64.b64encode(asset.read_bytes()).decode()+'">'+label+'</a>')
  graphic+='<div class="downloads">'+''.join(links)+'</div>'
 else:graphic='<div id="mesh-force-cost" class="pending">Force-component and runtime figure is being refreshed from the accepted results.</div>'
 return '<section id="mesh-selection"><div class="section-head"><h2>Mesh convergence and selection</h2></div><p><b>Target: ≤1% difference in both mean CD and mean CL.</b> Select the lightest mesh supported by two finer comparable meshes. Stop adding cases once supported; maximum M10. Force settling remains a separate 0.5% test.</p><div class="callout">'+decision+' Wave runs remain on hold.</div><div class="grid2">'+plot(rows,'CD','CD')+plot(rows,'CL_total','CL, total')+'</div><p class="muted">Lines connect the same near-wall family. Grey: wall-function spacing; blue: fine near-wall spacing. Only settled means are plotted.</p><div class="table-wrap"><table id="mesh-pair-comparison"><thead><tr><th>Coarse / fine</th><th>Comparison</th><th>Δ CD</th><th>Δ CL</th><th>Δ Fx, pressure</th><th>Δ Fx, viscous</th><th>Assessment</th></tr></thead><tbody>'+''.join(trs)+'</tbody></table></div><p class="muted">Signed differences = (coarse − fine) / |fine| × 100%. Force components help explain the total-drag difference; the agreed 1% acceptance test applies to CD and CL.</p><h3>Drag components and computing time</h3>'+graphic+'<div class="table-wrap"><table id="mesh-cost-table"><thead><tr><th>Mesh</th><th>Cells</th><th>Mean Fx, pressure [N]</th><th>Mean Fx, viscous [N]</th><th>Mean Fx, total [N]</th><th>Median time / step [s]</th><th>Mean time / step [s]</th><th>Timed steps</th></tr></thead><tbody>'+''.join(table_rows)+'</tbody></table></div><p class="muted">One physical step advances the solution by 1 ms with 20 inner iterations. Timing uses consecutive steps in each accepted final 0.2 s window. The mean includes recorded checkpoint and reporting overhead; the median reduces its influence. Initialization and final field exports outside the window are excluded. Other CPU tasks can affect timings. These are observed run costs, not isolated hardware benchmarks.</p></section>'
if __name__=='__main__':print(json.dumps(assess(),indent=2))
