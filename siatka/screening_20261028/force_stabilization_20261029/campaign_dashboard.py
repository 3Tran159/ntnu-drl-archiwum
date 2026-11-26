"""Current engineering campaign sections, built from saved evidence."""
import csv,html,json,math
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
def read(p,d=None):
 try:return json.loads(p.read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return d
def fmt(v,n=3):return '—' if v is None else f'{v:,.{n}f}'
def sections(live):
 plan=read(R/'campaign_registry.json',{});jobs=read(R/'queue.json',[]);meshes=[];settled=[]
 buoy=22.718189111947265/3855.6;brockett=2*math.pi*(1-.83*.12)*2.05*.025
 for case in plan.get('cases',[]):
  m=case['id'];metric=read(Q/m/'measurement.json',{}).get('metrics',{});top=read(Q/m/'topology_audit.json',{})
  valid=all(metric.get(k,1)==0 for k in ['NegativeVolumeCells','UnclosedCells','DegeneratedFeCells']) and top.get('single_layer_topology',False)
  matching=[j for j in jobs if j['id'].startswith(m+'_')];accepted=False
  if matching:
   folder=R/matching[-1]['id'];accepted=read(folder/'completed.json',{}).get('status')=='stabilized' or read(folder/'acceptance.json',{}).get('status')=='settled'
  active=live.get('queue',{}).get('status')=='running' and str(live.get('queue',{}).get('active','')).startswith(m+'_')
  status='Settled' if accepted else ('Running' if active else ('Ready for GPU' if valid else 'Meshing / audit'))
  full=None
  try:
   with (Q/m/'foil_layer_topology.csv').open() as f:rr=list(csv.DictReader(f))
   full=100*sum(float(r['edge_length_m']) for r in rr if float(r['continuous_quad_layers'])>=case['layers'])/sum(float(r['edge_length_m']) for r in rr)
  except OSError:pass
  meshes.append('<tr><td><b>'+m+'</b><span class="sub">'+case['role']+'</span></td><td>'+status+'</td><td>'+str(metric.get('cell_count','—'))+'</td><td>'+fmt(case['first_layer_um'],1)+'</td><td>'+str(case['layers'])+'</td><td>'+fmt(case['refinement'],2)+'×</td><td>'+fmt(metric.get('min_cell_quality'),4)+'</td><td>'+fmt(metric.get('max_skewness_angle_deg'),2)+'°</td><td>'+fmt(full,2)+'%</td></tr>')
  a=live.get('meshes',{}).get(m,{})
  if accepted and a.get('windows'):
   w=a['windows'][-1];cd=w['CD']['mean'];cl=w['CL_total']['mean'];dp=w.get('pressure_drag_N',{}).get('mean');dv=w.get('viscous_drag_N',{}).get('mean')
   settled.append('<tr><td><b>'+m+'</b></td><td>'+fmt(w['start'],3)+'–'+fmt(w['end'],3)+'</td><td>'+fmt(cd,6)+'</td><td>'+fmt(cl,6)+'</td><td>'+fmt(cl-buoy,6)+'</td><td>'+fmt(3855.6*cd,2)+'</td><td>'+fmt(dp,2)+'</td><td>'+fmt(dv,2)+'</td><td>'+fmt(100*((cl-buoy)/brockett-1),2)+'%</td></tr>')
 from mesh_parameter_table import matrix,optimization,temporal
 mesh='<section id="mesh"><div class="section-head"><h2>Mesh campaign</h2></div><p>Select the lightest mesh supported within 1% in both CD and CL by comparable denser cases, with separate time-resolution checks. Maximum M15.</p>'+matrix(live)
 mesh+='<details><summary>Mesh purpose and quality audit</summary><div class="table-wrap"><table><thead><tr><th>Case / purpose</th><th>Status</th><th>Cells</th><th>First layer [µm]</th><th>Layers</th><th>Surface/outer refinement</th><th>Min quality</th><th>Max skewness</th><th>Full layer coverage</th></tr></thead><tbody>'+''.join(meshes)+'</tbody></table></div><p class="muted">Zero negative-volume, unclosed and degenerate cells are required before flow admission. Check actual wall-layer coverage near the sharp trailing edge.</p></details>'+temporal()+optimization()+'<details><summary>Mesh geometry views</summary>@@MESH_CHART@@</details></section>'
 table='''<div class="card"><h3>Settled results · mean over the final 0.2 s</h3><div class="table-wrap"><table><thead><tr><th>Mesh</th><th>Window [s]</th><th>Mean CD</th><th>Mean CL,total</th><th>Mean CL,dynamic</th><th>Drag [N]</th><th>Pressure [N]</th><th>Viscous [N]</th><th>Δ CL vs Brockett</th></tr></thead><tbody>'''+''.join(settled)+'''</tbody></table></div><p class="muted">Forces refer to the 20 mm slice. Dynamic lift excludes nominal buoyancy. Pending cases appear after they pass the 0.5% force criterion.</p></div>'''
 return mesh,table
