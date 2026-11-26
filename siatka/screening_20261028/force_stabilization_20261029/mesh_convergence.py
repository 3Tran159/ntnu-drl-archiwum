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

def resolution_refines(fine,coarse,defs):
 """A finer confirmation must resolve every controlled direction at least as finely."""
 a,b=defs.get(fine,{}),defs.get(coarse,{})
 size_keys=['base_m','foil_target_m','foil_min_m','global_min_m','near_foil_m','free_surface_m','first_layer_um']
 if any(a.get(k) is None or b.get(k) is None for k in size_keys+['layers','total_prism_mm']):return False
 if abs(a['total_prism_mm']-b['total_prism_mm'])>1e-7:return False
 if any(a[k]>b[k]*(1+1e-8) for k in size_keys) or a['layers']<b['layers']:return False
 return any(a[k]<b[k]*(1-1e-8) for k in size_keys) or a['layers']>b['layers']

def assess(persist=True):
 from mesh_definition import definitions
 defs=definitions()
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
   pairs.append({'coarse':a['id'],'fine':b['id'],'same_family':a['family']==b['family'],'finer_in_all_controls':a['family']==b['family'] and resolution_refines(b['id'],a['id'],defs),'delta_pct':delta,'force_component_delta_pct':force_delta,'force_component_delta_N':{k:None if a.get(k) is None or b.get(k) is None else a[k]-b[k] for k in force_delta},'within_1pct':all(abs(v)<=1 for v in delta.values())})
 candidates=[]
 for a in rows:
  finer=[b for b in rows if b['cells']>a['cells'] and b['family']==a['family'] and resolution_refines(b['id'],a['id'],defs)]
  if len(finer)<2:continue
  group=[a]+finer
  consistent=all(abs(100*(x[k]-y[k])/y[k])<=1 for i,x in enumerate(group) for y in group[i+1:] for k in ['CD','CL_total'])
  if consistent:candidates.append({'id':a['id'],'cells':a['cells'],'family':a['family'],'confirmed_by':[b['id'] for b in finer]})
 low=[c for c in candidates if c['family']=='low_yplus'];recommended=min(low,key=lambda c:c['cells']) if low else None
 decision={'updated_at':datetime.datetime.now().astimezone().isoformat(),'time_settling_pct':.5,'mesh_agreement_pct':1,'max_mesh_id':'M15','settled_results':rows,'comparisons':pairs,'candidates':candidates,'recommended_candidate':recommended,'status':'candidate_requires_final_quality_review' if recommended else 'collecting_refinement_evidence','waves_allowed':False,'method':'Final 0.2 s means; both CL,total and CD within 1% across the candidate and at least two finer comparable meshes in the same near-wall family. Each confirming mesh must have no larger nominal outer/surface/zone/first-layer size and no fewer prism layers, at the same total prism thickness and unchanged geometry/domain. Cell count alone does not establish directional refinement. Prefer the resolved low-y+ family when wall-model sensitivity is material. Final wall-field and geometry review remains required.'}
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
 points=[(X(r['cells']/1000),Y(r[key]),r['id']) for r in rows];placed=[]
 for family,color in [('wall_function','#D55E00'),('low_yplus','#0072B2')]:
  rr=sorted((r for r in rows if r['family']==family),key=lambda r:r['cells'])
  if rr:
   path=' '.join(('M' if i==0 else 'L')+f'{X(r["cells"]/1000):.2f},{Y(r[key]):.2f}' for i,r in enumerate(rr))
   dash=' stroke-dasharray="6 3"' if family=='wall_function' else ''
   s+=f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1.5"{dash}/>'
   for r in rr:
    x,y=X(r['cells']/1000),Y(r[key])
    if family=='wall_function':s+=f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="{color}"/>'
    else:s+=f'<rect x="{x-4:.2f}" y="{y-4:.2f}" width="8" height="8" fill="{color}"/>'
    preferred=(-12,-14,'end') if r['id']=='M06' else (12,24,'start') if r['id']=='M08' else (6,-8,'start')
    choices=[preferred,(8,-24,'start'),(-10,24,'end'),(10,35,'start'),(-10,-28,'end'),(14,4,'start'),(-14,4,'end')]
    for dx,dy,anchor in choices:
     tx,ty=x+dx,y+dy;tw=27;box=(tx-tw if anchor=='end' else tx,ty-11,tx if anchor=='end' else tx+tw,ty+3)
     overlap=lambda a,b:not(a[2]+4<b[0] or b[2]+4<a[0] or a[3]+3<b[1] or b[3]+3<a[1])
     if box[0]<L-3 or box[2]>W-5 or box[1]<T or box[3]>H-B-2:continue
     if any(overlap(box,b) for b in placed):continue
     if any(mid!=r['id'] and overlap(box,(px-5,py-5,px+5,py+5)) for px,py,mid in points):continue
     break
    placed.append(box)
    if (dx,dy)!=(6,-8):
     ex=(box[0]+box[2])/2;ey=(box[1]+box[3])/2
     s+=f'<path d="M{x:.2f},{y:.2f} L{ex:.2f},{ey:.2f}" stroke="{color}" stroke-width=".7" fill="none" opacity=".65"/>'
    s+=f'<text data-mesh-label="{r["id"]}" x="{tx:.2f}" y="{ty:.2f}" text-anchor="{anchor}" font-size="11" fill="{color}" paint-order="stroke" stroke="white" stroke-width="3" stroke-linejoin="round">{r["id"]}</text>'
 for i in range(5):
  v=xmin+(xmax-xmin)*i/4;x=X(v);s+=f'<text x="{x:.2f}" y="{H-B+20}" text-anchor="middle" font-size="11">{v:.0f}</text>'
 return s+f'<text x="{W/2}" y="{H-6}" text-anchor="middle" font-size="12">Cells [thousands]</text></svg>'
