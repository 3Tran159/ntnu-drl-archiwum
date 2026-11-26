import json,os,shutil,time
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
for m in ['M04_verified','M05']:
 data=read(Q/m/'measurement.json')['metrics'];top=read(Q/m/'topology_audit.json')
 assert data['NegativeVolumeCells']==data['UnclosedCells']==data['DegeneratedFeCells']==0
 assert data['min_cell_quality']>.01 and data['min_face_validity']>.999 and top['single_layer_topology']
 assert top['max_target_source_xz_displacement_m']<1e-10 if m=='M04_verified' else True
old=Q/'M04';saved=Q/'M04_failed_sweep';verified=Q/'M04_verified'
assert old.resolve().parent==Q.resolve() and verified.resolve().parent==Q.resolve() and saved.resolve().parent==Q.resolve()
assert not saved.exists()
os.rename(old,saved);os.rename(verified,old)
shutil.copy2(saved/'source_identity.json',old/'source_identity.json')
shutil.copy2(saved/'repair_oriented_extrusion/geometry_validation.json',old/'extrusion_orientation_validation.json')
(old/'mesh_build.exit.json').write_text(json.dumps({'returncode':0,'accepted_after':'Exact spanwise extrusion and corrected CGNS face orientations, then independent STAR audit','original_attempt':str(saved),'source_wall_unchanged':True}))
(old/'design.json').write_text(json.dumps({'id':'M04','first_layer_m':3e-6,'layers':40,'total_prism_m':.01546,'reference':'M03','source_wall_unchanged':True,'target_projection_removed_max_m':.0001149888131791679},indent=2))
repair=R/'M04_REPAIR_IN_PROGRESS'
if repair.exists():repair.rename(R/'M04_REPAIR_COMPLETED.txt')
lock=R/'queue.lock'
if lock.exists():lock.rename(R/'queue_lock_shutdown_saved.json')
(R/'queue_state.json').write_text(json.dumps({'status':'paused_for_shutdown','active':None,'updated_at':time.strftime('%Y-%m-%dT%H:%M:%S'),'note':'User will shut down and move computer. M03/M02 settled. Valid M04 and M05 saved; no new GPU solves launched.'},indent=2))
print('Verified M04 adopted with all failed attempts preserved; M05 passed. Campaign paused for shutdown.')
