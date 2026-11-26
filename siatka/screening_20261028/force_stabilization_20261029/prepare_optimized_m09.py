from pathlib import Path
import json,datetime,csv,statistics,math,shutil
R=Path(r'F:\ntnu\mesh_screening_20261028\force_stabilization_20261029');Q=R.parent/'quasi2d_012_20261029'
data=json.loads((R/'mesh_convergence.json').read_text());rows={x['id']:x for x in data['settled_results']}
a,b=rows['M08'],rows['M07']
diff={k:100*(a[k]-b[k])/abs(b[k]) for k in ['CD','CL_total','Fx_pressure_N','Fx_viscous_N']}
report={'updated_at':datetime.datetime.now().astimezone().isoformat(),'M08':a,'M07':b,'difference_pct_M08_vs_M07':diff,'both_force_coefficients_within_1pct':all(abs(diff[k])<=1 for k in ['CD','CL_total']),'candidate_status':'M08 agrees with one finer comparable mesh. M09 optimization may proceed; final selection and time accuracy still pending.'}
(R/'M08_M07_comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert report['both_force_coefficients_within_1pct']
code=(R/'build_controlled_m08.py').read_text().split('\ndef main():')[0]
code=code.replace('"""Build and audit M06/M07 on CPU, then admit only valid meshes to the GPU queue."""','"""Build M09 on two CPU workers; record a verified candidate without starting a GPU job."""')
code=code.replace("base=.2/ref;first=","base=c.get('outer_base_m',.2/ref);first=")
code=code.replace("if name!='M08':","if name!='M09':")
anchor=" macro_path=R/('MeshRaw'+name+'.java');macro_path.write_text(macro)"
addition="""
 middle='''SimpleBlockPart middle=s.get(MeshPartFactory.class).createNewBlockPart(s.getGeometryPartManager());
middle.setPresentationName("Q2D_protected_middle_M09");
middle.setCorners(new DoubleVector(new double[]{-11.9,-.1,-3}),new DoubleVector(new double[]{30.94,.1,3.2}));
middle.rebuildSimpleShapePart();
VolumeCustomMeshControl protection=auto.getCustomMeshControls().createVolumeControl();
protection.setPresentationName("Q2D_protected_middle_M09");protection.getGeometryObjects().setObjects(middle);
for(Object v:protection.getCustomConditions().getChildren())if(v instanceof VolumeControlBase)((VolumeControlBase)v).setVolumeControlBaseSizeOption(true);
protection.getCustomValues().get(VolumeControlSize.class).setRelativeSize(0.14285714285714288/base*100);
'''
 anchor='for(DirectedMeshPartCollection pc:'
 if macro.count(anchor)!=1:raise RuntimeError('Unexpected base macro; no modification performed')
 macro=macro.replace(anchor,middle+anchor)
"""
assert anchor in code;code=code.replace(anchor,addition+anchor)
main=r'''
def main():
 import os,csv,statistics,math
 own=R/'M09_build.lock'
 if own.exists():raise RuntimeError('Existing M09 build controller; inspect before recovery')
 with own.open('x') as f:json.dump({'pid':os.getpid(),'purpose':'M09 two-CPU build, no GPU launch'},f)
 try:
  write(R/'M09_build_controller.json',{'pid':os.getpid(),'status':'waiting_for_small_wave_audit','started_at':datetime.datetime.now().astimezone().isoformat()})
  audit=Path('E:/ntnu/quasi2d_waves_20261029/W20_H16_X4_audit_r4.exit.json')
  until=time.time()+900
  while not audit.exists():
   if time.time()>until:raise RuntimeError('Wave audit has not exited; preserve CPU preparation limit')
   time.sleep(10)
  if (R/'STOP_ALL').exists():raise RuntimeError('Campaign pause marker present')
  for mesh,folder in [('M08','M08_until_settled_r3'),('M07','M07_until_settled_r1')]:
   result=read(R/folder/'controller_result.json',{})
   if result.get('status')!='completed' or not result.get('original_unchanged'):raise RuntimeError('Reference not accepted: '+mesh)
  pairs=read(R/'M08_M07_comparison.json',{})
  if not pairs.get('both_force_coefficients_within_1pct'):raise RuntimeError('M08/M07 coefficient agreement gate failed')
  c={'id':'M09','family':'low_yplus','reference':'M08','linear_refinement':1.4,'outer_base_m':.25,'first_layer_um':1.530612244897959,'layers':48,'total_prism_m':.01546,'surface_and_outer_match':'M08 surface, near-foil and free-surface controls; remote outer base changed','prism_match':'M07/M08','protected_middle_size_m':.14285714285714288,'protected_middle_xz_m':[-11.9,30.94,-3,3.2],'purpose':'Coarsen remote domain only; protect middle region and preserve M08 foil/prisms/near-foil/FS targets.'}
  write(R/'M09_build_controller.json',{'pid':os.getpid(),'status':'building_on_two_CPU','started_at':datetime.datetime.now().astimezone().isoformat(),'design':c})
  result=build(c)
  write(R/'M09_build_result.json',{'status':'verified_ready_pending_temporal_review','cells':result['cells'],'design':c,'updated_at':datetime.datetime.now().astimezone().isoformat(),'gpu_launched':False})
  write(R/'M09_build_controller.json',{'pid':os.getpid(),'status':'verified_ready_pending_temporal_review','cells':result['cells']})
  print(json.dumps({'M09_cells':result['cells'],'gpu_launched':False}),flush=True)
 except BaseException as ex:
  write(R/'M09_build_result.json',{'status':'needs_review','error':str(ex),'updated_at':datetime.datetime.now().astimezone().isoformat()});raise
 finally:
  if read(own,{}).get('pid')==os.getpid():own.unlink()
  subprocess.run([sys.executable,str(R/'update_status.py')],capture_output=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
if __name__=='__main__':main()
'''
target=R/'build_optimized_m09.py'
if target.exists():raise RuntimeError('M09 builder exists; inspect before replacing')
target.write_text(code+main,encoding='utf-8')
compile(code+main,str(target),'exec')
print(json.dumps({'comparison_pct':diff,'M09_builder_prepared':True,'M09_launched':False}))