def html_section():
 d=assess();rows=d['settled_results'];trs=[]
 for p in d['comparisons']:
  kind=('Refinement' if p['finer_in_all_controls'] else 'Mixed mesh changes') if p['same_family'] else 'Wall-resolution comparison'
  status=('Within 1%' if p['within_1pct'] else 'Above 1%') if p['finer_in_all_controls'] else ('Diagnostic comparison' if p['same_family'] else 'Different near-wall mesh')
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
 return '<section id="mesh-selection"><div class="section-head"><h2>Mesh convergence and selection</h2></div><p><b>Target: ≤1% difference in both mean CD and mean CL.</b> Select the lightest mesh supported by two finer comparable meshes. Stop adding cases once supported; maximum M15. Force settling remains a separate 0.5% test.</p><div class="callout">'+decision+' Wave runs remain on hold.</div><div class="grid2">'+plot(rows,'CD','CD')+plot(rows,'CL_total','CL, total')+'</div><p class="muted">Lines connect the same near-wall family. Orange circles: wall-function spacing; blue squares: fine near-wall spacing. Only settled means are plotted.</p><div class="table-wrap"><table id="mesh-pair-comparison"><thead><tr><th>Coarse / fine</th><th>Comparison</th><th>Δ CD</th><th>Δ CL</th><th>Δ Fx, pressure</th><th>Δ Fx, viscous</th><th>Assessment</th></tr></thead><tbody>'+''.join(trs)+'</tbody></table></div><p class="muted">Signed differences = (coarse − fine) / |fine| × 100%. Force components help explain the total-drag difference; the agreed 1% acceptance test applies to CD and CL. Finer confirmations must retain or refine every controlled mesh direction. Mixed changes remain diagnostic comparisons.</p><h3>Drag components and computing time</h3>'+graphic+'<div class="table-wrap"><table id="mesh-cost-table"><thead><tr><th>Mesh</th><th>Cells</th><th>Mean Fx, pressure [N]</th><th>Mean Fx, viscous [N]</th><th>Mean Fx, total [N]</th><th>Median time / step [s]</th><th>Mean time / step [s]</th><th>Timed steps</th></tr></thead><tbody>'+''.join(table_rows)+'</tbody></table></div><p class="muted">One physical step advances the solution by 1 ms with 20 inner iterations. Timing uses consecutive steps in each accepted final 0.2 s window. The mean includes recorded checkpoint and reporting overhead; the median reduces its influence. Initialization and final field exports outside the window are excluded. Other CPU tasks can affect timings. These are observed run costs, not isolated hardware benchmarks.</p></section>'
if __name__=='__main__':print(json.dumps(assess(),indent=2))
