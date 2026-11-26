"""Explicit local mesh-study pause/save and checkpoint resume. No import-time actions."""
from pathlib import Path
import csv,ctypes,datetime,hashlib,json,math,os,subprocess,sys,uuid
O=Path(r'C:/Users/ThinkPad/Documents/ChatGPT/ntnu science/mesh_study_20261030/gci_w01a_20261030')
R=Path(__file__).resolve().parent
D=O/'dashboard_control'
PY=Path(r'C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
def stamp():return datetime.datetime.now().astimezone().isoformat()
def read(p):
 try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return {}
def write(p,v):
 p=Path(p);p.parent.mkdir(exist_ok=True,parents=True);tmp=p.with_name(p.name+'.'+uuid.uuid4().hex+'.tmp')
 tmp.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf8');os.replace(tmp,p)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
 return h.hexdigest()
def alive(pid):
 if type(pid)!=int or pid<=0:return False
 k=ctypes.windll.kernel32;k.OpenProcess.restype=ctypes.c_void_p;k.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)];k.CloseHandle.argtypes=[ctypes.c_void_p]
 h=k.OpenProcess(0x1000,False,pid)
 if not h:return False
 try:
  c=ctypes.c_ulong();return bool(k.GetExitCodeProcess(h,ctypes.byref(c))) and c.value==259
 finally:k.CloseHandle(h)
def case_path(value):
 p=Path(value).resolve();base=(O/'force_stabilization_20261029').resolve()
 if p.parent!=base or not p.is_dir():raise ValueError('Not a registered mesh-study attempt')
 return p
def generation(s):return str(s.get('pid'))+'|'+str(s.get('job'))+'|'+str(s.get('directory'))
def active_state():
 s=read(O/'gpu_study_state.json');lock=read(O/'gpu_live_study.lock')
 if s.get('status')=='GPU_job_running' and alive(s.get('pid')) and alive(s.get('star_pid')) and lock.get('pid')==s.get('pid'):
  p=case_path(s['directory'])
  if read(p/'process.json').get('pid')==s['star_pid']:return s,p
 return None,None
def safe_saved(p,verify_hash=False):
 done=read(p/'completed.json');ex=read(p/'exit.json');export=read(p/'EXPORT_OK.json');source=read(p/'source_identity.json')
 if done.get('status') not in ('stopped_by_marker','target_reached','stabilized'):raise ValueError('No normal saved stop; failed fields cannot resume')
 if ex.get('returncode')!=0 or ex.get('source_unchanged') is not True:raise ValueError('Solver exit/source check has not passed')
 t=done.get('time_s')
 if not isinstance(t,(float,int)) or not math.isfinite(t) or t<=0 or abs(export.get('time_s',-1)-t)>1e-9:raise ValueError('Saved time/export mismatch')
 if not (p/'final.sim').is_file() or (p/'final.sim').stat().st_size==0:raise ValueError('Calculated final.sim is missing')
 if verify_hash and (not source.get('path') or sha(source['path'])!=source.get('sha256')):raise ValueError('Original source changed')
 return done
def snapshot():
 s,p=active_state();q=read(D/'pause.json');launch=read(D/'launch.json')
 pending=alive(launch.get('pid'));waiting=bool(q and q.get('state')=='pause_requested')
 value=dict(status='running' if s else 'inactive',can_pause=bool(s and not waiting),can_resume=False,generation=generation(s) if s else '',job=s.get('job') if s else None,message='Mesh study is running.' if s else 'No active mesh-study solve.',scope='Mesh campaign M10-M12 only. Wave campaign and HF session are separate.')
 if waiting:
  value.update(status='saving' if s or pending else 'checking_save',can_pause=False,message='Pause requested: wait for final.sim and solver exit before disconnecting power.')
  if not alive(q.get('controller_pid')) and not alive(q.get('star_pid')) and not pending:
   try:
    saved=case_path(q['directory']);done=safe_saved(saved)
    owned=(O/'STOP').is_file() and (O/'STOP').read_text()==q['id']
    if not owned:raise ValueError('The pause marker changed; inspect before resuming')
    value.update(status='paused',can_resume=True,generation=q['id'],job=q['job'],time_s=done['time_s'],file=str(saved/'final.sim'),message='Paused and saved at '+format(done['time_s'],'.4f')+' s. Resume continues this mesh campaign from the saved fields.')
   except (ValueError,OSError) as ex:value.update(status='needs_review',message=str(ex))
 if pending and not s and not waiting:value.update(status='starting',can_pause=False,message='Preparing verified mesh continuation; no duplicate launch is allowed.')
 return value
