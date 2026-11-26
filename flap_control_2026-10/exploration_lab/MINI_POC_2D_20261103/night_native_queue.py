from pathlib import Path
import sys,os,json,time,csv,math,datetime,subprocess,ctypes,shutil,statistics,hashlib,re
import day_chain as M
import night_review as V
R=M.R;N=R/'mini_vof_20261103/NIGHT_20261103';N.mkdir(exist_ok=True);END=datetime.datetime.fromisoformat('2026-11-04T06:50:00+01:00').timestamp();STOP=N/'STOP.json';LOCK=N/'NIGHT_CONTROLLER.lock';Q=N/'QUEUE_STATE.json';STATE=N/'NIGHT_STATUS.json';JOURNAL=N/'DECISIONS.jsonl';T=V.T;M.D=N;M.STATE=STATE;M.STOP=STOP;M.deadline=END;M.authorization_scope='Explicit USER_NIGHT_AUTHORIZATION N1->N2->N3 conditional PASS, one E CPU, no GPU, no active flap; stop before07:00 Oslo';SOURCE=R/'mini_vof_20261103/Q2D_NATIVE_A005_REMAINING49/VOF_checkpoint.sim'
class Hold(Exception):pass
class Mem(ctypes.Structure):_fields_=[('len',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(x,ctypes.c_ulonglong) for x in ['phys','avail','page','apage','virt','avirt','ext']]
def memory():
 m=Mem();m.len=ctypes.sizeof(m);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return m.avail

def event(kind,**kw):
 x=dict(at=datetime.datetime.now().astimezone().isoformat(),kind=kind,**kw)
 with JOURNAL.open('a',encoding='utf8') as f:f.write(json.dumps(x,ensure_ascii=False)+'\n')
 return x

def process_snapshot(all_processes=False):
 ps="Get-CimInstance Win32_Process | "+("" if all_processes else "Where-Object {$_.Name -in @('starccm+.exe','star-ccm+.exe')} | ")+"ForEach-Object {[PSCustomObject]@{pid=$_.ProcessId;ppid=$_.ParentProcessId;name=$_.Name;exe=$_.ExecutablePath;birth=$_.CreationDate.ToFileTimeUtc();affinity=if($_.Name -in @('starccm+.exe','star-ccm+.exe')){(Get-Process -Id $_.ProcessId).ProcessorAffinity.ToInt64()}else{0}}} | ConvertTo-Json -Compress"
 p=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,check=True);a=json.loads(p.stdout.strip() or '[]');return [] if a is None else a if isinstance(a,list) else [a]

def foreign_blockers(procs,owned):
 f=N/'PROTECTED_GPU_COEXISTENCE.json';allowed=json.loads(f.read_text())['processes'] if f.exists() else []
 out=[]
 for x in procs:
  if x.get('name') not in ['starccm+.exe','star-ccm+.exe'] or x['pid'] in owned:continue
  match=next((a for a in allowed if a['pid']==x['pid'] and a.get('birth')==x.get('birth') and a.get('exe')==x.get('exe')),None)
  if match is None or (x.get('affinity',0)&16):out.append(x)
 return out

def dashboard(state,stage,**kw):
 out=Path(kw.get('output',N));native={};latest={}
 try:native=json.loads((out/'native_status.json').read_text())
 except:pass
 try:
  with (out/'history.csv').open() as f:
   header=f.readline().strip().split(',');f.seek(0,2);size=f.tell();f.seek(max(0,size-8000));lines=f.read().splitlines();row=next(x for x in reversed(lines) if len(x.split(','))==len(header));latest=dict(zip(header,row.split(',')))
 except:pass
 mem=memory()
 if mem<4*1024**3 and not STOP.exists():M.atom(STOP,dict(reason='AVAILABLE_RAM_BELOW4GiB',at=time.time()))
 if time.time()>END and not STOP.exists():M.atom(STOP,dict(reason='END_NIGHT_WINDOW',at=time.time()))
 # Do not alter any newly-started independent solver. Pause ours if overlap was not measured.
 try:
  procs=process_snapshot(True);root=kw.get('PID');ids={root} if root else set()
  log=out/'MiniVofNight.log'
  if log.exists():ids|={int(x) for x in re.findall(r'Process rank \d+ \S+ (\d+)',log.read_text(encoding='utf8',errors='ignore'))}
  for _ in range(64):
   new=ids|{x['pid'] for x in procs if x['ppid'] in ids}
   if new==ids:break
   ids=new
  others=foreign_blockers(procs,ids)
  if others and state in ['STARTING','RUNNING'] and not STOP.exists():M.atom(STOP,dict(reason='INDEPENDENT_STAR_STARTED_NO_UNLOADED_BASELINE',processes=others,at=time.time()))
 except Exception as e:
  if not STOP.exists():M.atom(STOP,dict(reason='RESOURCE_AUDIT_FAILED',error=str(e)))
 solver=native.get('solver_state','STOPPED');op=native.get('operation','STARTING' if state=='STARTING' else state)
 M.atom(STATE,dict(at=datetime.datetime.now().astimezone().isoformat(),controller_pid=os.getpid(),stage=stage,solver_state=solver,operation=op,latest=latest,native=native,CPU=1,E_logical_cpu=4,GPU=False,available_RAM_GiB=mem/1024**3,night_approved=True,training_approved=False,stop_requested=STOP.exists(),**kw))
