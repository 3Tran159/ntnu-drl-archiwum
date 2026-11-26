from pathlib import Path
import json,hashlib,datetime,shutil,ast
H=Path(__file__).resolve().parents[1];stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup=H/'audit'/('before_poc_queue_'+stamp);backup.mkdir()
def change(name,fn):
 p=H/'tools'/name;shutil.copy2(p,backup/name);s=fn(p.read_text());ast.parse(s);p.write_text(s,encoding='utf8')
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def queue(s):
 s=rep(s,'def now():',"ALLOWED.add('KinematicPoc333939.java')\n\ndef now():")
 s=rep(s,"  assert j.get('angle_deg',0)==0,'No deflections supported in diagnostic queue'","  if j.get('kind')=='kinematic':\n   assert j['macro']=='KinematicPoc333939.java' and j.get('range_deg')==[-5,5]\n   assert cfg['scientific_gates'].get('C0_accepted_for_kinematics') is True\n  else:assert j.get('angle_deg',0)==0,'Nonzero hydrodynamic angles require a separate reviewed stage'")
 s=rep(s,'def output_path(receipt):',"def output_path(receipt):\n if receipt['macro']=='KinematicPoc333939.java':return H/'cases/SP_C_split0_overset'/('kinematic_poc_'+receipt['run_id'])")
 s=rep(s,"'inspection_complete','steady_diagnostic_ready','mesh_connectivity_prepared','urans_diagnostic_ready'","'kinematic_poc_passed','inspection_complete','steady_diagnostic_ready','mesh_connectivity_prepared','urans_diagnostic_ready'")
 s=rep(s," if active and not active['macro'].startswith('Inspect') and metrics.get('history_rows',0)>0:"," if active and active['macro']!='KinematicPoc333939.java' and not active['macro'].startswith('Inspect') and metrics.get('history_rows',0)>0:")
 s=rep(s,"jobs=[j for j in st['jobs'].values() if j.get('macro') and not j['macro'].startswith('Inspect') and j.get('output')]","jobs=[j for j in st['jobs'].values() if j.get('macro') and j['macro']!='KinematicPoc333939.java' and not j['macro'].startswith('Inspect') and j.get('output')]")
 s=rep(s,"    for k in ['time_s','CL_hydro'","    for k in ['flap_angle_deg','flap_angular_velocity_deg_s','angle_error_deg','center_error_m','min_volume_m3','min_cell_quality','min_face_validity','time_s','CL_hydro'")
 s=rep(s," base['operation']=view['metrics'].get('operation','HOLD')"," if not active:base['solver_state']='STOPPED' if any((H.parent/n).exists() for n in ['PAUSED_FOR_HOME.json','STOP_OWNED_CFD.json']) else 'HOLD'\n elif view['metrics'].get('saving_or_exporting'):base['solver_state']='SAVING'\n elif base['solver_state']=='STALLED':base['solver_state']='HOLD';base['stall_detected']=True\n base['operation']=base['solver_state']\n base['solver_actually_advancing']=base['solver_state']=='RUNNING'\n base['flow_frozen']=bool(active and active['macro']=='KinematicPoc333939.java')\n if base['flow_frozen']:base['flow_reference_time_s']=.65;base['hydrodynamic_data_valid']=False\n view['solver_state']=base['solver_state'];view['operation']=base['operation'];view['flow_frozen']=base['flow_frozen']\n atomic(H/'NIGHT_DASHBOARD.json',view)")
 s=rep(s,"    elif not pending:st['queue_state']='HOLD_SCIENTIFIC_REVIEW'","    elif cfg.get('accept_new_jobs') is False:st['queue_state']='HOLD_NO_NEW_JOBS'\n    elif not pending:st['queue_state']='HOLD_SCIENTIFIC_REVIEW'")
 return s