def pause(data):
 s,p=active_state()
 if set(data)!={'generation'} or not s or data['generation']!=generation(s):raise ValueError('The active mesh job changed. Refresh first.')
 if (O/'STOP').exists():raise ValueError('A study stop is already present; inspect its status')
 q=dict(id=uuid.uuid4().hex,state='pause_requested',requested_at=stamp(),directory=str(p),job=s['job'],controller_pid=s['pid'],star_pid=s['star_pid'])
 write(D/'pause.json',q)
 with (O/'STOP').open('x') as f:f.write(q['id'])
 (p/'STOP').touch()
 write(p/'dashboard_pause_request.json',q)
 return dict(message='Pause requested. Saving at a complete step; keep power connected until Paused and saved appears.')
def resume(data):
 st=snapshot();q=read(D/'pause.json')
 if set(data)!={'generation'} or not st['can_resume'] or data['generation']!=st['generation']:raise ValueError('No verified paused mesh run is ready, or selection changed')
 for p in [O/'gpu_live_study.lock',R/'queue.lock',R/'STOP_ALL']:
  if p.exists():raise ValueError('Another controller or stop lock is present; no duplicate start')
 req=D/('resume_'+uuid.uuid4().hex+'.json')
 write(req,dict(requested_at=stamp(),pause_id=q['id'],pause=q,explicit_resume=True))
 with req.with_suffix('.stdout.log').open('x') as out,req.with_suffix('.stderr.log').open('x') as err:
  p=subprocess.Popen([str(PY),str(Path(__file__).resolve()),'--resume',str(req)],cwd=R,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
 write(D/'launch.json',dict(pid=p.pid,request=str(req),started_at=stamp()))
 return dict(message='Verified continuation requested; saved attempts and force history are retained.',pid=p.pid)
def combined_history(paths,output,dt,end):
 rows=[];header=None;seen={}
 for p in paths:
  with Path(p).open(encoding='utf-8-sig',newline='') as f:
   rd=csv.DictReader(f);header=header or rd.fieldnames
   for row in rd:
    t=float(row['physical_time_s']);key=round(t,10)
    if key in seen:raise ValueError('Duplicate time in resume history')
    if abs(float(row['dt_s'])-dt)>1e-10 or (rows and abs(t-float(rows[-1]['physical_time_s'])-dt)>1e-8):raise ValueError('Resume history is not contiguous at the same timestep')
    if not all(math.isfinite(float(row[k])) for k in ['CD','CL_total','pressure_drag_N','viscous_drag_N']):raise ValueError('Nonfinite resume history')
    seen[key]=True;rows.append(row)
 if not rows or abs(float(rows[-1]['physical_time_s'])-end)>1e-8:raise ValueError('History does not end at saved checkpoint')
 with Path(output).open('x',encoding='utf8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=header,extrasaction='ignore');w.writeheader();w.writerows(rows)
 return rows
def replay_job(g,original_job,name,source,env):
 """Replay completed stages; create a unique continuation for an explicitly saved stop."""
 reg=D/'jobs'/(name+'.json');record=read(reg);base=g.BASE/name
 attempts=[case_path(p) for p in record.get('attempts',[])]
 if not attempts and base.exists():attempts=[case_path(base)]
 src=Path(source);start=float(env['NTNU_STAB_START']);target=float(env['NTNU_STAB_TARGET'])
 for p in attempts:
  identity=read(p/'source_identity.json');setup=read(p/'setup.json');done=safe_saved(p,True)
  if identity.get('sha256')!=sha(src):raise ValueError('Saved continuation lineage differs')
  for k,v in [('start_time_s',start),('target_time_s',target),('dt_s',float(env['NTNU_STAB_DT'])),('inner_iterations',int(env['NTNU_STAB_INNER'])),('cells',int(env['NTNU_STAB_CELLS']))]:
   if abs(float(setup.get(k,-999))-v)>1e-8:raise ValueError('Saved settings differ: '+k)
  if done['status'] in ('target_reached','stabilized'):
   return p
  src=p/'final.sim';start=done['time_s']
 newname=name+'_resume_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]
 cfg=dict(env,NTNU_STAB_START=str(start))
 if attempts:
  histories=[]
  inherited=attempts[0]/'prior_history.csv'
  if inherited.is_file():histories.append(inherited)
  histories.extend(p/'history.csv' for p in attempts)
  hist=D/('prior_'+uuid.uuid4().hex+'.csv');D.mkdir(exist_ok=True)
  combined_history(histories,hist,float(env['NTNU_STAB_DT']),start)
  cfg['NTNU_STAB_PRIOR_HISTORY']=str(hist)
 dest=g.BASE/newname
 write(reg,dict(attempts=[str(p) for p in attempts]+[str(dest)],logical_job=name,updated_at=stamp()))
 # Register read-only lineage separately; original raw histories are never overwritten.
 write(D/'lineages'/(newname+'.json'),dict(histories=[str(p/'history.csv') for p in attempts]+[str(dest/'history.csv')]))
 return original_job(newname,src,cfg)
def expand_histories(paths):
 result=[]
 for p in paths:
  p=Path(p);lineage=read(D/'lineages'/(p.parent.name+'.json')).get('histories',[str(p)])
  for value in lineage:
   q=Path(value)
   if q not in result:result.append(q)
 return result
def run_resume(request):
 req=read(request);q=req.get('pause',{});token=uuid.uuid4().hex;owned=[];started=False
 if Path(request).parent.resolve()!=D.resolve() or not req.get('explicit_resume'):raise ValueError('Explicit local resume request required')
 sys.path.insert(0,str(O));import gpu_calm_study_live as g
 try:
  if alive(q.get('controller_pid')) or alive(q.get('star_pid')):raise ValueError('Previous save is still active')
  if (R/'STOP_ALL').exists():raise ValueError('Campaign emergency stop present')
  for p in [O/'gpu_live_study.lock',R/'queue.lock']:
   with p.open('x') as f:json.dump(dict(pid=os.getpid(),token=token,purpose='Explicit mesh study continuation'),f)
   owned.append(p)
  source=case_path(q['directory']);done=safe_saved(source,True)
  stop=O/'STOP'
  if not stop.is_file() or stop.read_text()!=q['id']:raise ValueError('Pause marker changed')
  # Pin code identities to the installed, tested controller revision.
  checks=read(R/'mesh_control_receipt.json')
  if checks.get('status')!='passed':raise ValueError('Control tests have not passed')
  for file,digest in checks['source_sha256'].items():
   if sha(file)!=digest:raise ValueError('Control source changed since tests: '+Path(file).name)
  write(D/'resume_sources'/(token+'.json'),dict(path=str(source/'final.sim'),sha256=sha(source/'final.sim'),time_s=done['time_s'],source_unchanged=True))
  q.update(state='resumed',resumed_at=stamp());write(D/'pause.json',q)
  stop.rename(D/('pause_marker_'+q['id']+'.txt'))
  original=g.job;g.job=lambda name,src,env:replay_job(g,original,name,src,env)
  original_load=g.a.load_history;g.a.load_history=lambda paths:original_load(expand_histories(paths))
  started=True;g.main()
  write(D/'last_resume.json',dict(status='completed',at=stamp(),request=str(request)))
 except BaseException as ex:
  # A user-requested save remains resumable; a scientific guard failure never does.
  pause_now=read(D/'pause.json')
  status='pause_save_finished' if pause_now.get('state')=='pause_requested' else 'needs_review'
  write(D/'last_resume.json',dict(status=status,error=g.runner.redact(str(ex)),at=stamp(),request=str(request)))
  if started:g.state(status,error=g.runner.redact(str(ex)))
  raise
 finally:
  for p in reversed(owned):
   if read(p).get('token')==token:p.unlink()
if __name__=='__main__':
 if len(sys.argv)!=3 or sys.argv[1]!='--resume':raise SystemExit('Use explicit local dashboard controls')
 run_resume(Path(sys.argv[2]))