M.status=dashboard

def latest_cp(out):
 x=json.loads((out/'LATEST_CHECKPOINT.json').read_text());p=Path(x['path']);assert p.exists() and p.stat().st_size==x['bytes'];return p,float(x['time_s'])

def properties(out,job):
 M.atom(out/'job.json',job)
 with (out/'job.properties').open('w',encoding='utf8') as f:
  for k,v in job.items():
   if isinstance(v,bool):v=str(v).lower()
   f.write(k+'='+str(v).replace('\\','/')+'\n')

def recover_client(out):
 out=Path(out);text=(out/'MiniVofNight.log').read_text(encoding='utf8',errors='ignore')
 if 'Connection reset' not in text:return False
 dest=out/'client_recovery';dest.mkdir(exist_ok=True)
 if (dest/'RECOVERY_ATTEMPT.json').exists():return False
 ranks={int(x) for x in re.findall(r'Process rank \d+ \S+ (\d+)',text)};m=re.search(r'Server::start -host ([^: ]+):(\d+)',text)
 live=[x for x in process_snapshot() if x['pid'] in ranks and '21.04.009' in (x.get('exe') or '')]
 if not live or not m:return False
 port=int(m.group(2));ps="@(Get-NetTCPConnection -LocalPort "+str(port)+" -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique) | ConvertTo-Json -Compress";z=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);owners=json.loads(z.stdout.strip() or'[]');owners=owners if isinstance(owners,list) else [owners]
 if not set(owners)&ranks:return False
 M.atom(dest/'RECOVERY_ATTEMPT.json',dict(at=time.time(),owned_ranks=sorted(ranks),port=port,procedure='Attach to same server, stop, save diagnostic interrupted-inner checkpoint, normal Close; no force/no new solver'))
 with (dest/'attach.log').open('w') as f:
  try:subprocess.run([M.EXE,'-host',m.group(1),'-port',str(port),'-batch',str(R/'NightRecoverOwnedServer.java')],env={**os.environ,**M.LIC,'MINI_CASE_DIR':str(dest)},stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=90)
  except subprocess.TimeoutExpired:event('RECOVERY_ATTACH_TIMEOUT_PRESERVE_SERVER',out=str(out));return False
 ok=(dest/'RECOVERY.json').exists();event('CLIENT_RECOVERY',out=str(out),saved=ok)
 return ok

def call(stage,source,t0,steps,*,amp=.05,oldamp=None,ramp=0,inner=20,dt=.001,foil=False,fresh=False,damping=8,pressure_urf=.5):
 if STOP.exists() or time.time()>=END:raise Hold('Stop marker/deadline')
 out=N/stage
 if (out/'SOLVE_STATUS.json').exists():event('REUSE_FINISHED_JOB',stage=stage);return out
 if out.exists():raise Hold('Incomplete prior job exists; do not silently replay '+stage)
 if foreign_blockers(process_snapshot(),set()):raise Hold('Unverified independent STAR active; no parallel launch')
 out.mkdir();wall_budget=max(1,END-time.time()-240)
 job=dict(authorization='N1_N2_N3_USER_20261103',stage=stage,fresh=fresh,foil=foil,expected_cells=44442 if foil else 41280,expected_time=t0,dt=dt,inner=inner,amplitude=amp,old_amplitude=amp if oldamp is None else oldamp,ramp_s=ramp,steps=int(steps),forcing_length=4,damping_length=damping,pressure_tol=.01,pressure_urf=pressure_urf,wall_budget_s=wall_budget,deadline_ms=int(END*1000),stop_path=STOP.as_posix())
 if fresh:job['mesh']=(N/'FOIL_MESH/mesh_3d.msh').as_posix()
 properties(out,job);event('START',stage=stage,input=str(source) if source else None,job=job);M.atom(Q,dict(stage=stage,operation='STARTING',source=str(source) if source else None,source_time=t0,next='Only after stage PASS',night_approved=True))
 try:M.launch(stage,'MiniVofNight.java',out,source,build=fresh,max_runtime_s=wall_budget+180)
 except Exception as exc:
  saved=recover_client(out);raise Hold('Native job/client failure; bounded recovery_saved='+str(saved)+'; '+str(exc))
 state=json.loads((out/'SOLVE_STATUS.json').read_text());cp,t=latest_cp(out);manifest=[dict(path=str(p),bytes=p.stat().st_size,sha256=M.sha(p)) for p in out.glob('*.sim')];M.atom(out/'CHECKPOINT_MANIFEST.json',manifest);event('NATIVE_FINISHED',stage=stage,status=state,checkpoint=str(cp));return out

