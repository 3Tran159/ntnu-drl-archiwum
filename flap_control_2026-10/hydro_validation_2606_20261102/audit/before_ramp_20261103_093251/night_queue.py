import math
"""Owned NTNU queue: serial, explicit approvals, scientific gates, never force-kills."""
from pathlib import Path
import os,sys,json,time,datetime,subprocess,hashlib,ctypes,shutil,re,csv,html,traceback
H=Path(__file__).resolve().parents[1]
CFG=H/'NIGHT_QUEUE.json'; STATE=H/'NIGHT_QUEUE_STATE.json'; LOCK=H/'audit/night_queue.lock'
ALLOWED={'B0URANSTopDirection.java','C0URANSTopDirection.java','InspectPressureOutlets.java','C0URANSPressureUrf01.java','C0URANSContinueInner40.java','C0TightURANSV2.java','C0TightURANS.java','InspectBMatchingNumerics.java','ContinueC0TightTurbulenceSecond.java','ContinueC0TightMomentumSecond.java','ContinueC0TightWarm.java','PrepareC0TightMappedFields.java','FreshC0TightContinuityInit.java','FreshC0TightInit.java','PrepareC0TightCagePatches.java','PrepareC0TightCage.java','PrepareC0ForewallCoverage.java','PrepareC0ForewallLayers.java','InspectC0LayerFailure.java','PrepareC0WallLayersZeroStorage.java','PrepareC0WallLayersCold.java','PrepareC0WallLayersFrozen.java','PrepareC0WallLayersRecut.java','PrepareC0WallLayers36.java','ContinueC0MomentumSecond.java','ContinueC0Flux.java','InspectHydroComparison.java','InspectNativeOverset.java','ResumeC0Qualified.java','C0InnerIterationTest.java','C0DistanceInterpolationTest.java','FreshC0DistanceInit.java','FreshC0NoContinuityInit.java','FreshC0NoFluxInit.java','PrepareC0OverlapRefinement.java','FinalizeC0MeshAudit.java','FinalizeC0DistanceMeshAudit.java','PrepareC0OverlapPatch.java','PrepareC0OverlapBand.java','FreshC0RefinedInit.java','FreshC0RelaxedInit.java','ContinueC0FirstOrder.java'}
ALLOWED.update(['KinematicPoc333939.java','PrepareStaticPlus2.java','BenchmarkStaticPlus2.java'])

def now():return datetime.datetime.now().astimezone().isoformat()
def read(p,default=None):
 try:return json.loads(p.read_text(encoding='utf8'))
 except FileNotFoundError:return default
def atomic(p,data):
 tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf8');os.replace(tmp,p)
def event(kind,**data):
 with (H/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=now(),kind=kind,**data),ensure_ascii=False)+'\n')
def processes():
 ps=r"""Get-CimInstance Win32_Process | ForEach-Object {[pscustomobject]@{pid=$_.ProcessId;ppid=$_.ParentProcessId;name=$_.Name;born=[string]$_.CreationDate.Ticks;ownedBatch=($_.Name -eq 'starccm+.exe' -and $_.CommandLine -match ' -batch ' -and $_.CommandLine.Contains('F:\ntnu\flap_control\hydro_validation_2606_20261102'))}} | ConvertTo-Json -Compress"""
 r=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=30,check=True)
 a=json.loads(r.stdout) if r.stdout.strip() else []
 return [a] if isinstance(a,dict) else a
class Memory(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(x,ctypes.c_ulonglong) for x in ['total','available','page_total','page_available','virtual_total','virtual_available','extended']]
def resources():
 m=Memory();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
 return dict(ram_available_GiB=round(m.available/1024**3,2),disk_free_GiB=round(shutil.disk_usage(H).free/1024**3,2))
def validate(cfg):
 assert cfg['max_cpu_processes']==16 and cfg['gpu_compute'] is False
 assert cfg['scientific_gates']['C0_bias_explained_and_approved'] is False or cfg['scientific_gates'].get('approval_evidence')
 ids=set()
 for j in cfg['jobs']:
  assert j['id'] not in ids;ids.add(j['id'])
  assert j['macro'] in ALLOWED
  p=Path(j['input']).resolve();assert p.is_file() and p.is_relative_to(H/'cases')
  if j.get('kind')=='kinematic':
   assert j['macro']=='KinematicPoc333939.java' and j.get('range_deg')==[-5,5]
   assert cfg['scientific_gates'].get('C0_accepted_for_kinematics') is True
  elif j.get('kind')=='benchmark':
   assert j['macro']=='BenchmarkStaticPlus2.java' and j.get('angle_deg')==2 and j.get('cpu_processes') in [8,12,16]
   assert cfg['scientific_gates'].get('kinematic_sweep_accepted') is True
  elif j.get('kind')=='static_preparation':
   assert j['macro']=='PrepareStaticPlus2.java' and j.get('angle_deg')==2
   assert cfg['scientific_gates'].get('kinematic_sweep_accepted') is True
  else:assert j.get('angle_deg',0)==0,'Nonzero hydrodynamic angles require a separate reviewed stage'
 return True
