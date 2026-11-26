"""Persisted standalone workflow. Import/selection never starts flow; starts are explicit."""
from pathlib import Path
import json,math,hashlib,datetime,uuid,os,subprocess,contextlib
import run_until_settled as e
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029');D=R/'local_control'
FIXED=dict(z_m=[-22,8],waterline_m=2,depth_m=24,span_m=.02,U_m_s=18,inner=10,order='SECOND_ORDER',pressure_AMG_tolerance=.01)
PRESETS=[('W01a',.5,20),('W02',.5,30),('W03',.25,20),('W04',.75,20),('W05',.25,30),('W06',.75,30),('W07',.5,10),('W08',.5,40)]
TESTED_SOURCES=('local_control_model.py','local_control_worker.py','local_domain_preparation.py','local_mesh_inputs.py','LocalCalmWave.java','local_wave_arrival.py','wave_cycle_repeatability.py','PrepareLocalMeshCalm.java','audit_selected_mesh_domain.py','local_recipe_validation.py')
def read(p):return e.read(p,{})
def write(p,x):e.write(Path(p),x)
def stamp():return e.stamp()
def hold():return read(R/'campaign_hold.json')
def mesh_inputs():
 import local_mesh_inputs as mi
 return mi
def mesh_profile(mesh_id=None):
 mi=mesh_inputs()
 if mesh_id:
  matches=[x for x in mi.list_entries() if x.get('id')==mesh_id]
  if len(matches)!=1:raise ValueError('Choose an inspected mesh from the list')
  p=matches[0]
 else:p=mi.selected()
 if not p or p.get('status') not in ('ready','compatible','mechanically_compatible','mesh_inspection_passed'):raise ValueError('Inspect and select a prepared mesh .sim first')
 return p
def validate(raw):
 allowed={'name','height_m','wavelength_m','upstream_m','downstream_m','wall_minutes','action','mesh_id','checkpoint_interval_s'}
 if not isinstance(raw,dict) or set(raw)-allowed:raise ValueError('Unknown configuration fields')
 def n(k,lo,hi,default=None):
  v=raw.get(k,default)
  if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not lo<=v<=hi:raise ValueError(k+' is outside the supported range')
  return float(v)
 h=n('height_m',.25,.75);lam=n('wavelength_m',10,40)
 if h not in (.25,.5,.75) or lam not in (10,20,30,40):raise ValueError('Choose a supported wave height and wavelength')
 up=n('upstream_m',11.9,100);down=n('downstream_m',10,120);xmax=down+1.19;length=up+xmax
 if length<3*lam-1e-6 or length>max(4*lam,80)+1e-6 or length>160+1e-6:raise ValueError('Domain must span 3-4 wavelengths (up to 80 m for short waves), at most 160 m')
 if -up+lam>-2 or xmax-lam<5:raise ValueError('Generation/damping zones must leave the foil and wake clear')
 wall=n('wall_minutes',10,720);checkpoint=n('checkpoint_interval_s',.05,1,.05)
 name=str(raw.get('name','Custom'))[:40]
 if not name or any(ord(x)<32 for x in name):raise ValueError('Invalid display name')
 action=raw.get('action','run')
 if action not in ('run','prepare'):raise ValueError('Choose run or prepare')
 p=mesh_profile(raw.get('mesh_id'));dt=float(p['dt_s'])
 if not math.isfinite(dt) or not .0001-1e-12<=dt<=.001+1e-12 or p.get('inner')!=10:raise ValueError('Inspected numerical profile is unsupported; configure the .sim and inspect a new copy')
 if abs(checkpoint/dt-round(checkpoint/dt))>1e-7:raise ValueError('Checkpoint interval must be a whole number of time steps')
 return dict(name=name,height_m=h,wavelength_m=lam,xmin_m=-up,xmax_m=xmax,zone_m=lam,upstream_m=up,downstream_m=down,length_m=length,wall_minutes=wall,action=action,checkpoint_interval_s=checkpoint,mesh_id=p['id'],mesh=p.get('label',p['id']),mesh_sha256=p['file_sha256'],mesh_cgns=p['mesh_cgns'],mesh_sim=p['mesh_sim'],mesh_cells=p['cells'],mesh_domain_x_m=p['domain_x_m'],dt_s=dt,**FIXED)