def native_status(out):return json.loads((out/'SOLVE_STATUS.json').read_text())['status']
def acceptable_partial(out):return native_status(out) in ['NUMERICAL_END_PASS','HOLD_RESIDUAL_WINDOW']
def repair(reason,stage,change):
 p=N/'REPAIRS.json';r=json.loads(p.read_text()) if p.exists() else {};n=r.get(stage,0)
 if n>=2:raise Hold(stage+': maximum two targeted repairs reached')
 r[stage]=n+1;M.atom(p,r);event('TARGETED_REPAIR',stage=stage,attempt=n+1,reason=reason,change=change);return n+1

def passed(stage,out,review):
 assert review.get('pass') or review.get('pass_calm');cp,t=latest_cp(out);rec=dict(stage=stage,checkpoint=str(cp),sha256=M.sha(cp),physical_time=t,review=review,approved_scope='PoC only; not quantitative validation or training authorization');M.atom(N/(stage+'_PASS.json'),rec);event('PASS',stage=stage,checkpoint=str(cp));return cp,t

def plot_partial(out):
 try:
  n=V.numerical(out);h=V.read(out/'history.csv');g=V.read(out/'gauges.csv') if (out/'gauges.csv').exists() else [];V.plots(out,n,h,g,float(h[0]['time_s']) if h else 0)
 except Exception as e:event('PARTIAL_REPORT_ERROR',error=str(e),out=str(out))

def remaining_fits(steps,dt,cost,reserve=300):return time.time()+steps*cost*1.2+reserve<END