def output_path(receipt):
 if receipt['macro']=='BenchmarkStaticPlus2.java':return H/'cases/SP_C_split0_overset'/('plus2_benchmark_'+receipt['run_id'])
 if receipt['macro']=='PrepareStaticPlus2.java':return H/'cases/SP_C_split0_overset'/('static_plus2_prepared_'+receipt['run_id'])
 if receipt['macro']=='KinematicPoc333939.java':return H/'cases/SP_C_split0_overset'/('kinematic_poc_'+receipt['run_id'])
 if receipt['macro']=='B0URANSTopDirection.java':return H/'cases/SP_B_split0_fixed'/('b0_top_direction_'+receipt['run_id'])
 if receipt['macro']=='InspectPressureOutlets.java':return H/'audit'/('pressure_outlets_'+receipt['variant']+'_'+receipt['run_id'])
 if receipt['macro']=='InspectBMatchingNumerics.java':return H/'audit'/('matching_B_'+receipt['run_id'])
 if receipt['macro']=='InspectHydroComparison.java':return H/'audit'/('comparison_'+receipt['variant']+'_'+receipt['run_id'])
 if receipt['macro']=='InspectNativeOverset.java':return H/'audit'/('native_overset_'+receipt['run_id'])
 prefix={'C0URANSTopDirection.java':'c0_top_direction_','C0URANSPressureUrf01.java':'c0_urans_pressure_urf01_','C0URANSContinueInner40.java':'c0_urans_continue_inner40_','C0TightURANSV2.java':'c0_tight_urans_v2_','C0TightURANS.java':'c0_tight_urans_','ContinueC0TightTurbulenceSecond.java':'c0_tight_turbulence_second_','ContinueC0TightMomentumSecond.java':'c0_tight_momentum_second_','ContinueC0TightWarm.java':'c0_tight_warm_','PrepareC0TightMappedFields.java':'c0_tight_mapped_','FreshC0TightContinuityInit.java':'c0_tight_continuity_','FreshC0TightInit.java':'c0_tight_firstorder_','PrepareC0TightCagePatches.java':'c0_tight_cage_v2_','PrepareC0TightCage.java':'c0_tight_cage_v1_','PrepareC0ForewallCoverage.java':'c0_forewall36_coverage_','PrepareC0ForewallLayers.java':'c0_forewall36_','InspectC0LayerFailure.java':'c0_layers36_error_audit_','PrepareC0WallLayersZeroStorage.java':'c0_layers36_zero_storage_','PrepareC0WallLayersCold.java':'c0_layers36_cold_','PrepareC0WallLayersFrozen.java':'c0_layers36_frozen_','PrepareC0WallLayersRecut.java':'c0_layers36_recut_','PrepareC0WallLayers36.java':'c0_layers36_','ContinueC0MomentumSecond.java':'c0_momentum_second_','ContinueC0Flux.java':'c0_flux_recovery_','ContinueC0FirstOrder.java':'c0_first_order_','FreshC0RelaxedInit.java':'c0_relaxed_init_','FreshC0RefinedInit.java':'c0_refined_init_','PrepareC0OverlapBand.java':'c0_overlap_band05mm_','PrepareC0OverlapPatch.java':'c0_overlap_patch05mm_','FinalizeC0DistanceMeshAudit.java':'c0_overlap_distance_audit_','FinalizeC0MeshAudit.java':'c0_overlap_audit_','PrepareC0OverlapRefinement.java':'c0_overlap1mm_','FreshC0NoFluxInit.java':'c0_fresh_noflux_','FreshC0NoContinuityInit.java':'c0_fresh_noci_','FreshC0DistanceInit.java':'c0_distance_fresh_','C0InnerIterationTest.java':'c0_inner40_','C0DistanceInterpolationTest.java':'c0_distance_','ResumeC0Qualified.java':'c0_resume_'}[receipt['macro']]
 return H/'cases/SP_C_split0_overset'/(prefix+receipt['run_id'])
