from pathlib import Path
import json
import run_until_settled as e
R=Path(__file__).resolve().parent;C=Path('E:/ntnu/quasi2d_waves_20261029/W20_H24_X4_CPUprop_dt1ms_r2')
for name in ['wave_propagation_state.json','wave_preparation_state.json']:
 p=R/name;st=e.read(p,{})
 if st.get('result',{}).get('completed',{}).get('status')=='stability_guard':
  st['status']='needs_review_stability_guard';st['updated_at']=e.stamp()
  st['reason']='Pilot stopped at t0.704s under the unchanged stability guard after rapid maximum-speed growth. No continuation is admitted before the saved-field and boundary audit.'
  st['next_audit']='wave_checkpoint_audit_state.json';e.write(p,st)
e.write(R/'wave_pilot_stability_review.json',{'updated_at':e.stamp(),'case':C.name,'status':'needs_spatial_diagnosis','completed':e.read(C/'completed.json',{}),'last_progress':e.read(C/'progress.json',{}),'extension_admitted':False,'source_preserved':True,'audit_controller_pid':28100,'audit_state':'wave_checkpoint_audit_state.json','checks':['Locate velocity and CFL maxima independently, including local phase and adjacent cells','Check distance to inlet/outlet/top and forcing/damping transitions','Inspect actual top/outlet backflow phase and velocity/pressure profile bindings','Keep guard50m/s unchanged; gauge agreement and low interface CFL do not establish global stability']})
print('Pilot status corrected to stability review; no continuation admitted.')