def main():
 assert json.loads((N/'AUTHORIZATION.json').read_text())['approved'];assert M.sha(SOURCE)=='ef36d8738b8c2efaa882c5da7953aef8f55477303bceb76076ceb91847cdf85c';assert not (R/'STOP_MINI.json').exists(),'Existing Mini safety stop'
 # The supported launcher/affinity/license path is reused. No task scheduler or Windows autostart.
 with LOCK.open('x') as f:json.dump(dict(pid=os.getpid(),created=time.time()),f)
 try:
  if foreign_blockers(process_snapshot(),set()):raise Hold('Unverified STAR active; no duplicate controller/solver')
  if (N/'N3_PASS.json').exists():event('ALREADY_COMPLETE_NO_REPLAY');return
  if not (N/'PROTECTED_GPU_COEXISTENCE.json').exists():shutil.copy2(R/'mini_vof_20261103/W04_RESOURCE_REVIEW.json',N/'W04_RESOURCE_REVIEW.json')
  event('START_NIGHT',authorization=str(N/'USER_NIGHT_AUTHORIZATION.txt'))
  cp=SOURCE;t=.05;inner=20;damping=8
  if (N/'N1_PASS.json').exists():j=json.loads((N/'N1_PASS.json').read_text());cp=Path(j['checkpoint']);t=j['physical_time'];assert M.sha(cp)==j['sha256'];inner=int(json.loads((cp.parent/'job.json').read_text())['inner']);damping=float(json.loads((cp.parent/'job.json').read_text()).get('damping_length',8))
  else:
   # First targeted correction: tighter pressure solve and faster pressure coupling, unchanged physical/PASS limits.
   rfile=N/'REPAIRS.json'
   if not rfile.exists():repair('continuity .0776 in accepted 50step smoke','N1',{'pressure_AMG':'.1 -> .01','pressure_URF':'.2 -> .5','inner':20})
   recovery_state=N/'RESUME_AFTER_CLIENT_RECOVERY.json'
   if recovery_state.exists():
    rec=json.loads(recovery_state.read_text());inner=40;cal=call('N1_CALIBRATION_2',Path(rec['source']),rec['source_time'],40,inner=inner);nr=V.numerical(cal);plot_partial(cal)
    if not nr['pass']:raise Hold('Second targeted pressure correction failed: '+str(nr['reasons']))
   else:
    cal=call('N1_CALIBRATION_1',cp,t,40,inner=20);nr=V.numerical(cal);plot_partial(cal)
    if not nr['pass']:
     if not acceptable_partial(cal):raise Hold('N1 calibration physical/setup HOLD: '+native_status(cal))
     repair('continuity still above.01; no threshold relaxation','N1',{'inner':'20 -> 40','pressure_URF':.5});cp,t=latest_cp(cal);inner=40;cal=call('N1_CALIBRATION_2',cp,t,40,inner=inner);nr=V.numerical(cal);plot_partial(cal)
     if not nr['pass']:raise Hold('N1 second targeted correction did not pass: '+str(nr['reasons']))
   cp,t=latest_cp(cal);cost=nr['mean_s_step'];steps=math.ceil(5*T/.001)+2
   if not remaining_fits(steps,.001,cost):raise Hold('N1 complete retained periods do not fit window')
   out=call('N1_PROPAGATION',cp,t,steps,inner=inner);review=V.wave_review(out,.05,t+2*T)
   if not review['pass']:
    reason='; '.join(review['reasons']);nrepair=json.loads((N/'REPAIRS.json').read_text()).get('N1',0)
    if nrepair<2 and acceptable_partial(out):
     if all(('Reflection' in x or 'decomposition' in x) for x in review['reasons']):damping=10;change={'damping_length':'8 -> 10m; probe16m remains outside zone'}
     elif all(('Residual' in x or 'HOLD_RESIDUAL' in x) for x in review['reasons']):inner=40;change={'inner':'20 -> 40'}
     else:raise Hold('N1 scientific HOLD: '+reason)
     repair(reason,'N1',change);cp,t=latest_cp(out);out=call('N1_PROPAGATION_REPAIR2',cp,t,math.ceil(4*T/.001)+2,inner=inner,damping=damping);review=V.wave_review(out,.05,t+T)
    if not review['pass']:raise Hold('N1 not PASS: '+str(review['reasons']))
   cp,t=passed('N1',out,review)
  # No N2 launch without persisted, checksummed N1 PASS.
  assert (N/'N1_PASS.json').exists()
  if (N/'N2_PASS.json').exists():j=json.loads((N/'N2_PASS.json').read_text());cp=Path(j['checkpoint']);t=j['physical_time'];assert M.sha(cp)==j['sha256']
  else:
   startup=T+24/(18+.5*math.sqrt(9.81/V.K))+.5*T;steps=math.ceil((startup+3*T)/.001)+2
   prior=V.numerical(cp.parent);cost=prior['mean_s_step']
   if not remaining_fits(steps,.001,cost):raise Hold('N2 complete propagation assessment will not fit remaining window')
   out=call('N2_A025',cp,t,steps,amp=.25,oldamp=.05,ramp=T,inner=inner,damping=damping);review=V.wave_review(out,.25,t+startup)
   if not review['pass']:raise Hold('N2 not PASS; no foil: '+str(review['reasons']))
   cp,t=passed('N2',out,review)
  assert (N/'N2_PASS.json').exists()
  # Same sealed mesh and physics for calm baseline and wave: isolate incident-wave force changes.
  mesh=N/'FOIL_MESH/mesh_3d.msh'
  if not mesh.exists():raise Hold('Corrected foil extrusion is not ready')
  dt=.001;out=call('N3_CALM_PILOT',None,0,500,amp=0,inner=inner,foil=True,fresh=True,damping=damping);st=native_status(out)
  if st=='HOLD_CFL':
   h=V.read(out/'history.csv');maxc=max(float(x['max_CFL']) for x in h);dt=min(.001,.001*25/maxc*.8);repair('CFL on thin foil cells','N3',{'dt':dt,'same_mesh':True});startcp=out/'START.sim'
   if dt<.00005:raise Hold('Required foil timestep too small for night window; preserve diagnosis')
   out=call('N3_CALM_CFL_REPAIR',startcp,0,math.ceil(.5/dt),amp=0,inner=inner,dt=dt,foil=True,damping=damping)
  elif st not in ['NUMERICAL_END_PASS','HOLD_RESIDUAL_WINDOW']:raise Hold('N3 physical pilot failed: '+st)
  cr=V.calm_review(out);cost=cr['mean_s_step']
  for ix in [1,2]:
   if cr.get('pass_calm'):break
   if not acceptable_partial(out):raise Hold('N3 calm not physically acceptable')
   if any('Residual' in x or 'HOLD_RESIDUAL' in x for x in cr['reasons']):
    if inner>=40:raise Hold('N3 residual gate fails at40inner')
    repair('N3 inner convergence','N3',{'inner':40});inner=40
   cp,t=latest_cp(out)
   if t>=1.5:raise Hold('Calm force settling cap1.5s reached')
   out=call('N3_CALM_SETTLE_'+str(ix),cp,t,math.ceil(.5/dt),amp=0,inner=inner,dt=dt,foil=True,damping=damping);cr=V.calm_review(out)
  if not cr.get('pass_calm'):raise Hold('N3 calm forces not settled; no wave foil run')
  cp,t=passed('N3_CALM',out,cr);cost=cr['mean_s_step'];startup=2*T+12.952/(18+.5*math.sqrt(9.81/V.K))+.5*T;steps=math.ceil((startup+3*T)/dt)+2
  if not remaining_fits(steps,dt,cost):raise Hold('N3 full retained cycles cannot fit before07:00; calm result saved')
  out=call('N3_WAVE_FIXED025',cp,t,steps,amp=.25,oldamp=0,ramp=2*T,inner=inner,dt=dt,foil=True,damping=damping);wr=V.wave_review(out,.25,t+startup,foil=True)
  if not wr['pass'] and acceptable_partial(out) and all('Force cycle repeatability' in x for x in wr['reasons']):
   cp,t=latest_cp(out)
   if remaining_fits(math.ceil(3*T/dt)+2,dt,wr['numerical']['mean_s_step']):out=call('N3_WAVE_REPEATABILITY_EXTENSION',cp,t,math.ceil(3*T/dt)+2,amp=.25,inner=inner,dt=dt,foil=True,damping=damping);wr=V.wave_review(out,.25,t,foil=True)
  if not wr['pass']:raise Hold('N3 wave force trajectory not accepted: '+str(wr['reasons']))
  passed('N3',out,wr);M.atom(Q,dict(stage='COMPLETE',solver_state='STOPPED',operation='COMPLETE',N1='PASS',N2='PASS',N3='PASS_POC',training_approved=False));event('NIGHT_COMPLETE')
 except Exception as e:
  event('HOLD',reason=str(e));M.atom(Q,dict(stage='HOLD',solver_state='STOPPED' if M.workers()==0 else 'HOLD',operation='HOLD',reason=str(e),no_next_stage=True,training_approved=False))
  if not isinstance(e,Hold):raise
 finally:
  morning();LOCK.unlink(missing_ok=True)