def scan_current(st,plist):
 rec=st.get('active');metrics={}
 if not rec:return metrics
 out=Path(rec['output']);log=Path(rec['log']);metrics['physical_time_s']=rec.get('initial_time_s')
 if log.exists():
  with log.open('rb') as f:f.seek(max(0,log.stat().st_size-160000));tail=f.read().decode('utf8','replace')
  t=re.findall(r'TimeStep\s+(\d+):\s+Time\s+([+\d.eE-]+)',tail)
  if t:metrics.update(timestep=int(t[-1][0]),physical_time_s=float(t[-1][1]))
  its=re.findall(r'^\s*(\d+)\s+[+\d.eE-]+\s+[+\d.eE-]+',tail,re.M)
  if its:metrics['iteration']=int(its[-1])
  metrics['log_updated_at']=datetime.datetime.fromtimestamp(log.stat().st_mtime).astimezone().isoformat()
  metrics['seconds_without_log_write']=round(time.time()-log.stat().st_mtime)
  save_lines=[line for line in tail.splitlines() if 'Saving:' in line]
  metrics['saving_or_exporting']=bool(save_lines and 'complete (' not in save_lines[-1])
  metrics['native_exit_code']=int(re.findall(r'Server process exited with code\s*:\s*(\d+)',tail)[-1]) if re.findall(r'Server process exited with code\s*:\s*(\d+)',tail) else None
 rows=[];steady=rec['macro'].startswith(('FreshC0','ContinueC0'));hp=out/('pose_preparation.csv' if rec['macro']=='PrepareStaticPlus2.java' else 'steady_iterations.csv' if steady else 'history.csv')
 if hp.exists():
  try:
   with hp.open(encoding='utf8') as f:rows=list(csv.DictReader(f))
   if rows:
    row=rows[-1]
    for k in ['flap_angle_deg','flap_angular_velocity_deg_s','angle_error_deg','center_error_m','min_volume_m3','min_cell_quality','min_face_validity','time_s','CL_hydro','CD','Mh_Nm','p_absolute_min_Pa','mass_imbalance_relative','overset_error_cells','difficult_interpolation_cells','omega_floor_cells','k_floor_cells','max_turbulent_viscosity_ratio']:
     if row.get(k):metrics[k]=float(row[k])
    metrics['physical_time_s']=0.0 if steady else float(row['time_s'])
    if steady:metrics['iteration']=int(row.get('native_iteration') or row['iteration']);metrics['additional_iterations']=int(row['iteration']);metrics['steady_initialization']=True
    if row.get('angle_deg'):metrics['flap_angle_deg']=float(row['angle_deg'])
    metrics['history_rows']=len(rows)
  except (ValueError,KeyError):pass
 ckpts=sorted(out.glob('*.sim'),key=lambda x:x.stat().st_mtime) if out.exists() else []
 complete_ckpts=[cp for cp in ckpts if time.time()-cp.stat().st_mtime>2]
 if complete_ckpts and log.exists():
  candidate=complete_ckpts[-1];cache=st.setdefault('checkpoint_integrity',{})
  if str(candidate) not in cache:
   native_log=log.read_text(encoding='utf8',errors='replace')
   save_done=any('Saving:' in line and str(candidate) in line and 'complete (' in line for line in native_log.splitlines())
   if save_done:
    before=candidate.stat()
    with candidate.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    after=candidate.stat()
    if before.st_size==after.st_size and before.st_mtime_ns==after.st_mtime_ns:
     saved_time=rec.get('initial_time_s')
     match=re.match(r'checkpoint_step_(\d+)\.sim',candidate.name)
     if match:
      selected=[r for r in rows if int(r['step'])==int(match.group(1))]
      if selected:saved_time=float(selected[-1]['time_s'])
     elif candidate.name in ['checkpoint.sim','error_checkpoint.sim','motion_verified.sim','SP_C_plus2_prepared_NOT_SOLVED_2606.sim'] and rows:saved_time=float(rows[-1]['time_s'])
     cache[str(candidate)]=dict(path=str(candidate),bytes=after.st_size,sha256=digest,saved_time_s=saved_time,native_save_complete=True,hash_at=now(),native_reopen_verified=False)
  if str(candidate) in cache:
   metrics['last_output_sim']=str(candidate);metrics['checkpoint_integrity']=cache[str(candidate)]
 alive={p['pid']:p for p in plist};tracked=st.setdefault('owned_processes',{})
 roots={p['pid'] for p in plist if p['ownedBatch']}|{int(pid) for pid,born in tracked.items() if pid.isdigit() and int(pid) in alive and alive[int(pid)]['born']==born}
 if rec['pid'] in alive and alive[rec['pid']]['ownedBatch']:roots.add(rec['pid'])
 changed=True
 while changed:
  changed=False
  for p in plist:
   if p['ppid'] in roots and p['ppid'] in alive and p['pid'] not in roots and int(p['born'] or 0)>=int(alive[p['ppid']]['born'] or 0)>0:roots.add(p['pid']);changed=True
 for pid in roots:
  if pid in alive:tracked[str(pid)]=alive[pid]['born']
 metrics['owned_active_pids']=sorted(p for p in roots if p in alive)
 status=read(out/'status.json')
 metrics['macro_status']=status
 metrics['operation']='MESH_PREPARATION' if rec['macro'].startswith(('Prepare','Finalize')) else 'STEADY_INITIALIZATION' if steady else 'READ_ONLY_AUDIT' if rec['macro'].startswith('Inspect') else ('RUNNING' if metrics.get('physical_time_s',0)>rec.get('initial_time_s',.3024) else 'STARTING')
 if not metrics['owned_active_pids']:
  success=status is not None and (status.get('status') in ['benchmark_complete','static_pose_prepared','kinematic_poc_passed','inspection_complete','steady_diagnostic_ready','mesh_connectivity_prepared','urans_diagnostic_ready'] or (status.get('status')=='force_stabilization_passed' and status.get('hydrodynamic_convergence_verified')))
  if metrics.get('native_exit_code') not in [None,0]:success=False
  rec['ended_at']=now();rec['state']='completed' if success else 'failed';rec['macro_status']=status
  for cp in ckpts:
   stat=cp.stat()
   with cp.open('rb') as cf:digest=hashlib.file_digest(cf,'sha256').hexdigest()
   rec.setdefault('checkpoints',[]).append(dict(path=str(cp),bytes=stat.st_size,sha256=digest))
  if log.exists():
   redacted=re.sub(r'(?i)(-podkey\s+)\S+',r'\1[REDACTED]',log.read_text(encoding='utf8',errors='replace'))
   dest=H/'runs/redacted'/log.name;dest.parent.mkdir(exist_ok=True);dest.write_text(redacted,encoding='utf8');rec['redacted_log']=str(dest)
  if success and not rec['macro'].startswith('Inspect') and not metrics.get('checkpoint_integrity',{}).get('native_save_complete'):
   success=False;rec['state']='failed';rec['completion_error']='No verified native complete checkpoint'
  from queue_safety import automatic_job_report
  automatic_job_report(H,rec)
  st['jobs'][rec['id']]=rec;st['active']=None;st['last_metrics']=metrics;st['owned_processes']={}
  if not success:st['failure_hold']=rec['id']
  st['queue_state']='HOLD_FAILED_JOB' if not success else 'HOLD_SCIENTIFIC_REVIEW'
  event('job_completed' if success else 'job_failed',job=rec['id'],output=str(out),macro_status=status)
 return metrics

