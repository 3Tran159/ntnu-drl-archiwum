"""Read-only machine and campaign telemetry. Never starts/stops a solver."""
import csv,ctypes,datetime,json,math,os,re,shutil,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parent
W=Path('E:/ntnu/quasi2d_waves_20261029')
def read(p,default=None):
 try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return default if default is not None else {}
def write(p,v):
 t=p.with_name(p.name+'.'+str(os.getpid())+'.tmp');t.write_text(json.dumps(v,indent=2),encoding='utf8');t.replace(p)
def finite(v):
 try:return float(v) if math.isfinite(float(v)) else None
 except (ValueError,TypeError):return None
def history(p):
 try:
  with p.open(encoding='utf-8-sig',newline='') as f:return [{k:finite(v) for k,v in row.items()} for row in csv.DictReader(f)]
 except OSError:return []
class Mem(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(x,ctypes.c_ulonglong) for x in ('total','avail','page','availpage','virt','availvirt','extended')]
def collect():
 now=datetime.datetime.now().astimezone();stamp=now.isoformat(timespec='seconds');out={'sampled_at':stamp,'sample_unix':time.time(),'scope':'Whole computer; campaign activity identified separately','errors':[]}
 m=Mem();m.length=ctypes.sizeof(m)
 if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):out['memory']={'used_gb':(m.total-m.avail)/2**30,'total_gb':m.total/2**30,'free_gb':m.avail/2**30,'percent':m.load}
 idle=ctypes.c_ulonglong();kernel=ctypes.c_ulonglong();user=ctypes.c_ulonglong()
 ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle),ctypes.byref(kernel),ctypes.byref(user))
 prev=read(R/'computer_cpu_sample.json');new={'idle':idle.value,'total':kernel.value+user.value}
 delta=new['total']-prev.get('total',new['total'])
 out['cpu_percent']=100*(1-(new['idle']-prev['idle'])/delta) if delta>0 else None
 write(R/'computer_cpu_sample.json',new)
 out['disks']={}
 for name in ('E','F'):
  try:
   d=shutil.disk_usage(name+':/');out['disks'][name]={'free_gb':d.free/2**30,'total_gb':d.total/2**30}
  except OSError:out['disks'][name]={'free_gb':None}
 try:
  q=subprocess.run(['nvidia-smi','--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5,creationflags=subprocess.CREATE_NO_WINDOW)
  fields=next(csv.reader(q.stdout.splitlines()));out['gpu']={'name':fields[0].strip(),'percent':finite(fields[1]),'used_mb':finite(fields[2]),'total_mb':finite(fields[3]),'temperature_c':finite(fields[4])}
 except (OSError,ValueError,StopIteration,IndexError,subprocess.TimeoutExpired):out['gpu']=None
 # Only allowlisted metadata is emitted; command lines and service credentials never leave this query.
 ps=r"""Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^(pythonw?|star-ccm\+|starccm\+|java)\.exe$'} | ForEach-Object {$s='';if($_.CommandLine -match '([A-Za-z0-9_\-]+\.py)(?=[\s\x22]|$)'){$s=$matches[1]};[PSCustomObject]@{pid=$_.ProcessId;name=$_.Name;script=$s;campaign=[bool]($_.CommandLine -match 'quasi2d_waves_20261029|force_stabilization_20261029');created=$_.CreationDate.ToString('o')}} | ConvertTo-Json -Compress"""
 try:
  p=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,timeout=8,creationflags=subprocess.CREATE_NO_WINDOW)
  if p.returncode:raise ValueError('Process query failed')
  processes=json.loads(p.stdout or '[]');processes=[processes] if isinstance(processes,dict) else processes
 except (ValueError,OSError,subprocess.TimeoutExpired):processes=[];out['errors'].append('Process observation unavailable')
 out['star_processes']=sum('star' in p['name'].lower() for p in processes)
 bypid={p['pid']:p for p in processes}
 out['stop_requested']=(R/'STOP_ALL').exists()
 states=[]
 for path in R.glob('*state*.json'):
  s=read(path)
  if not isinstance(s,dict):continue
  pid=s.get('controller_pid',s.get('pid'))
  proc=bypid.get(pid,{})
  if pid and proc.get('script','').startswith(('run_','adopt_','resume_')) and path.stat().st_mtime >= datetime.datetime.fromisoformat(proc['created']).timestamp()-5:
   states.append((path,s))
 out['locks']=[]
 for path in (R/'queue.lock',W/'preparation.lock'):
  if path.exists():out['locks'].append({'name':path.name,'modified_at':datetime.datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(),'owner':read(path)})
 ownstar=any(p.get('campaign') and 'star' in p['name'].lower() for p in processes)
 out['campaign_solver_observed']=ownstar
 out['other_star_processes']=sum('star' in p['name'].lower() and not p.get('campaign') for p in processes)
 if states:
  path,s=max(states,key=lambda item:(item[1].get('gpu') is True,item[0].stat().st_mtime));out['state_file']=path.name
  seen=set();concurrent=[]
  for sp,st in states:
   pid=st.get('controller_pid',st.get('pid'))
   if pid==s.get('controller_pid',s.get('pid')) or pid in seen:continue
   seen.add(pid);concurrent.append({'case':st.get('case',st.get('active')),'stage':st.get('status'),'gpu':st.get('gpu'),'controller_pid':pid})
  out['concurrent_activity']=concurrent
  case=s.get('case',s.get('active',''));case=case.get('id','') if isinstance(case,dict) else case
  folder=Path(s.get('directory') or s.get('folder') or str(R/str(case)))
  if not folder.exists() and case:
   choices=[W/str(case)]+list(R.glob('*/'+str(case)))
   folder=next((p for p in choices if p.is_dir()),folder)
  prog=read(folder/'progress.json');rows=history(folder/'history.csv');last=rows[-1] if rows else prog
  mode='wave' if 'wave' in str(path.name).lower() or 'wave' in str(s.get('scope','')).lower() else 'calm'
  if not rows and any(k in str(s.get('status','')).lower() for k in ('build','mesh','prepar','setup')):mode='preparation'
  out['activity']={'state':'running','mode':mode,'case':case,'description':s.get('scope',s.get('purpose','Campaign calculation')),'stage':s.get('status','Running'),'controller_pid':s.get('controller_pid',s.get('pid')),'source':str(path),'directory':str(folder),'metrics':last,'saved_at':datetime.datetime.fromtimestamp((folder/'history.csv').stat().st_mtime).astimezone().isoformat() if (folder/'history.csv').exists() else s.get('updated_at'),'progress':prog}
  saved_at=out['activity'].get('saved_at')
  try:out['activity']['data_age_s']=time.time()-datetime.datetime.fromisoformat(saved_at).timestamp()
  except (ValueError,TypeError):out['activity']['data_age_s']=None
  if len(rows)>2:
   a,b=rows[-2:];dt=(b.get('time_s',b.get('physical_time_s')) or 0)-(a.get('time_s',a.get('physical_time_s')) or 0)
   wa=a.get('wall_s',a.get('wall_seconds'));wb=b.get('wall_s',b.get('wall_seconds'))
   if dt>0 and wa is not None and wb is not None:
    out['activity']['cost']={'seconds_per_step':wb-wa,'seconds_per_physical_second':(wb-wa)/dt}
  for name in ('latest_checkpoint.json','checkpoint.json'):
   if (folder/name).exists():out['activity']['checkpoint']=read(folder/name);break
  if 'checkpoint' not in out['activity']:
   saved=[p for p in list(folder.glob('checkpoint_t*.sim'))+list(folder.glob('final.sim')) if p.is_file() and p.stat().st_size>0 and time.time()-p.stat().st_mtime>5]
   if saved:
    p=max(saved,key=lambda p:p.stat().st_mtime);out['activity']['checkpoint']={'path':str(p),'size_bytes':p.stat().st_size,'modified_at':datetime.datetime.fromtimestamp(p.stat().st_mtime).astimezone().isoformat(),'verification':'File observed; validity requires the corresponding completed save record'}
  out['activity']['elapsed_wall_s']=time.time()-datetime.datetime.fromisoformat(bypid[s.get('controller_pid',s.get('pid'))]['created']).timestamp()
  out['activity']['cells']=prog.get('cells',prog.get('cell_count',s.get('cells')))
  if mode=='calm' and rows:
   t=last.get('physical_time_s',last.get('time_s',0));windows=[[r for r in rows if t-hi<(r.get('physical_time_s',r.get('time_s',-99)) or -99)<=t-lo] for lo,hi in ((.2,.4),(0,.2))]
   times=[r.get('physical_time_s',r.get('time_s')) for r in rows];times=[x for x in times if x is not None]
   interval=times[-1]-times[-2] if len(times)>1 else 0
   covered=bool(interval>0 and times and times[0]<=t-.4+interval*1.01 and all(len(win)>2 and (win[-1].get('physical_time_s',win[-1].get('time_s'))-win[0].get('physical_time_s',win[0].get('time_s'))) >= .2-interval*1.01 for win in windows))
   if covered:
    changes={}
    for key in ('CD','CL_total'):
     if all(all(x.get(key) is not None for x in win) for win in windows):
      means=[sum(x[key] for x in win)/len(win) for win in windows];changes[key]=100*(means[1]-means[0])/abs(means[0]) if means[0] else None
    out['activity']['window_changes_pct']=changes
  if mode=='wave':
   g=history(folder/'gauges.csv');gt=g[-1].get('time_s') if g else None
   out['activity']['gauge_samples']=[x for x in g if x.get('time_s')==gt][-30:]
   budgets=history(folder/'native_phase_budget.csv')
   out['activity']['phase_budget']=budgets[-1] if budgets else {}
   if budgets:
    values=[x['native_abs_sum_pct_inward_mass'] for x in budgets if x.get('native_abs_sum_pct_inward_mass') is not None]
    out['activity']['mass_peak_pct']=max(values) if values else None
   out['activity']['mass_review_limit_pct']=0.01
 elif ownstar:
  out['activity']={'state':'unconfirmed','mode':'unknown','description':'Campaign solver process observed without a matched live controller','stage':'Inspect process ownership before any launch'}
 else:
  out['activity']={'state':'unconfirmed' if out['errors'] else ('paused' if out['stop_requested'] else 'idle'),'mode':'none','description':'Process observation unavailable' if out['errors'] else 'No campaign solver observed','stage':'Paused by user' if out['stop_requested'] else 'Idle'}
 last=read(R/'wave_propagation_state.json');done=last.get('result',{}).get('completed',{})
 out['last_wave']={'case':last.get('case'),'time_s':done.get('time_s'),'status':done.get('status'),'updated_at':last.get('updated_at'),'directory':last.get('directory')}
 out['mode_fields']={'calm':['physical_time','CD','CL','adjacent_0.2s_changes','CFL','step_cost','checkpoint'],'wave':['physical_time','gauge_actual_reference','phase_balance','speed','interface_CFL','alpha_bounds','step_cost','checkpoint'],'preparation':['stage','elapsed','cells_when_available'],'none':['last_completed','next_review']}
 write(R/'computer_status.json',out)
 return out
if __name__=='__main__':
 x=collect();print(json.dumps({'sampled_at':x['sampled_at'],'activity':x['activity']['state'],'cpu':x.get('cpu_percent'),'star_processes':x['star_processes']}))
