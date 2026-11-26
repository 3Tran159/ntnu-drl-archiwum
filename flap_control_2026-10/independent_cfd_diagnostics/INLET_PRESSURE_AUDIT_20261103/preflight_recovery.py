from pathlib import Path
import sys,json,hashlib,datetime
import numpy as np,pandas as pd
H=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102');D=Path(__file__).resolve().parent;sys.path.insert(0,str(H/'tools'))
import night_queue as q
from ramp_authorization import blocks
from queue_safety import launch_integrity
def s5(x):return 10*x**3-15*x**4+6*x**5
def law(t):
 s=t-.690;v=s/.020
 x=.1+2.5*s if s<=0 else .1+2.5*s-2.25*.020*(2.5*v**4-3*v**5+v**6) if s<.020 else .1275+.25*(s-.020)
 rate=2.5 if s<=0 else .25 if s>=.020 else 2.5-2.25*s5(v)
 acceleration=0 if s<=0 or s>=.020 else -2.25/.020*30*v*v*(1-v)**2
 sx=30*x*x*(1-x)**2;sxx=60*x*(1-x)*(1-2*x)
 return x,18-8*s5(x),-8*sx*rate,-8*(sxx*rate*rate+sx*acceleration)
ts=np.linspace(.690,4.2,35101);a=np.array([law(t) for t in ts]);assert np.all(np.diff(a[:,1])<=1e-10)
assert np.allclose(law(.690)[1:],[17.93152,-4.86,-216],atol=1e-8)
assert np.allclose(law(4.2)[1:],[10,0,0],atol=1e-8)
for t in [.690,.710]:assert np.max(np.abs(np.array(law(t-1e-10))-np.array(law(t+1e-10))))<1e-4
# Pressure-inertia extrapolation is a prediction, not an acceptance criterion.
base=pd.read_csv(H/'audit/relocation_native_20261103_C0/Background_reopened_volume.csv')
old=pd.read_csv(H.parent/'independent_cfd_diagnostics/C0_speed_down_20261103/run_20261103_111057/Background_final_volume.csv')
assert np.allclose(base[['X (m)','Y (m)','Z (m)']],old[['X (m)','Y (m)','Z (m)']],atol=1e-12)
ratio=abs(a[:,2].min())/4.86;pred=base['Absolute Pressure (Pa)']+ratio*(old['Absolute Pressure (Pa)']-base['Absolute Pressure (Pa)'])
cfg=q.read(q.CFG);st=q.read(q.STATE);j=cfg['jobs'][-1];assert j['id']=='INLET_PRESSURE_RECOVERY_20261103_TEST'
assert q.validate(cfg);assert not blocks(st,cfg,j);launch_integrity(H,j)
assert blocks(st,cfg,next(x for x in cfg['jobs'] if x['id']=='BOUNDED_FIXED_PLUS2_SWEEP_20261103_RUN'))
assert blocks({**st,'failure_hold':j['id']},cfg,j)
assert not q.LOCK.exists() and not st.get('active') and not any(p['ownedBatch'] for p in q.processes())
assert q.resources()['disk_free_GiB']>=15
f=json.loads((D/'FIELD_AUDIT.json').read_text());m=f['0706']['min_cell']
dist=dict(inlet_m=m['x']+35,outlet_m=45-m['x'],top_m=8-m['z'],bottom_m=m['z']+22,span_low_m=m['y']-.01,span_high_m=.03-m['y'])
result=dict(at=q.now(),preflight_pass=True,one_test_only=True,dt_s=.002,inner_iterations=50,CPU=8,steps=50,start=law(.690),end_test=law(.790),end_reduction_t_s=4.2,max_deceleration_m_s2=float(-a[:,2].min()),old_max_deceleration_m_s2=37.5,predicted_global_min_Pa=float(pred.min()),prediction_is_not_validation=True,C2_join_verified=True,source_checksum_verified=True,old_failure_still_blocked=True,new_failure_will_block_replay=True,min_cell_region='Background',min_cell_locator='native CSV data row 21719 and centroid; persistent STAR global cell ID was not exported',min_cell_distances=dist,domain_bounds_source=str(H/'macros/BuildExtrudedHydroMesh.java')+':119',resources=q.resources())
(D/'RECOVERY_PREFLIGHT.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result,indent=2))
