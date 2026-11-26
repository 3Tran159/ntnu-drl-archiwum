from pathlib import Path
import json,re,hashlib,datetime,sys
import numpy as np,pandas as pd
H=Path(__file__).resolve().parents[1];p=Path(sys.argv[1]).resolve();assert p.is_relative_to(H/'cases/SP_C_split0_overset')
status=json.loads((p/'status.json').read_text());assert status['status']=='kinematic_poc_passed' and status['steps']==100
df=pd.read_csv(p/'history.csv');assert len(df)==100 and list(df['step'])==list(range(1,101))
assert np.isfinite(df.select_dtypes(include='number')).all().all()
assert abs(df.flap_angle_deg.max()-5)<1e-9 and abs(df.flap_angle_deg.min()+5)<1e-9
assert np.max(abs(df.angle_error_deg))<.01 and df.center_error_m.max()<1e-7
assert df.min_volume_m3.min()>0 and df.min_cell_quality.min()>0 and df.min_face_validity.min()>.9
assert df.overset_error_cells.max()==0 and df.difficult_interpolation_cells.max()==0
audits=[]
for k in range(1,101):
 txt=(p/f'full_audit_step_{k}.txt').read_text();row={n:float(v) for n,v in re.findall(r'(total|active|inactive|acceptors|errors|difficult_interpolation|min_volume|min_quality|max_acceptor_size_ratio)=([-+.eE0-9]+)',txt)}
 assert row['total']==333939 and row['errors']==0 and row['difficult_interpolation']==0 and row['min_volume']>0 and row['min_quality']>0
 assert row['active']+row['inactive']+row['acceptors']==333939 and row['acceptors']>0 and row['max_acceptor_size_ratio']>0
 audits.append(row)
assert abs(df.time_s.iloc[-1]-.85)<1e-9
cp=p/'motion_verified.sim';assert cp.stat().st_size>100000000
with cp.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
stl=json.loads((H/'audit/kinematics_preflight_20261103/geometry_clearance.json').read_text())
result=dict(at=datetime.datetime.now().astimezone().isoformat(),accepted=True,scope='rigid-body kinematics and discrete native Overset connectivity only',hydrodynamic_validation=False,training_approved=False,run=str(p),checkpoint=str(cp),checkpoint_bytes=cp.stat().st_size,checkpoint_sha256=digest,steps=100,saved_time_s=.85,angle_range_deg=[float(df.flap_angle_deg.min()),float(df.flap_angle_deg.max())],max_angle_error_deg=float(abs(df.angle_error_deg).max()),max_mesh_centroid_error_m=float(df.center_error_m.max()),full_mesh_audits=100,all_cell_count=333939,minimum_full_cell_volume_m3=min(x['min_volume'] for x in audits),minimum_full_cell_quality=min(x['min_quality'] for x in audits),minimum_active_face_validity=float(df.min_face_validity.min()),overset_error_cells=0,difficult_interpolation_cells=0,acceptor_count_range=[int(min(x['acceptors'] for x in audits)),int(max(x['acceptors'] for x in audits))],active_count_range=[int(min(x['active'] for x in audits)),int(max(x['active'] for x in audits))],maximum_acceptor_size_ratio=max(x['max_acceptor_size_ratio'] for x in audits),donor_check='All acceptors have valid native interpolation and zero Overset Error Status at all100 solver positions; unique donor-cell count not separately exported.',geometry_clearance_lower_bound_m=stl['conservative_full_range_clearance_m'],remaining_limits=['Overset connectivity sampled at100 solver positions,not a mathematical continuous-angle guarantee.','Geometry clearance bound covers continuous angle range; retained STL discretization.','No force/moment/cavitation conclusions from frozen-flow sweep.','Original C0t0.650 remains hydrodynamic restart; this file keeps flow solvers frozen.'])
(H/'audit/KINEMATIC_POC_REVIEW_20261103.json').write_text(json.dumps(result,indent=2),encoding='utf8')
(p/'work_review.json').write_text(json.dumps(result,indent=2),encoding='utf8')
from PIL import Image
frames=[]
for k in range(21):
 im=Image.open(p/f'frame_{k:03d}.png').convert('RGB');frames.append(im)
gif=p/'flap_motion_plusminus5.gif';frames[0].save(gif,save_all=True,append_images=frames[1:],duration=150,loop=0,optimize=False)
result['animation']=str(gif);result['animation_frames']=21;result['animation_duration_s']=3.15;result['physical_cycle_s']=.2
(H/'audit/KINEMATIC_POC_REVIEW_20261103.json').write_text(json.dumps(result,indent=2),encoding='utf8')
(p/'work_review.json').write_text(json.dumps(result,indent=2),encoding='utf8')
with (H/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=result['at'],kind='kinematics_review_passed',evidence=str(H/'audit/KINEMATIC_POC_REVIEW_20261103.json'),next='Prepare static+2 from original hydrodynamic checkpoint; no hydro Run'))+'\n')
print(json.dumps(result,indent=2))