def morning():
 stages={}
 for s in ['N1','N2','N3_CALM','N3']:
  p=N/(s+'_PASS.json');stages[s]=json.loads(p.read_text()) if p.exists() else {'status':'NOT_PASS'}
 M.atom(N/'MORNING_REPORT.json',dict(at=datetime.datetime.now().astimezone().isoformat(),queue=json.loads(Q.read_text()) if Q.exists() else {},stages=stages,training_approved=False,no_active_flap=True,decision_history=str(JOURNAL)))
 lines=['NTNU MINI-VOF NIGHT REPORT',datetime.datetime.now().astimezone().isoformat()]
 for s,x in stages.items():
  lines.append(s+': '+('PASS_POC' if 'checkpoint' in x else 'NOT_PASS'))
  if 'checkpoint'in x:lines.append('  checkpoint: '+x['checkpoint']);lines.append('  details: '+str(Path(x['checkpoint']).parent))
 if Q.exists():lines.append('Queue: '+Q.read_text())
 lines+=['No WAVE/ACTIVE, DRL or surrogate training executed.','PASS means bounded PoC criteria; no full mesh/energetic validation claim.'];(N/'MORNING_REPORT.txt').write_text('\n'.join(lines),encoding='utf8')
 if not (N/'NIGHT_CONTROLLER.lock').exists():return
 M.atom(STATE,dict(at=datetime.datetime.now().astimezone().isoformat(),solver_state='STOPPED' if M.workers()==0 else 'HOLD',operation='COMPLETE' if (N/'N3_PASS.json').exists() else 'HOLD',queue=json.loads(Q.read_text()) if Q.exists() else {},report=str(N/'MORNING_REPORT.txt'),night_approved=True))

if __name__=='__main__':main()