def domain_key(s):
 keys=('mesh_id','mesh_sha256','xmin_m','xmax_m','zone_m','dt_s','inner','order','pressure_AMG_tolerance')
 x={k:s[k] for k in keys};x.update(FIXED)
 return hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()[:20]
def default_domain(s):return all(abs(a-b)<1e-7 for a,b in zip(s['mesh_domain_x_m'],[s['xmin_m'],s['xmax_m']]))
def canonical(s):return {k:s[k] for k in ('name','height_m','wavelength_m','upstream_m','downstream_m','wall_minutes','action','mesh_id','checkpoint_interval_s')}
def registered_calm(s,verify=False):
 key=domain_key(s);reg=read(D/'calm'/f'{key}.json');p=Path(reg.get('manifest','missing'));v=read(p)
 f=Path(v.get('file','missing'));t=v.get('physical_time_s');gate=v.get('settling',{})
 if isinstance(t,bool) or not isinstance(t,(int,float)) or not math.isfinite(t) or t<=0:return None
 if v.get('status')!='calm_force_settled' or not gate.get('passed',gate.get('pass',False)) or not v.get('source_unchanged') or not f.is_file():return None
 if v.get('mesh_id')!=s['mesh_id'] or v.get('mesh_sha256')!=s['mesh_sha256'] or v.get('domain_key')!=key:return None
 if v.get('domain_x_m')!=[s['xmin_m'],s['xmax_m']] or v.get('domain_z_m')!=[-22,8] or v.get('dt_s')!=s['dt_s'] or v.get('inner')!=s['inner'] or v.get('order')!='SECOND_ORDER' or v.get('pressure_AMG_tolerance')!=.01 or v.get('wave_active') is not False:return None
 if verify and e.digest(f)!=v.get('sha256'):raise ValueError('Computed C01 file changed; inspect before launch')
 return dict(v,manifest=str(p),domain_key=key)
def enqueue(raw):
 s=validate(raw);jobid=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]
 folder=D/'jobs'/jobid;folder.mkdir(parents=True,exist_ok=False)
 j=dict(id=jobid,status='queued',created_at=stamp(),spec=s,domain_key=domain_key(s),attempts=[],results=[],message='Saved to queue. Explicit Start is required; no calculation launched')
 write(folder/'job.json',j);return j
def jobs():
 root=D/'jobs'
 return sorted((read(p) for p in root.glob('*/job.json')),key=lambda j:(j.get('created_at',''),j.get('id',''))) if root.exists() else []
def process_alive(pid):
 if not isinstance(pid,int) or pid<=0:return False
 import ctypes
 k=ctypes.windll.kernel32;k.OpenProcess.restype=ctypes.c_void_p;h=k.OpenProcess(0x1000,False,pid)
 if not h:return False
 try:
  n=ctypes.c_ulong();return bool(k.GetExitCodeProcess(ctypes.c_void_p(h),ctypes.byref(n))) and n.value==259
 finally:k.CloseHandle(ctypes.c_void_p(h))
def readiness():
 a=read(R/'local_control_macro_receipt.json');b=read(R/'local_control_zero_step_review.json');t=read(R/'local_control_test_review.json')
 tested=t.get('source_sha256',{});hashes_match=all((R/name).is_file() and tested.get(name)==e.digest(R/name) for name in TESTED_SOURCES)
 compile_ok=a.get('status')=='javac_passed' and (R/'LocalCalmWave.java').is_file() and a.get('macro_sha256')==e.digest(R/'LocalCalmWave.java')
 api_ok=b.get('status')=='zero_step_API_audit_passed' and a.get('macro_sha256')==b.get('macro_sha256')
 tests_ok=t.get('status')=='passed' and hashes_match
 try:p=mesh_profile();mesh_ok=True;mesh_message=p.get('label',p['id'])
 except (ValueError,ImportError,KeyError):mesh_ok=False;mesh_message='Paste a prepared mesh .sim path, inspect it and select the imported copy'
 checks=[dict(name='Mesh input',ok=mesh_ok,message=mesh_message),dict(name='Macro compiled',ok=compile_ok,message='Java compilation'),dict(name='Controller tests',ok=tests_ok,message='Tests bound to the current source files'),dict(name='Zero-step recipe check',ok=api_ok,message='Use Check recipe after compilation/tests; it performs no flow steps'),dict(name='Campaign hold released',ok=not hold().get('active'),message=hold().get('reason','No campaign hold'))]
 recipe=compile_ok and api_ok and tests_ok
 return dict(ready=recipe and mesh_ok and not hold().get('active'),recipe_ready=recipe,compile_ok=compile_ok,tests_ok=tests_ok,api_ok=api_ok,can_validate_recipe=compile_ok and tests_ok,checks=checks,message='Ready for explicit local starts; scientific accuracy remains a separate check' if recipe and mesh_ok and not hold().get('active') else 'No automatic start. Complete the checks listed below')
