import json,datetime,statistics,csv,py_compile
from pathlib import Path
R=Path(__file__).resolve().parent
Q=R.parent/'quasi2d_012_20261029'
src=(R/'build_refinement_batch.py').read_text()
assert 'def main():' in src
src=src[:src.index('def main():')]
old="raw.mkdir();out.mkdir();shutil.copy2(Q/'M03/mesh.sim',raw/'input_M03_copy.sim')"
assert old in src
src=src.replace(old,"allocate_directories(name,raw,out);shutil.copy2(Q/'M03/mesh.sim',raw/'input_M03_copy.sim')")
src=src.replace("'purpose':'Systematic refinement of the low-y+ M04 family'","'purpose':c['purpose']")
needle="macro_path=R/('MeshRaw'+name+'.java');macro_path.write_text(macro)"
assert needle in src
patch="""macro=macro.replace(r'\\"prism_layers\\":40',r'\\"prism_layers\\":'+str(layers))
 macro=macro.replace(r'\\"first_layer_m\\":0.000003',r'\\"first_layer_m\\":'+str(first))
 macro=macro.replace(r'\\"linear_refinement_ratio\\":\\"+2.0+',r'\\"linear_refinement_vs_M04\\":\\"+'+str(ref)+'+')
 """+needle
src=src.replace(needle,patch)
helpers="""
def allocate_directories(name,raw,out):
 if name!='M08':raise RuntimeError('This build is only authorized for the specified M08 design')
 storage=Path('E:/ntnu/mesh_builds_20261029')
 if shutil.disk_usage('E:/').free<12*1024**3:raise RuntimeError('Less than12GiB on E')
 if raw.parent.resolve()!=Q.resolve() or out.parent.resolve()!=Q.resolve():raise RuntimeError('Unexpected junction parent')
 targets=[storage/(name+'_build'),storage/name]
 for target in targets:
  if target.resolve().parent!=storage.resolve() or target.exists():raise RuntimeError('Existing or unexpected storage target')
 storage.mkdir(parents=True,exist_ok=True)
 for link,target in zip([raw,out],targets):
  target.mkdir()
  p=subprocess.run(['cmd','/c','mklink','/J',str(link),str(target)],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
  if p.returncode or not link.is_junction() or link.resolve()!=target.resolve():raise RuntimeError('Junction creation/verification failed; preserve all partial files')
"""
src+=helpers
main="""
def main():
 import os
 import mesh_selection_queue as queue
 c=json.loads((R/'M08_controlled_design.json').read_text())
 write(R/'M08_build_controller.json',{'pid':os.getpid(),'started_at':datetime.datetime.now().astimezone().isoformat(),'status':'building','design':c})
 try:
  pending=queue.preflight()
  if pending:raise RuntimeError('Another admitted pending case exists; do not duplicate queue work')
  result=build(c)
  jobs=read(R/'mesh_selection_jobs.json',[])
  if any(j['id'].startswith('M08_') for j in jobs):raise RuntimeError('M08 already admitted')
  jobs.append({'id':'M08_until_settled_r1','source':str(Q/'M08/mesh.sim'),'start':0,'cells':result['cells'],'initialize':True,'dt':.001,'inner':20,'order':'FIRST_ORDER','target':10,'wall_budget_s':10800,'termination':'First passing evaluation of both mean changes below0.5%'})
  jobs.sort(key=lambda j:int(j['id'][1:3]));write(R/'mesh_selection_jobs.json',jobs)
  write(R/'M08_build_result.json',{'status':'verified_and_admitted','cells':result['cells'],'design':c,'updated_at':datetime.datetime.now().astimezone().isoformat()})
  write(R/'M08_build_controller.json',{'pid':os.getpid(),'status':'verified_starting_guarded_queue'})
  with (R/'mesh_selection_M08_controller.log').open('a',encoding='utf-8') as log,(R/'mesh_selection_M08_controller.err').open('a',encoding='utf-8') as err:
   p=subprocess.Popen([sys.executable,str(R/'mesh_selection_queue.py'),'--run'],stdout=log,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW,cwd=str(R))
  write(R/'M08_queue_launch.json',{'pid':p.pid,'launched_at':datetime.datetime.now().astimezone().isoformat()})
  print(json.dumps({'mesh':'M08','status':'verified_and_admitted','cells':result['cells'],'queue_pid':p.pid}),flush=True)
 except BaseException as e:
  write(R/'M08_build_result.json',{'status':'needs_review','error':str(e),'updated_at':datetime.datetime.now().astimezone().isoformat()})
  raise
if __name__=='__main__':main()
"""
dest=R/'build_controlled_m08.py'
if dest.exists():raise RuntimeError('Existing builder preserved')
dest.write_text(src+main)
py_compile.compile(str(dest),doraise=True)
design={'id':'M08','family':'low_yplus','reference':'M06','linear_refinement':1.4,'first_layer_um':3/1.96,'layers':48,'purpose':'Controlled wall-normal refinement: M06 surface and outer sizes with M07 first height and layer count. Separate the observed viscous drag change from tangential/bulk refinement.','surface_and_outer_match':'M06','prism_match':'M07','total_prism_m':.01546,'geometry':'Preserve existing foil and domain; exact single-cell span extrusion','next_gate':'Independent validity audit, then identical dt/inner/time-settling screen. No wave admission.'}
(R/'M08_controlled_design.json').write_text(json.dumps(design,indent=2))
reg=json.loads((R/'campaign_registry.json').read_text())
assert not any(c['id']=='M08' for c in reg['cases'])
reg['cases'].append({'id':'M08','role':'M06 surface/outer mesh, M07 prism spacing','first_layer_um':design['first_layer_um'],'layers':48,'refinement':1.4,'gpu':'Meshing on2CPU; GPU after audit','family':'low_yplus'})
(R/'campaign_registry_before_M08.json').write_text((R/'campaign_registry.json').read_text())
(R/'campaign_registry.json').write_text(json.dumps(reg,indent=2))
plan=json.loads((R/'mesh_selection_plan.json').read_text())
(R/'mesh_selection_plan_before_M08.json').write_text(json.dumps(plan,indent=2))
plan['next_candidates']=[design]
plan['latest_decision']='M07 settled. M06/M07 CL agrees0.01615%, CD fails1.32683%; M04 fails against finer meshes. Test controlled wall-normal M08 before unnecessary global refinement.'
plan['updated_at']=datetime.datetime.now().astimezone().isoformat()
(R/'mesh_selection_plan.json').write_text(json.dumps(plan,indent=2))
report=json.loads((R/'mesh_convergence.json').read_text())
cases=[x for x in report['settled_results'] if x['id'] in ['M04','M06','M07']]
jobs=json.loads((R/'queue.json').read_text())
for r in cases:
 j=[x for x in jobs if x['id'].startswith(r['id']+'_')][-1]
 with (R/j['id']/'history.csv').open() as f:hh=list(csv.DictReader(f))
 ww=[a for a in hh if r['window_start_s']+1e-8<float(a['physical_time_s'])<=r['time_s']+1e-8]
 assert len(ww)==200
 for field in ['CD','CL_total']:assert abs(statistics.mean(float(a[field]) for a in ww)-r[field])<1e-12
pairs=[x for x in report['comparisons'] if x['coarse'] in ['M04','M06'] and x['fine'] in ['M06','M07']]
(R/'M04_M06_M07_comparison.json').write_text(json.dumps({'verified_at':datetime.datetime.now().astimezone().isoformat(),'method':'200 samples in each accepted final0.2s window; relative difference denominator is finer result','cases':cases,'pairs':pairs,'selected':None,'next':'M08 controlled wall-normal test'},indent=2))
print(json.dumps({'prepared':'build_controlled_m08.py','M08_design':design,'comparison_verified':True}))