change('night_queue.py',queue)
change('night_native.py',lambda s:rep(s,'name=sys.argv[1];assert name in allowed',"allowed['KinematicPoc333939.java']=8\nname=sys.argv[1];assert name in allowed"))
def dash(s):
 insert='''
 review0=json.loads((h/'WORK_CURRENT_REVIEW.json').read_text(encoding='utf8'))
 if review0.get('current_job_kind')=='kinematic':
  m=view.get('metrics',{});e=html.escape
  rows=''.join('<tr><td>'+e(k)+'</td><td>'+e(str(m.get(k,'—')))+'</td></tr>' for k in ['physical_time_s','flap_angle_deg','flap_angular_velocity_deg_s','angle_error_deg','center_error_m','min_volume_m3','min_cell_quality','overset_error_cells','difficult_interpolation_cells'])
  text='<html><meta charset="utf-8"><meta http-equiv="refresh" content="30"><style>body{font:18px system-ui;background:#10202c;color:#eef;max-width:1000px;margin:40px auto}td{padding:8px;border-bottom:1px solid #567}a{color:#8df}</style><h1>'+e(base.get('solver_state','HOLD'))+' — kinematics +/-5deg</h1><p>Flow and turbulence are frozen. This test validates motion/connectivity, not forces.8CPU,noGPU.</p><table>'+rows+'</table><p>C0 source solution:0.650s,11560iterations,333939cells. B0/C0 native reopen and matching numerical audit passed. Quantitative mesh/time/energy validation remains open.</p><p>'+e(review0.get('last_decision',''))+'</p><p>Next: Work review of entire sweep; prepare+2deg only after success.</p><pre>'+e(json.dumps(view.get('active'),indent=2))+'</pre></html>'
  (h/'NIGHT_DASHBOARD.html').write_text(text,encoding='utf8');return
'''
 return rep(s,'def render(h,view,base):','def render(h,view,base):'+insert)
change('night_dashboard.py',dash)
cfg=json.loads((H/'NIGHT_QUEUE.json').read_text());state=json.loads((H/'NIGHT_QUEUE_STATE.json').read_text())
assert state.get('active') is None and not (H/'audit/night_queue.lock').exists()
assert not [j for j in cfg['jobs'] if j['id'] not in state['jobs']], 'Existing pending work must be reviewed before adding job'
assert json.loads((H/'audit/C0_KINEMATIC_BASE_ACCEPTANCE_20261103.json').read_text())['accepted_for_kinematics']
assert json.loads((H/'audit/kinematics_preflight_20261103/geometry_clearance.json').read_text())['conservative_full_range_clearance_m']>0
source=H/'cases/SP_C_split0_overset/relocation_reopen_20261103_082325/C0_recovered_t065.sim'
with source.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()=='c8b2396f2d087112d06045b06a6c62e93c4003eafde969aa8c8d0ca8120afc10'
job=dict(id='kinematic_poc333939_20261103',macro='KinematicPoc333939.java',input=str(source),approved=True,kind='kinematic',range_deg=[-5,5],initial_time_s=.65,gate='C0_accepted_for_kinematics',runtime_guards={'maximum_overset_error_cells':0},approval_evidence=str(H/'audit/C0_KINEMATIC_BASE_ACCEPTANCE_20261103.json'))
cfg['jobs'].append(job);cfg['controller_exit_requested']=False;cfg['accept_new_jobs']=True
(H/'NIGHT_QUEUE.json').write_text(json.dumps(cfg,indent=2),encoding='utf8')
review=json.loads((H/'WORK_CURRENT_REVIEW.json').read_text());review.update(current_job_kind='kinematic',current_mesh_cells=333939,current_case_label='C0 kinematic +/-5deg — FLOW FROZEN',last_decision='Baseline accepted for kinematics only. Launch one100-step cycle; full native mesh/connectivity audit every step. No force data acceptance.',next='Work review of sweep; prepare static+2 only on success.')
(H/'WORK_CURRENT_REVIEW.json').write_text(json.dumps(review,indent=2),encoding='utf8')
with (H/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),kind='kinematic_job_authorized',job=job,backups=str(backup)))+'\n')
print(json.dumps(dict(queue_ready=True,job=job,backups=str(backup)),indent=2))