def last_flow_snapshot(st,metrics):
 active=st.get('active')
 if active and active['macro'] not in ['KinematicPoc333939.java','PrepareStaticPlus2.java'] and not active['macro'].startswith('Inspect') and metrics.get('history_rows',0)>0:
  return {k:v for k,v in metrics.items() if k!='owned_active_pids'}
 jobs=[j for j in st['jobs'].values() if j.get('macro') and j['macro'] not in ['KinematicPoc333939.java','PrepareStaticPlus2.java'] and not j['macro'].startswith('Inspect') and j.get('output')]
 jobs.sort(key=lambda j:j.get('ended_at',''),reverse=True)
 for rec in jobs:
  steady=rec['macro'].startswith(('FreshC0','ContinueC0'))
  hp=Path(rec['output'])/('steady_iterations.csv' if steady else 'history.csv')
  if not hp.exists():continue
  with hp.open(encoding='utf8') as f:rows=list(csv.DictReader(f))
  if not rows:continue
  row=rows[-1];v=dict(job_id=rec['id'],physical_time_s=0.0 if steady else float(row['time_s']),history_rows=len(rows))
  if steady:v.update(iteration=int(row.get('native_iteration') or row['iteration']),additional_iterations=int(row['iteration']),steady_initialization=True,operation='STEADY_INITIALIZATION')
  for key in ['time_s','CL_hydro','CD','Mh_Nm','p_absolute_min_Pa','mass_imbalance_relative','omega_floor_cells','k_floor_cells','max_turbulent_viscosity_ratio','overset_error_cells','difficult_interpolation_cells']:
   if row.get(key):v[key]=float(row[key])
  cp=Path(rec['output'])/('steady_checkpoint.sim' if steady else 'checkpoint.sim')
  if not cp.exists():
   alternatives=sorted(Path(rec['output']).glob('*.sim'),key=lambda x:x.stat().st_mtime)
   if alternatives:cp=alternatives[-1]
  if cp.exists():
   v['last_output_sim']=str(cp)
   if str(cp) in st.get('checkpoint_integrity',{}):v['checkpoint_integrity']=st['checkpoint_integrity'][str(cp)]
  log=Path(rec['log'])
  if log.exists() and not steady:
   with log.open('rb') as f:f.seek(max(0,log.stat().st_size-160000));tail=f.read().decode('utf8','replace')
   ts=re.findall(r'TimeStep\s+(\d+):\s+Time\s+([+\d.eE-]+)',tail);it=re.findall(r'^\s*(\d+)\s+[+\d.eE-]+\s+[+\d.eE-]+',tail,re.M)
   if ts:v['timestep']=int(ts[-1][0])
   if it:v['iteration']=int(it[-1])
  return v
 return metrics or st.get('last_metrics',{})

