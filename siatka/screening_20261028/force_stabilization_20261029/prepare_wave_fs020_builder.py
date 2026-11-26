from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'build_wave_fs020_r1.py'
if p.exists():raise RuntimeError('Preserve builder')
s=(R/'build_optimized_m09.py').read_text().split('\ndef main():')[0]
s=s.replace('Build M09 on two CPU workers; record a verified candidate without starting a GPU job.','Build M10_FS020_r1: wave-resolution variant derived from M09 controls, CPU2 only.')
assert s.count("'free_surface_m':.04/ref")==1;s=s.replace("'free_surface_m':.04/ref","'free_surface_m':c.get('free_surface_m',.04/ref)")
assert s.count("f'{.04/ref}/base'")==1;s=s.replace("f'{.04/ref}/base'","f'{c.get(\"free_surface_m\",.04/ref)}/base'")
s=s.replace("if name!='M09':raise RuntimeError('This build is only authorized for the specified M08 design')","if name!='M10_FS020_r1':raise RuntimeError('This build is only authorized for the specified wave free-surface variant')")
s+=r'''
import os
import run_until_settled as e
write=e.write
def publish(status,**kw):
 e.write(R/'wave_fs_refinement_state.json',dict(status=status,updated_at=e.stamp(),controller_pid=os.getpid(),workers=2,gpu=False,mesh='M10_FS020_r1',scope='Wave free-surface refinement preparation; no flow admission and no change to accepted M09 calm result',**kw))
def main():
 W=Path('E:/ntnu/quasi2d_waves_20261029');lock=W/'preparation.lock';source=Q/'M03'/'mesh.sim'
 if lock.exists():raise RuntimeError('CPU preparation owner exists')
 if (R/'STOP_ALL').exists():raise RuntimeError('Stop marker')
 if e.read(R/'selected_mesh_decision.json',{}).get('status')!='supported_calm_mesh_template':raise RuntimeError('M09 selection not supported')
 if e.free_memory()<24*1024**3:raise RuntimeError('Need24GiB available')
 if e.read(R/'mesh_selection_plan.json',{}).get('maximum_mesh_number',0)<10:raise RuntimeError('Mesh number authorization')
 with lock.open('x') as f:json.dump(dict(pid=os.getpid(),purpose='Wave free-surface M10 variant CPU2 build; no GPU'),f)
 digest=e.digest(source)
 try:
  c=dict(id='M10_FS020_r1',mesh_number=10,family='M09_derived_wave_grid',reference='M09',linear_refinement=1.4,outer_base_m=.25,first_layer_um=1.530612244897959,layers=48,total_prism_m=.01546,free_surface_m=.020,protected_middle_size_m=.14285714285714288,protected_middle_xz_m=[-11.9,30.94,-3,3.2],purpose='Wave FS sensitivity: change only nominal free-surface control0.0285714to0.020m; preserve M09 foil/near-foil/prism/outer controls. Regenerated actual edges must be audited. Extend to matched4lambda domain after build; requires its own pairedcalm/wave, no accuracyclaim.')
  e.write(R/'M10_wave_fs_design.json',dict(design=c,status='building',historical_proposal='Prior M10 LE/TE-local idea remains unbuilt; this actual M10 variant prioritizes wave free-surface resolution. No LE/TE changes.'))
  publish('building_on_two_CPU',design=c)
  result=build(c)
  unchanged=e.digest(source)==digest
  if not unchanged:raise RuntimeError('Source digest changed')
  out=Q/c['id']
  e.write(R/'wave_fs_refinement_result.json',dict(status='short_domain_mesh_audited_pending_extension',updated_at=e.stamp(),design=c,result=result,source_unchanged=unchanged,source_sha256=digest,directory=str(out),flow_steps=0,pending=['Audit actualFSsize andfoil/prismpreservation','Extend coherentlyto80m preservingrefinedboundaryspacing','STARimport/quality/boundaryaudit','Matchedcalm/W01prep andgrid/forcecomparison']))
  publish('short_domain_mesh_audited_pending_extension',cells=result['cells'],directory=str(out),source_unchanged=unchanged,flow_steps=0)
 except BaseException as ex:
  publish('needs_review',error=str(ex),source_unchanged=e.digest(source)==digest);raise
 finally:
  if e.read(lock,{}).get('pid')==os.getpid():lock.unlink()
if __name__=='__main__':main()
'''
compile(s,str(p),'exec');p.write_text(s)
print('Prepared CPU2 M10_FS020_r1 builder; allsourcepaths/newjunctions guarded, noGPUflow.')