def acknowledge(jobid):
 p=job_path(jobid);j=read(p)
 if j.get('status')!='needs_review':raise ValueError('Job is not awaiting review')
 j.update(status='reviewed_archived',review_acknowledged_at=stamp(),message='Review acknowledged; preserved attempt archived. Failed fields are never resumed');write(p,j)
def release_hold():
 mesh_profile()
 h=hold()
 h.update(active=False,status='released_explicitly_by_user',released_at=stamp(),reason='User enabled the selected mesh workflow; queue remains paused until explicit Start')
 write(R/'campaign_hold.json',h);D.mkdir(exist_ok=True);(D/'PAUSE').touch()
 return dict(message='Campaign hold released. Queue remains paused; no calculation started.')
def start_worker(resume=True):
 if hold().get('active'):raise ValueError('Campaign on hold pending mesh review. Explicitly enable the selected mesh workflow first')
 if not resume and (D/'PAUSE').exists():raise ValueError('Queue paused; automated start refused')
 if not readiness()['ready']:raise ValueError('Complete the local recipe and selected-mesh checks first')
 if any(j.get('status')=='needs_review' for j in jobs()):raise ValueError('A failed job needs review acknowledgement before more work')
 if not any(j.get('status') in ('queued','waiting') for j in jobs()):raise ValueError('No queued job. Use Continue saved run for a paused calculation')
 lock=D/'worker.lock'
 if lock.exists():
  v=read(lock)
  if process_alive(v.get('pid')):return dict(status='running',pid=v['pid'])
  raise ValueError('Stale local queue lock needs inspection; no controller is blindly restarted')
 D.mkdir(exist_ok=True)
 if resume and (D/'PAUSE').exists():(D/'PAUSE').unlink()
 with (D/('worker_'+uuid.uuid4().hex+'.stdout.log')).open('x') as out,(D/('worker_'+uuid.uuid4().hex+'.stderr.log')).open('x') as err:
  p=subprocess.Popen([str(Path(os.sys.executable)),str(R/'local_control_worker.py'),'--run'],cwd=R,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.NORMAL_PRIORITY_CLASS)
 return dict(status='starting',pid=p.pid)
def job_path(jobid):
 if not isinstance(jobid,str) or not jobid or not all(c.isalnum() or c=='_' for c in jobid):raise ValueError('Invalid job')
 p=D/'jobs'/jobid/'job.json'
 if not p.is_file():raise ValueError('Unknown job')
 return p
@contextlib.contextmanager
def job_transition(jobid):
 p=job_path(jobid).parent/'transition.lock'
 try:
  with p.open('x') as f:f.write(str(os.getpid()))
 except FileExistsError:raise ValueError('Job is changing phase; refresh and retry')
 try:yield
 finally:p.unlink(missing_ok=True)
def continue_job(jobid):
 if hold().get('active'):raise ValueError('Campaign remains on hold')
 with job_transition(jobid):
  p=job_path(jobid);j=read(p)
  if j.get('status')!='paused':raise ValueError('Only a normally stopped, saved run can continue; failed runs require a new diagnostic')
  manifest=read(Path(j.get('resume_manifest','missing')))
  f=Path(manifest.get('file','missing'))
  if manifest.get('status')!='safe_saved_continuation' or manifest.get('physical_guard_failed') is not False or manifest.get('source_unchanged') is not True or not f.is_file() or e.digest(f)!=manifest.get('sha256'):raise ValueError('Saved continuation identity/checks failed')
  if manifest.get('mesh_id')!=j['spec'].get('mesh_id') or manifest.get('domain_key')!=domain_key(j['spec']):raise ValueError('Saved mesh/domain changed; new matched C01 required')
  j.update(status='queued',resume_source=manifest,message='Continuation queued from a verified save; new attempt folder, original wave clock retained',updated_at=stamp());write(p,j)
 return dict(message='Saved continuation queued. Press Start queued jobs when ready.')