def publish(st,cfg,metrics,rs):
 view=dict(at=now(),queue_pid=os.getpid(),queue_state=st.get('queue_state','MONITORING'),active=st.get('active'),metrics=metrics or st.get('last_metrics',{}),resources=rs,scientific_gates=cfg['scientific_gates'],jobs=st['jobs'],next_job=st.get('next_job'),failure_hold=st.get('failure_hold'),max_cpu_processes=16,gpu_compute=False)
 view['flow_metrics']=last_flow_snapshot(st,view['metrics'])
 atomic(H/'NIGHT_DASHBOARD.json',view)
 body=html.escape(json.dumps(view,indent=2,ensure_ascii=False))

 atomic(STATE,st)
 base=read(H/'validation/C0_actual_resume_20261102_221053.json',{})
 base['historical_resume_checkpoint']={k:base.pop(k,None) for k in ['bytes','sha256','timestep','iteration','start_time_s']}
 active=st.get('active')
 base.update(at=view['at'],local_queue_started=True,queue_pid=os.getpid(),queue_state=view['queue_state'],resources=rs,scientific_gates=cfg['scientific_gates'],active_operation=active['macro'] if active else 'Awaiting scientific decision',active_input=active['input'] if active else None,actual_live_metrics=view['metrics'],dashboard=str(H/'NIGHT_DASHBOARD.html'))
 if active and not active['macro'].startswith('Inspect'):
  moving=(view['metrics'].get('physical_time_s',0)>active.get('initial_time_s',0) or (view['metrics'].get('steady_initialization') and view['metrics'].get('iteration',0)>0)) and bool(view['metrics'].get('owned_active_pids'))
  base['solver_state']='RUNNING' if moving else 'STOPPED'
  if moving and view['metrics'].get('seconds_without_log_write',0)>900 and not view['metrics'].get('saving_or_exporting'):base['solver_state']='STALLED'
  base['physical_time_s']=view['metrics'].get('physical_time_s',active.get('initial_time_s'))
  if view['metrics'].get('last_output_sim'):base['last_checkpoint']=view['metrics']['last_output_sim']
 else:base['solver_state']='STOPPED'
 if view['metrics'].get('history_rows',0)>0:
  base['physical_time_s']=view['metrics'].get('physical_time_s')
  if view['metrics'].get('last_output_sim'):base['last_checkpoint']=view['metrics']['last_output_sim']
 base['historical_resume_stop_reason']=base.pop('stop_reason','')
 for key in ['timestep','iteration']:
  if key in view['metrics']:base[key]=view['metrics'][key]
 if active:base['start_time_s']=active.get('initial_time_s')
 if view['metrics'].get('checkpoint_integrity'):base['last_checkpoint_integrity']=view['metrics']['checkpoint_integrity']
 if not active or active['macro'].startswith('Inspect'):
  flow=view['flow_metrics']
  if flow.get('physical_time_s') is not None:base['physical_time_s']=flow['physical_time_s']
  if flow.get('last_output_sim'):base['last_checkpoint']=flow['last_output_sim']
  for key in ['timestep','iteration']:
   if key in flow:base[key]=flow[key]
   else:base.pop(key,None)
  if flow.get('checkpoint_integrity'):base['last_checkpoint_integrity']=flow['checkpoint_integrity']
  if active:base['inspection_input_time_s']=active.get('initial_time_s')
 if view['flow_metrics'].get('steady_initialization'):
  base['dt_s']=None;base.pop('timestep',None);base['last_solved_case']='C0 steady initialization; mesh size recorded in the source mesh review';base['time_note']='Steady numerical initialization: physical time does not advance'
 if active and not view['metrics'].get('last_output_sim'):
  fallback=view['flow_metrics']
  if fallback.get('last_output_sim'):base['last_checkpoint']=fallback['last_output_sim']
  if fallback.get('checkpoint_integrity'):base['last_checkpoint_integrity']=fallback['checkpoint_integrity']
 if active and active['macro'].startswith(('FreshC0','ContinueC0')):
  base['dt_s']=None;base.pop('timestep',None);base['last_solved_case']='C0 steady initialization; mesh size recorded in the source mesh review';base['time_note']='Separate steady numerical initialization at physical time 0; previous transient checkpoint preserved'
 base['current_case_path']=active['output'] if active else None
 if not active:base['solver_state']='STOPPED' if any((H.parent/n).exists() for n in ['PAUSED_FOR_HOME.json','STOP_OWNED_CFD.json']) else 'HOLD'
 elif view['metrics'].get('saving_or_exporting'):base['solver_state']='SAVING'
 elif base['solver_state']=='STALLED':base['solver_state']='HOLD';base['stall_detected']=True
 base['operation']=base['solver_state']
 base['solver_actually_advancing']=base['solver_state']=='RUNNING'
 base['flow_frozen']=bool(active and active['macro'] in ['KinematicPoc333939.java','PrepareStaticPlus2.java'])
 if base['flow_frozen']:base['flow_reference_time_s']=.65;base['hydrodynamic_data_valid']=False
 view['solver_state']=base['solver_state'];view['operation']=base['operation'];view['flow_frozen']=base['flow_frozen']
 atomic(H/'NIGHT_DASHBOARD.json',view)
 base['flow_solution_approved']=False
 cache=st.get('checkpoint_integrity',{})
 if cache:base['latest_owned_checkpoint']=max(cache.values(),key=lambda c:c.get('hash_at',''))
 transient_st=dict(st);transient_st['jobs']={k:j for k,j in st['jobs'].items() if j.get('output') and (Path(j['output'])/'history.csv').exists()}
 if not active or active['macro'].startswith(('Fresh','ContinueC0','Prepare','Finalize','Inspect')):transient_st['active']=None
 transient=last_flow_snapshot(transient_st,{})
 if transient.get('last_output_sim'):
  base['last_transient_checkpoint']=transient['last_output_sim'];base['last_transient_time_s']=transient.get('physical_time_s')
 if active and active['macro']!='PrepareStaticPlus2.java' and active['macro'].startswith(('Prepare','Finalize')):
  base['meshing_or_audit_active']=bool(view['metrics'].get('owned_active_pids'));base['time_note']='Mesh-only stage: physical time0, no flow iterations'
 review=read(H/'WORK_CURRENT_REVIEW.json',{});base['work_review']=review;base['current_obstacle']=review.get('obstacle','C0 bias unresolved; no deflections approved');base['reviewed_recovery_checkpoint']=review.get('reviewed_recovery_checkpoint')
 base['max_cpu_processes']=cfg['max_cpu_processes'];base['local_queue_started']=st.get('queue_state')!='CONTROLLER_STOPPED'
 base['C0_bias_status']=cfg['scientific_gates'].get('reason','')
 flowpath=str(view['flow_metrics'].get('last_output_sim',''))
 if any(tag in flowpath for tag in ['c0_tight_','c0_urans_','c0_top_direction_']):
  base['last_solved_case']='C0 split flap,0degrees,Overset,333939cells';base['mesh_cells']=333939
 elif 'SP_B_split0_fixed' in flowpath:
  base['last_solved_case']='B0 split flap,0degrees,noOverset,256750cells';base['mesh_cells']=256750
 if active and review.get('current_run')==active.get('output'):
  base['current_case_label']=review.get('current_case_label',active['id']);base['current_case_mesh_cells']=review.get('current_mesh_cells')
  if view['metrics'].get('history_rows',0)>0:
   base['last_solved_case']=base['current_case_label'];base['mesh_cells']=review.get('current_mesh_cells')
 base['reviewed_recovery_checkpoint']=review.get('current_case_checkpoint',review.get('latest_top_boundary_checkpoint',review.get('reviewed_recovery_checkpoint')))
 if review.get('current_job_kind') in ['kinematic','static_preparation']:
  from night_mechanics_dashboard import synchronize
  synchronize(H,st,view,base,review)
  atomic(H/'NIGHT_DASHBOARD.json',view)
 if review.get('current_job_kind')=='benchmark':
  from benchmark_telemetry import publish_benchmark
  publish_benchmark(H,view,base,st,review)
  atomic(H/'NIGHT_DASHBOARD.json',view)
 if review.get('current_job_kind')=='plus2_hold':
  failed=read(H/'audit/STATIC_PLUS2_RESULT_20261103.json',{})
  base.update(last_solved_case='Static+2 failed diagnostic; scientifically rejected',physical_time_s=failed.get('time_s'),iteration=failed.get('iteration'),mesh_cells=333939,current_case_path=str(Path(failed['checkpoint']).parent),last_checkpoint=failed['checkpoint'],flow_solution_approved=False,hydrodynamic_solver_advancing=False)
  base['operation']=base['solver_state'];view['operation']=view['solver_state']=base['solver_state']
  if view.get('metrics'):view['metrics']['operation']=base['solver_state']
  atomic(H/'NIGHT_DASHBOARD.json',view)
 atomic(H/'NIGHT_STATUS.json',base)
 try:
  from night_dashboard import render
  render(H,view,base)
 except Exception:event('dashboard_render_error',error=traceback.format_exc())
