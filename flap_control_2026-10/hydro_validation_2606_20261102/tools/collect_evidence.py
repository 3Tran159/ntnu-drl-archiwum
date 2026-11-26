from pathlib import Path
import json,hashlib,datetime,re
R=Path('F:/ntnu/flap_control/hydro_validation_2606_20261102')
audit=R/'validation/stage_evidence.json'
g=json.loads((R/'geometry/current_geometry.json').read_text())
runs=[]
for p in (R/'cases').glob('*/smoke_*/status.json'):
 q=p.parent;d=json.loads(p.read_text());d['folder']=str(q)
 for n in ['metadata.json']:
  if (q/n).exists():d[n]=json.loads((q/n).read_text())
 runs.append(d)
e=dict(updated_at=datetime.datetime.now().astimezone().isoformat(),version='2606.0002 build 21.04.009-R8',geometry=dict(native_profile_points=g['native_profile_points'],hinge_fraction=.8,gap_m=g['gap_m'],min_clearance_m=g['min_clearance_m'],motion_sweep_deg=[-5,5]),C01_reference_VOF=dict(CL_hydro=.31565950495122014,CD=.007002316911710474,mesh_cells=309441,min_pressure_saved_checkpoint_Pa=34323.89486465555),smoke_runs=runs,training_approved=False,experimental_validation=False,W04_allowed=False)
audit.write_text(json.dumps(e,indent=2))
print(json.dumps(dict(evidence_file=str(audit),recorded_smoke_runs=len(runs))))
for p in (R/'runs').glob('*.log'):
 txt=p.read_text(encoding='utf8',errors='replace')
 if 'Server process exited with code' in txt:
  red=re.sub(r'(?i)(-podkey\s+)\S+',r'\1[REDACTED]',txt)
  if red!=txt:p.write_text(red,encoding='utf8')