def cancel(jobid):
 with job_transition(jobid):
  p=job_path(jobid);j=read(p)
  if j.get('status') not in ('queued','waiting'):raise ValueError('Only waiting jobs can be cancelled; use Stop and save for an active calculation')
  (p.parent/'CANCEL').touch(exist_ok=True);j.update(status='cancelled',updated_at=stamp());write(p,j)
def catalogue():
 return [dict(name=name,height_m=h,wavelength_m=lam,upstream_m=1.75*lam,downstream_m=2.25*lam-1.19,wall_minutes=180,action='run',length_m=4*lam,checkpoint_interval_s=.05) for name,h,lam in PRESETS]
def public_status():
 try:mi=mesh_inputs().public_status()
 except (ImportError,ValueError,KeyError) as ex:mi=dict(entries=[],selected_id=None,import_status={'status':'unavailable','reason':str(ex)})
 calm=None
 try:
  s=validate(dict(name='W01a',height_m=.5,wavelength_m=20,upstream_m=35,downstream_m=43.81,wall_minutes=180,action='run'));calm=registered_calm(s)
 except ValueError:pass
 return dict(state=read(D/'state.json'),jobs=jobs(),paused=(D/'PAUSE').exists(),worker=read(D/'worker.lock'),calm=calm,catalog=catalogue(),receipt=read(R/'local_control_macro_receipt.json'),report=str(R.parent/'local_campaign_results.html'),readiness=readiness(),mesh_inputs=mi,campaign_hold=hold(),validation=read(R/'local_recipe_validation_state.json'))
def file_choices():
 result=[]
 for j in jobs():
  for a in j.get('attempts',[]):
   p=Path(a['directory'])
   for filename,meta in [('prepared_wave.sim',read(p/'prepared_wave_audit.json')),('final.sim',read(p/'completed.json')),('C01_settled.sim',read(p/'settled_checkpoint.json'))]:
    f=p/filename
    if meta and f.is_file():result.append(dict(path=str(f),time_s=meta.get('time_s',meta.get('physical_time_s')),kind=('Diagnostic failed save' if meta.get('status')=='stability_guard' else filename),case=p.name))
   cp=read(p/'latest_checkpoint.json');f=Path(cp.get('file','missing'))
   if cp.get('completed_save') and f.is_file():result.append(dict(path=str(f),time_s=cp.get('time_s'),kind='Completed checkpoint',case=p.name))
 s=read(R/'wave_foil_run_state.json');p=Path(s.get('directory','missing'))
 for name,meta in [('C01_settled.sim',read(p/'settled_checkpoint.json')),('final.sim',read(p/'completed.json'))]:
  if meta and (p/name).is_file():result.append(dict(path=str(p/name),time_s=meta.get('time_s',meta.get('physical_time_s')),kind='Diagnostic failed save' if meta.get('status')=='stability_guard' else name,case=p.name))
 return result
def open_file(path,folder=False):
 valid={str(Path(x['path']).resolve()) for x in file_choices()}
 s=read(R/'wave_foil_run_state.json');cp=read(Path(s.get('directory','missing'))/'latest_checkpoint.json')
 if cp.get('completed_save'):valid.add(str(Path(cp.get('file','missing')).resolve()))
 p=Path(path).resolve()
 if str(p) not in valid or not p.is_file() or p.suffix.lower()!='.sim' or not p.is_relative_to(W):raise ValueError('Choose a verified completed .sim from the file list')
 if folder:subprocess.Popen(['explorer.exe','/select,',str(p)],creationflags=subprocess.CREATE_NO_WINDOW)
 else:os.startfile(str(p))
 return dict(message='Opened folder' if folder else 'Requested opening the saved simulation',path=str(p))