def main():
 cfg=read(CFG);validate(cfg)
 if '--check' in sys.argv:print(json.dumps(dict(valid=True,jobs=[j['id'] for j in cfg['jobs']],resources=resources())));return
 plist=processes();alive={p['pid'] for p in plist}
 old=read(LOCK,{})
 if old.get('pid') in alive and (not old.get('born') or any(p['pid']==old['pid'] and p['born']==old['born'] for p in plist)):raise RuntimeError('Queue already active; adopt its state, do not start duplicate')
 if LOCK.exists():shutil.copy2(LOCK,H/'audit'/('night_queue_stale_'+datetime.datetime.now().strftime('%H%M%S')+'.json'));LOCK.unlink()
 with LOCK.open('x',encoding='utf8') as f:json.dump(dict(pid=os.getpid(),at=now(),born=next((p['born'] for p in plist if p['pid']==os.getpid()),None)),f)
 try:
  from benchmark_telemetry import start_telemetry
  start_telemetry(H)
 except Exception:event('optional_telemetry_unavailable',error=traceback.format_exc())
 st=read(STATE,dict(jobs={},active=None));st['controller_started_at']=now();st['controller_pid']=os.getpid();event('controller_started',pid=os.getpid())
 try:
  while True:
   cfg=read(CFG)
   if cfg.get('controller_exit_requested') and not st.get('active'):
    st['queue_state']='CONTROLLER_STOPPED';publish(st,cfg,{},resources());event('controller_graceful_exit');break
   validate(cfg);plist=processes();rs=resources()
   from queue_safety import recover_launch
   recovered=recover_launch(H,st,cfg,plist,output_path)
   if recovered:event(recovered)
   if not st.get('active'):
    pending=[j for j in cfg['jobs'] if j['id'] not in st['jobs'] and not j.get('disabled')]
    st['next_job']=pending[0]['id'] if pending else None
    if (H.parent/'STOP_OWNED_CFD.json').exists() or (H.parent/'PAUSED_FOR_HOME.json').exists():st['queue_state']='PAUSED_BY_MARKER'
    elif st.get('failure_hold') and not cfg.get('release_failure_hold',{}).get(st['failure_hold']):st['queue_state']='HOLD_FAILED_JOB'
    elif cfg.get('accept_new_jobs') is False:st['queue_state']='HOLD_NO_NEW_JOBS'
    elif not pending:st['queue_state']='HOLD_SCIENTIFIC_REVIEW'
    else:
     j=pending[0]
     if not j.get('approved'):st['queue_state']='HOLD_APPROVAL'
     elif j.get('gate') and not cfg['scientific_gates'].get(j['gate']):st['queue_state']='HOLD_SCIENTIFIC_GATE'
     elif j.get('adopt_receipt'):
      rec=read(Path(j['adopt_receipt']));rec.update(id=j['id'],output=str(output_path(rec)),initial_time_s=j.get('initial_time_s',0),state='active');st['active']=rec;event('adopt_existing_job',job=j['id'],pid=rec['pid'])
     elif any(p['ownedBatch'] for p in plist):st['queue_state']='WAIT_EXISTING_OWNED_STAR'
     elif rs['ram_available_GiB']<8 or rs['disk_free_GiB']<15:st['queue_state']='WAIT_RESOURCES'
     else:
      from queue_safety import launch_integrity
      try:launch_integrity(H,j)
      except Exception as integrity_error:
       st['failure_hold']=j['id'];st['jobs'][j['id']]=dict(state='input_integrity_failed',reason=str(integrity_error));publish(st,cfg,{},rs);event('input_integrity_failed',job=j['id'],reason=str(integrity_error));continue
      st['launch_intent']=dict(id=j['id'],at=now());st['queue_state']='LAUNCHING';publish(st,cfg,{},rs)
      result=subprocess.run([sys.executable,str(H/'tools/night_native.py'),j['macro'],j['input']]+([str(j['cpu_processes'])] if 'cpu_processes' in j else []),capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
      if result.returncode:
       st.pop('launch_intent',None);st['failure_hold']=j['id'];st['jobs'][j['id']]=dict(state='launch_failed',at=now());event('launch_failed',job=j['id'],returncode=result.returncode)
       (H/'audit'/('queue_launch_error_'+j['id']+'.txt')).write_text(re.sub(r'(?i)(-podkey\s+)\S+',r'\1[REDACTED]',result.stderr),encoding='utf8')
      else:
       rec=read(H/'audit/night_launch_latest.json');assert rec['macro']==j['macro'] and rec['input']==j['input']
       rec.update(id=j['id'],output=str(output_path(rec)),initial_time_s=j.get('initial_time_s',0),state='active');st['active']=rec;st.pop('launch_intent',None);st['next_job']=None;event('job_launched',job=j['id'],pid=rec['pid'],macro=j['macro'])
   metrics=scan_current(st,processes())
   if st.get('active'):
    st['queue_state']='MONITORING'
    if rs['ram_available_GiB']<4 or rs['disk_free_GiB']<5:
     marker=H.parent/'STOP_OWNED_CFD.json'
     if not marker.exists():atomic(marker,dict(source='night_queue',reason='resource_floor',at=now(),resources=rs));event('graceful_pause_requested',reason='resource_floor')
     st['queue_state']='RESOURCE_PAUSE_REQUESTED'
   if st.get('active'):
    active_job=next(j for j in cfg['jobs'] if j['id']==st['active']['id'])
    from queue_safety import job_watchdog
    stalled=job_watchdog(st['active'],metrics,active_job)
    if stalled:
     marker=H.parent/'STOP_OWNED_CFD.json'
     if not marker.exists():atomic(marker,dict(source='night_queue',reason=stalled,at=now(),target_job=st['active']['id']));event('watchdog_graceful_stop_requested',reason=stalled,job=st['active']['id'])
     st['queue_state']='WATCHDOG_HOLD';cfg['accept_new_jobs']=False;atomic(CFG,cfg)
    runtime=active_job.get('runtime_guards',{})
    violations=[]
    for key,metric,lower in [('minimum_absolute_pressure_Pa','p_absolute_min_Pa',True),('maximum_mass_imbalance_relative','mass_imbalance_relative',False),('maximum_omega_floor_cells','omega_floor_cells',False),('maximum_k_floor_cells','k_floor_cells',False),('maximum_turbulent_viscosity_ratio','max_turbulent_viscosity_ratio',False),('maximum_overset_error_cells','overset_error_cells',False)]:
     if key in runtime and metric in metrics:
      val=float(metrics[metric]);limit=float(runtime[key])
      if not math.isfinite(val) or (val<=limit if lower else val>limit):violations.append(dict(metric=metric,value=val,limit=limit))
    if violations:
     marker=H.parent/'STOP_OWNED_CFD.json'
     if not marker.exists():atomic(marker,dict(source='night_queue',reason='scientific_runtime_gate',at=now(),target_job=st['active']['id'],violations=violations));event('graceful_pause_requested',reason='scientific_runtime_gate',job=st['active']['id'],violations=violations)
     st['queue_state']='SCIENTIFIC_PAUSE_REQUESTED'
   publish(st,cfg,metrics,rs)
   if '--once' in sys.argv:break
   time.sleep(30)
 except Exception:
  event('controller_error',error=traceback.format_exc());raise
 finally:
  if read(LOCK,{}).get('pid')==os.getpid():LOCK.unlink()
if __name__=='__main__':main()
