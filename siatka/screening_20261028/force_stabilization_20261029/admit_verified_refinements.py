import json
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
def read(p,d=None):
 try:return json.loads(p.read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return d
def write(p,a):
 tmp=p.with_suffix('.admit.tmp');tmp.write_text(json.dumps(a,indent=2),encoding='utf-8');tmp.replace(p)
jobs=read(R/'mesh_selection_jobs.json',[]);registry=read(R/'campaign_registry.json',{})
for c in read(R/'mesh_selection_plan.json',{})['next_candidates']:
 m=c['id'];out=Q/m;ready=read(out/'mesh_build.exit.json',{});metric=read(out/'measurement.json',{}).get('metrics',{});top=read(out/'topology_audit.json',{})
 if not any(x['id']==m for x in registry['cases']):
  registry['cases'].append({'id':m,'role':'Low-y+ refinement of M04','first_layer_um':c['first_layer_um'],'layers':c['layers'],'refinement':c['linear_refinement'],'gpu':'Meshing / audit','family':'low_yplus'})
 if ready.get('returncode')!=0 or not top.get('single_layer_topology') or any(metric.get(k,1)!=0 for k in ['NegativeVolumeCells','UnclosedCells','DegeneratedFeCells']):continue
 if not any(j['id'].startswith(m+'_') for j in jobs):
  jobs.append({'id':m+'_until_settled_r1','source':str(out/'mesh.sim'),'start':0,'cells':metric['cell_count'],'initialize':True,'dt':.001,'inner':20,'order':'FIRST_ORDER','target':10,'wall_budget_s':10800,'termination':'First evaluation with both mean changes below 0.5%'})
jobs.sort(key=lambda j:int(j['id'][1:3]));write(R/'mesh_selection_jobs.json',jobs);write(R/'campaign_registry.json',registry)
print(json.dumps({'queued':[j['id'] for j in jobs],'visible_cases':[c['id'] for c in registry['cases']]}))
