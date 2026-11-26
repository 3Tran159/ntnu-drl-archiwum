"""Sequential exploratory CFD campaign. Default is read-only --dry-run; --run is explicit."""
import argparse,csv,datetime,hashlib,io,json,math,os,re,shutil,statistics,subprocess,threading,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent
STORAGE=Path('E:/ntnu/quasi2d_waves_20261029')
GIB=1024**3
GOOD={'calm_settled','repeatability_screen_pass'}
CASE_KEYS={'id','domain_id','height_m','source_label','prerequisites','stage','adopt_existing','notes'}
SETTINGS={'dt_s':.001,'inner':10,'order':'SECOND_ORDER','wave_min_complete_cycles':4,'typical_cycles':10,'max_cycles':20,'calm_max_time_s':6,'wall_limit_s':129600,'mass_exception_exploratory':True}
class ReviewRequired(RuntimeError):pass
def stamp():return datetime.datetime.now().astimezone().isoformat()
def read(p,default=None):
 try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return {} if default is None else default
def write(p,obj):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.'+str(os.getpid())+'.'+uuid.uuid4().hex[:8]+'.tmp')
 tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf8')
 for attempt in range(50):
  try:tmp.replace(p);return
  except PermissionError:
   if attempt==49:raise
   time.sleep(.1)
def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for block in iter(lambda:f.read(8*1024**2),b''):h.update(block)
 return h.hexdigest()
def number(value):
 try:
  x=float(value);return x if math.isfinite(x) else None
 except (TypeError,ValueError):return None
def within(path,root):
 try:return Path(path).resolve().is_relative_to(Path(root).resolve())
 except (OSError,ValueError):return False
def validate_plan(p):
 if p.get('version')!=1 or not re.fullmatch(r'[A-Za-z0-9_-]+',str(p.get('campaign_id',''))):raise ReviewRequired('Invalid campaign version/identity')
 if p.get('final_accuracy_admitted') is not False:raise ReviewRequired('Campaign must remain explicitly exploratory')
 s=p.get('settings',{})
 if set(s)!=set(SETTINGS):raise ReviewRequired('Unknown or missing calculation settings; no resource overrides accepted')
 for k,expected in SETTINGS.items():
  if s[k]!=expected:raise ReviewRequired('Unsupported calculation setting: '+k)
 cases=p.get('cases',[]);seen=set();original_finished=False
 if not cases:raise ReviewRequired('Empty campaign')
 for c in cases:
  if set(c)-CASE_KEYS:raise ReviewRequired('Unknown case keys: '+','.join(sorted(set(c)-CASE_KEYS)))
  cid=c.get('id');domain=c.get('domain_id')
  if not all(re.fullmatch(r'[A-Za-z0-9_-]+',str(v or '')) for v in [cid,domain]) or cid in seen:raise ReviewRequired('Invalid or duplicate case identity')
  if c.get('height_m') not in (0,.25,.5,.75):raise ReviewRequired('Unprepared wave height')
  labels={0:'CALM',.25:'H025',.5:'H050',.75:'H075'}
  if c.get('source_label')!=labels[c['height_m']]:raise ReviewRequired('Height/source label mismatch')
  if c.get('stage') not in ('original','original_check','extension'):raise ReviewRequired('Unknown campaign stage')
  if original_finished and c['stage']!='extension':raise ReviewRequired('Original cases cannot follow extensions')
  original_finished|=c['stage']=='extension'
  if not isinstance(c.get('prerequisites'),list) or any(x not in seen for x in c['prerequisites']):raise ReviewRequired('Prerequisites must refer to earlier cases')
  if c.get('adopt_existing'):
   a=c['adopt_existing']
   if set(a)!={'directory','parent_history','initial_time_s','expected_cells'}:raise ReviewRequired('Unknown external adoption contract')
   if c['height_m']==0 or a['initial_time_s']<0:raise ReviewRequired('Invalid existing-session contract')
  seen.add(cid)
 return p
def configuration_failure(root,plan):
 """A failed external trial blocks this original configuration, never just that case."""
 for c in plan.get('cases',[]):
  if not c.get('adopt_existing'):continue
  folder=Path(c['adopt_existing']['directory']);done=read(folder/'completed.json')
  result=read(folder/'controller_result.json')
  if (folder/'macro_error.txt').exists() or (done and done.get('status') not in ('stopped_by_marker','target_reached')) or result.get('error'):
   return {'case':c['id'],'status':'unarmed_configuration_guard_failure','physical_time_s':done.get('time_s'),'completion_status':done.get('status'),'directory':str(folder),'review':str(Path(root)/'wave_foil_r2_guard_review.json'),'reason':'Existing wave trial failed a physical guard or macro check. This plan is unarmed; a separate diagnostic does not approve it.'}
 return None
def csv_rows(path):
 text=Path(path).read_text(encoding='utf-8-sig')
 # A concurrently written, unterminated last record is not a completed report.
 if text and not text.endswith(('\n','\r')):text=text.rsplit('\n',1)[0]+'\n' if '\n' in text else ''
 return list(csv.DictReader(io.StringIO(text)))
def native_audit(folder,steps):
 try:rows=csv_rows(Path(folder)/'native_phase_budget.csv')
 except (OSError,csv.Error):return {'pass':False,'reason':'Native phase history missing'}
 fields=('time_s','step','dt_s','native_water_error_kg_step','native_air_error_kg_step','native_abs_sum_pct_inward_mass','inward_mass_kg_s')
 if not rows or any(any(number(row.get(k)) is None for k in fields) for row in rows):return {'pass':False,'reason':'Nonfinite native phase report'}
 audit=read(Path(folder)/'native_inner_sampling_audit.json');expected=steps*10
 passed=(len(rows)==steps and audit.get('completed_physical_steps')==steps and audit.get('expected_per_step')==10 and audit.get('expected_inner_samples')==expected and all(expected<=audit.get(k,-1)<=expected+10 for k in ('water_samples','air_samples')))
 peak=max(float(row['native_abs_sum_pct_inward_mass']) for row in rows)
 return {'pass':passed,'post_step_samples':len(rows),'native_abs_peak_pct':peak,'mass_review_flag':peak>.01,'mass_limit_pct':.01,'exploratory_exception_applied':True,'inner_sampling':audit}
def force_rows(path):
 rows=[];bad=[]
 try:
  for i,row in enumerate(csv_rows(path),2):
    t=number(row.get('time_s'));cd=number(row.get('CD'));cl=number(row.get('CL_total'))
    if None in (t,cd,cl):bad.append(i);continue
    rows.append(dict(row,time_s=t,CD=cd,CL_total=cl))
 except (OSError,csv.Error):return [],['unreadable']
 return rows,bad
def calm_screen(path):
 rows,bad=force_rows(path);out={'pass':False,'window_s':.2,'limit_pct':.5,'invalid_rows':bad}
 if bad or len(rows)<4:return out
 times=[x['time_s'] for x in rows]
 if any(b<=a for a,b in zip(times,times[1:])):return dict(out,reason='Non-monotonic history')
 t=times[-1];dt=statistics.median(b-a for a,b in zip(times,times[1:]))
 if t<.4 or times[0]>t-.4+1e-9:return dict(out,reason='Two full adjacent 0.2 s windows unavailable')
 selected=[r for r in rows if t-.4-1e-9<=r['time_s']<=t+1e-9]
 if any(b['time_s']-a['time_s']>2.5*dt+1e-9 for a,b in zip(selected,selected[1:])):return dict(out,reason='History gap')
 previous=[r for r in rows if t-.4<r['time_s']<=t-.2]
 current=[r for r in rows if t-.2<r['time_s']<=t]
 if min(len(previous),len(current))*dt<.2-2*dt:return dict(out,reason='Incomplete averaging windows')
 values={}
 for key in ('CD','CL_total'):
  a=statistics.mean(r[key] for r in previous);b=statistics.mean(r[key] for r in current)
  change=100*abs(b-a)/abs(a) if abs(a)>1e-12 else 0. if abs(b-a)<1e-12 else None
  values[key]={'previous_mean':a,'mean':b,'change_pct':change}
 components={}
 for key in ('pressure_drag_N','viscous_drag_N','Fx_slice_N','Fz_slice_N'):
  v=[number(r.get(key)) for r in current]
  if v and all(x is not None for x in v):components[key]=statistics.mean(v)
 return dict(out,**{'pass':all(v['change_pct'] is not None and v['change_pct']<.5 for v in values.values()),'end_s':t,'previous_window_s':[t-.4,t-.2],'current_window_s':[t-.2,t],'coefficients':values,'mean_force_components_N':components})
def history_guard(path):
 rows,bad=force_rows(path)
 if bad:return 'Nonfinite or malformed independent force history'
 if not rows:return None
 previous=None
 for row in rows:
  if previous is not None and row['time_s']<=previous:return 'Non-monotonic physical time'
  previous=row['time_s']
  for key in ('max_speed_m_s','max_CFL','interface_CFL','alpha_min','alpha_max','mass_kg','water_volume_m3','pressure_drag_N','viscous_drag_N','Fx_slice_N','Fz_slice_N'):
   if number(row.get(key)) is None:return 'Nonfinite independent report: '+key
  if float(row['max_speed_m_s'])>50 or float(row['alpha_min'])< -1e-8 or float(row['alpha_max'])>1.00000001:return 'Independent physical stability guard'
  if abs(float(row['Fx_slice_N'])-float(row['pressure_drag_N'])-float(row['viscous_drag_N']))>1e-6*max(1,abs(float(row['Fx_slice_N']))):return 'Independent force-component sum mismatch'
 return None
def cycle_summary(screen):
 cycles=screen.get('last_four_cycles',[])
 if not screen.get('latest_four_complete') or len(cycles)!=4:return {}
 return {'cycle_numbers':[c['cycle'] for c in cycles],'window_s':[cycles[0]['start_s'],cycles[-1]['end_s']],
  **{key:statistics.mean(c['coefficients'][key]['mean'] for c in cycles) for key in ('CD','CL_total')}}
class Backend:
 def __init__(self):
  import run_until_settled as e
  self.e=e
 def resources(self,storage):return {'memory':self.e.free_memory(),'disk':shutil.disk_usage(storage).free}
 def redact(self,text):return self.e.redact(str(text))
 def alive(self,pid):
  if not isinstance(pid,int) or pid<=0:return False
  if pid==os.getpid():return True
  if os.name=='nt':
   import ctypes
   k=ctypes.windll.kernel32;k.OpenProcess.restype=ctypes.c_void_p
   h=k.OpenProcess(0x1000,False,pid)
   if not h:return ctypes.GetLastError()==5
   try:
    code=ctypes.c_ulong()
    return bool(k.GetExitCodeProcess(ctypes.c_void_p(h),ctypes.byref(code))) and code.value==259
   finally:k.CloseHandle(ctypes.c_void_p(h))
  try:os.kill(pid,0);return True
  except ProcessLookupError:return False
  except PermissionError:return True
 def gpu_pids(self):
  try:
   p=subprocess.run(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
   if p.returncode:raise ReviewRequired('GPU process inventory unavailable')
   return [int(x.strip()) for x in p.stdout.splitlines() if x.strip().isdigit()]
  except (OSError,subprocess.TimeoutExpired) as ex:raise ReviewRequired('GPU process inventory unavailable') from ex
 def launch(self,folder,env):
  return subprocess.Popen([str(self.e.STAR),*self.e.saved_options(1),'-gpgpu','auto:1','-batch',str(folder/'CampaignFoilWave.java'),str(folder/'input.sim')],cwd=str(folder),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 def kill_owned(self,process):
  if process.poll() is None:
   subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=30)
 def sleep(self,seconds):time.sleep(seconds)
class Controller:
 def __init__(self,root=ROOT,storage=STORAGE,backend=None):
  self.root=Path(root);self.storage=Path(storage);self.b=backend or Backend();self.token=uuid.uuid4().hex
  self.own=self.root/'autonomous_wave_campaign.lock';self.queue=self.root/'queue.lock'
  self.results_path=self.root/'campaign_results.json';self.state_path=self.root/'campaign_state.json'
  self.process=None;self.keep_locks=False
 def status(self,status,**kw):
  write(self.state_path,dict(status=status,updated_at=stamp(),controller_pid=os.getpid(),**kw))
 def stop_requested(self,folder=None):
  return (self.root/'STOP_ALL').exists() or (self.root/'STOP_CAMPAIGN').exists() or (folder is not None and (folder/'STOP').exists())
 def owned(self,path):return read(path).get('token')==self.token and read(path).get('pid')==os.getpid()
 def claim(self,path,purpose,case=None):
  try:
   with path.open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'token':self.token,'purpose':purpose,'case':case,'created_at':stamp()},f)
  except FileExistsError:raise ReviewRequired('Lock already exists; never take over or remove it: '+path.name)
 def release(self,path):
  if self.owned(path):path.unlink()
 def conflict(self):
  if self.stop_requested():return 'stop_requested'
  if self.queue.exists():
   q=read(self.queue);p=q.get('pid')
   return 'waiting_existing_session' if self.b.alive(p) or any(self.b.alive(q.get(k)) for k in ('server_pid','launcher_pid')) else 'waiting_lock_review'
  for name in ('held_wave_server.lock','wave_cycle_continuation_r2.lock'):
   if (self.root/name).exists():return 'waiting_existing_session'
  live=read(self.root/'wave_foil_run_state.json')
  if any(self.b.alive(live.get(k)) for k in ('server_pid','server_launcher_pid','launcher_pid')):return 'waiting_existing_session'
  if self.b.gpu_pids():return 'waiting_other_GPU_process'
  return None
 def check_resources(self,start=True):
  r=self.b.resources(self.storage)
  if r['memory']<(24 if start else 8)*GIB or r['disk']<(30 if start else 8)*GIB:raise ReviewRequired('Insufficient memory/disk reserve')
  return r
 def inputs(self,case):
  registry=read(self.root/'campaign_inputs'/(case['domain_id']+'.json'))
  if registry.get('status')!='paired_inputs_audited_zero_steps' or registry.get('source_unchanged') is not True or registry.get('flow_steps')!=0:raise ReviewRequired('Domain inputs are not audited zero-step sources')
  d=registry.get('domain',{});item=registry.get('inputs',{}).get(case['source_label'],{})
  if not item:raise ReviewRequired('Exact-height prepared input missing: '+case['source_label'])
  if d.get('id')!=case['domain_id'] or d.get('wave_depth_m')!=24:raise ReviewRequired('Domain identity/depth mismatch')
  for k in ('xmin_m','xmax_m','wavelength_m','zone_m'):
   if number(d.get(k)) is None:raise ReviewRequired('Missing finite domain parameter: '+k)
  if d['xmin_m']>=-2 or d['xmax_m']<=3 or d['wavelength_m'] not in (10,20,30,40):raise ReviewRequired('Unsupported domain')
  if not d.get('gauges_m') or not all(number(x) is not None and d['xmin_m']<x<d['xmax_m'] and (x< -1 or x>2) for x in d['gauges_m']):raise ReviewRequired('Invalid gauge positions')
  extent=re.search(r'_X([34])_',case['domain_id'])
  if not extent or abs((d['xmax_m']-d['xmin_m'])-int(extent.group(1))*d['wavelength_m'])>1e-8:raise ReviewRequired('Domain extent is not the registered wavelength multiple')
  cells=registry.get('cells')
  if not isinstance(cells,int) or not 10000<cells<1000000 or item.get('cells')!=cells:raise ReviewRequired('Cell count mismatch')
  if item.get('height_m')!=case['height_m']:raise ReviewRequired('Exact-height source unavailable; never modify another source height')
  source=Path(item.get('path',''));audit_path=Path(item.get('audit',''))
  if not within(source,self.storage) or not within(audit_path,self.storage) or source.suffix.lower()!='.sim' or not source.is_file() or not audit_path.is_file():raise ReviewRequired('Input or audit missing/outside campaign storage')
  if not re.fullmatch(r'[0-9a-f]{64}',str(item.get('sha256',''))) or digest(source)!=item['sha256']:raise ReviewRequired('Source hash mismatch')
  a=read(audit_path)
  if a.get('status')!='prepared_zero_steps' or a.get('flow_steps')!=0 or a.get('cells')!=cells or number(a.get('time_s')) is None or abs(number(a.get('time_s')))>1e-9:raise ReviewRequired('Zero-step audit mismatch')
  settings=a.get('settings',{})
  for key,expected in [('order','SECOND_ORDER'),('dt_s',.001),('inner',10),('water_depth_m',24),('U_m_s',18),('submergence_m',2),('outlet_pressure','ENVIRONMENTAL'),('bottom','SLIP'),('forcing_m',d['zone_m']),('damping_m',d['zone_m'])]:
   if settings.get(key)!=expected:raise ReviewRequired('Prepared setting mismatch: '+key)
  for key,expected in [('height_m',case['height_m']),('wavelength_m',d['wavelength_m']),('xmin_m',d['xmin_m']),('xmax_m',d['xmax_m'])]:
   if key in settings and settings[key]!=expected:raise ReviewRequired('Prepared wave/domain mismatch: '+key)
  if a.get('wave') is not (case['height_m']>0):raise ReviewRequired('Prepared calm/wave mismatch')
  if case['height_m']>0 and 'FifthOrderVofWave' not in str(a.get('wave_class','')):raise ReviewRequired('Fifth-order wave audit required')
  period=number(item.get('wave_period_s'))
  if case['height_m']>0 and (period is None or period<=0):raise ReviewRequired('Positive audited encounter period required')
  receipt=read(self.root/'campaign_macro_build_receipt.json')
  if receipt.get('status')!='javac_passed' or digest(self.root/'CampaignFoilWave.java')!=receipt.get('macros',{}).get('CampaignFoilWave.java'):raise ReviewRequired('Compiled macro identity mismatch')
  return {'registry':registry,'source':source,'source_sha256':item['sha256'],'audit':audit_path,'audit_sha256':digest(audit_path),'domain':d,'cells':cells,'period_s':period or 0}
 def previous(self,plan,case):
  prefix=plan['campaign_id']+'__'+case['id']+'__a'
  paths=sorted(p for p in self.storage.glob(prefix+'*') if p.is_dir())
  return paths
 def verified_result(self,result):
  if result.get('status') not in GOOD:return False
  path=Path(result.get('final_sim',''))
  return within(path,self.storage) and path.is_file() and result.get('source_unchanged') is True and bool(result.get('final_sha256')) and digest(path)==result['final_sha256']
 def adoption(self,case):
  a=case['adopt_existing'];folder=Path(a['directory'])
  if not within(folder,self.storage):raise ReviewRequired('Existing case outside campaign')
  done=read(folder/'completed.json');result=read(folder/'controller_result.json');identity=read(folder/'source_identity.json')
  screen=read(self.root/'wave_periodicity_current.json')
  if not done or not result:return None
  if done.get('status') not in ('stopped_by_marker','target_reached') or result.get('error') or (folder/'macro_error.txt').exists():raise ReviewRequired('Existing session failed or guarded; never adopt/restart it')
  if result.get('source_unchanged') is not True or identity.get('source_cells')!=a['expected_cells']:raise ReviewRequired('Existing source/cell identity unresolved')
  if screen.get('case')!=folder.name or screen.get('min_cycles')!=4 or screen.get('stop_for_repeatability') is not True or screen.get('history_quality_pass') is not True:raise ReviewRequired('Existing wave is not supported by authoritative four-cycle screen')
  final=folder/'final.sim'
  if not final.is_file():raise ReviewRequired('Existing final save missing')
  histories=[a['parent_history'],str(folder/'history.csv')]
  from wave_cycle_repeatability import evaluate
  verified=evaluate(histories,screen['period_s'],4,20)
  if not verified.get('stop_for_repeatability'):raise ReviewRequired('Existing saved histories do not reproduce repeatability')
  return {'id':case['id'],'domain_id':case['domain_id'],'height_m':case['height_m'],'status':'repeatability_screen_pass','adopted_existing':True,'directory':str(folder),'final_sim':str(final),'final_sha256':digest(final),'source_unchanged':True,'time_s':done.get('time_s'),'elapsed_wall_s':result.get('elapsed_s'),'screen':verified,'means':cycle_summary(verified),'history_paths':histories,'accuracy_admitted':False,'completed_at':stamp()}
 def audit(self,plan):
  results=read(self.results_path,{'cases':{}}).get('cases',{});rows=[]
  try:conflict=self.conflict()
  except ReviewRequired as ex:conflict=str(ex)
  for case in plan['cases']:
   row={'id':case['id'],'domain_id':case['domain_id'],'status':'pending'}
   try:
    prior=results.get(case['id'],{})
    if self.verified_result(prior):row.update(status=prior['status'],consumed=True)
    elif self.previous(plan,case):row.update(status='previous_attempt_requires_reconciliation')
    elif case.get('adopt_existing'):
     adopted=self.adoption(case);row.update(status='existing_result_ready_for_adoption' if adopted else 'waiting_existing_session')
    else:
     info=self.inputs(case);row.update(status='input_ready',cells=info['cells'],period_s=info['period_s'])
    row['prerequisites_pending']=[k for k in case['prerequisites'] if not self.verified_result(results.get(k,{}))]
   except (ReviewRequired,OSError,ValueError) as ex:row.update(status='pending_review',reason=self.b.redact(str(ex)))
   rows.append(row)
  return {'mode':'read_only_dry_run','configuration_failure':configuration_failure(self.root,plan),'campaign_id':plan['campaign_id'],'gpu_launch_performed':False,'conflict':conflict,'own_lock_exists':self.own.exists(),'cases':rows,'accuracy_admitted':False}
 def save_result(self,plan,result):
  all_results=read(self.results_path,{'campaign_id':plan['campaign_id'],'cases':{}})
  if all_results.get('campaign_id')!=plan['campaign_id']:raise ReviewRequired('Results belong to another campaign')
  all_results['cases'][result['id']]=result;all_results['updated_at']=stamp();all_results['accuracy_admitted']=False
  write(self.results_path,all_results)
 def refresh_report(self):
  try:
   import build_autonomous_campaign_report as report
   report.build(self.root,self.root.parent/'campaign_results.html')
  except Exception as ex:write(self.root/'campaign_report_error.json',{'at':stamp(),'error':self.b.redact(str(ex))})
 def reconcile(self,plan,case):
  paths=self.previous(plan,case)
  if not paths:return None
  if len(paths)!=1:raise ReviewRequired('Multiple attempts require explicit reconciliation; never choose silently')
  folder=paths[0];process=read(folder/'process.json')
  if self.b.alive(process.get('launcher_pid')):raise ReviewRequired('Previous attempt still has a live process')
  result=read(folder/'controller_result.json')
  if self.verified_result(result):self.save_result(plan,result);return result
  raise ReviewRequired('Previous attempt is consumed and unresolved. Preserve it; zero-time macro cannot resume checkpoints or restart guard failures')
 def run_case(self,plan,case,info):
  folder=self.storage/(plan['campaign_id']+'__'+case['id']+'__a001')
  if folder.exists() or self.previous(plan,case):raise ReviewRequired('Consumed attempt; never restart')
  if configuration_failure(self.root,plan):raise ReviewRequired('Unarmed configuration: adopted wave failed physical guards')
  if self.stop_requested():raise ReviewRequired('STOP requested')
  if self.conflict():raise ReviewRequired('GPU ownership changed before launch')
  self.check_resources(True);self.claim(self.queue,'Autonomous sequential exploratory wave campaign',case['id'])
  p=None;th=None;reason=None;failure=None;started=time.time();last_progress=started;last_pt=0.;last_analysis=0.;stop_at=None
  source=info['source'];sha=info['source_sha256'];dt=plan['settings']['dt_s'];period=info['period_s']
  target=20*period if case['height_m'] else plan['settings']['calm_max_time_s']
  steps=math.ceil((target-.020)/dt)
  if not 30<=steps<=50000:
   self.release(self.queue);raise ReviewRequired('Target outside compiled macro bounds')
  try:
   folder.mkdir(exist_ok=False)
   write(folder/'attempt.json',{'status':'consumed_preparing','id':case['id'],'created_at':stamp(),'plan_sha256':digest(self.root/'campaign_plan.json'),'case':case,'target_s':target,'wave_period_s':period,'startup_s':.020,'zero_time_source_required':True})
   shutil.copy2(source,folder/'input.sim');shutil.copy2(self.root/'CampaignFoilWave.java',folder/'CampaignFoilWave.java')
   if digest(folder/'input.sim')!=sha or digest(source)!=sha or digest(info['audit'])!=info['audit_sha256']:raise ReviewRequired('Source/audit changed during copy')
   write(folder/'source_identity.json',{'source':str(source),'source_sha256':sha,'audit':str(info['audit']),'audit_sha256':info['audit_sha256'],'copied_sha256':sha,'source_time_s':0,'cells':info['cells']})
   write(folder/'plan_snapshot.json',plan);write(folder/'registry_snapshot.json',info['registry'])
   d=info['domain'];env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
   values={'NTNU_WAVE_OUT':str(folder),'NTNU_WAVE_DT':dt,'NTNU_WAVE_STEPS':steps,'NTNU_WAVE_CELLS':info['cells'],'NTNU_WAVE_HEIGHT':case['height_m'],'NTNU_WAVE_WALL_S':plan['settings']['wall_limit_s'],'NTNU_CFG_XMIN':d['xmin_m'],'NTNU_CFG_XMAX':d['xmax_m'],'NTNU_CFG_LAMBDA':d['wavelength_m'],'NTNU_CFG_GAUGES':','.join(map(str,d['gauges_m']))}
   env.update({k:str(v) for k,v in values.items()})
   if self.stop_requested():raise ReviewRequired('STOP before launch')
   if configuration_failure(self.root,plan) or self.b.gpu_pids():raise ReviewRequired('Configuration or GPU ownership changed before launch')
   with (folder/'star.log').open('x',encoding='utf8') as log:
    p=self.b.launch(folder,env);self.process=p
    write(folder/'process.json',{'launcher_pid':p.pid,'controller_pid':os.getpid(),'started_at':stamp(),'gpu':True,'workers':1,'attempt':folder.name})
    def drain():
     for line in p.stdout:
      try:log.write(self.b.redact(line));log.flush()
      except ValueError:break
    th=threading.Thread(target=drain,daemon=True);th.start()
    while p.poll() is None:
     now=time.time();elapsed=now-started;progress=read(folder/'progress.json');pt=number(progress.get('time_s'))
     if pt is not None and pt>last_pt:last_pt=pt;last_progress=now
     resources=self.b.resources(self.storage)
     physical=history_guard(folder/'history.csv') if (folder/'history.csv').exists() else None
     requested=read(folder/'requested_wave_audit.json')
     if requested:
      if requested.get('height_m')!=case['height_m'] or requested.get('wavelength_m')!=d['wavelength_m'] or requested.get('reinitialized') is not False:physical='Runtime source definition differs from audited exact-height input'
      if case['height_m'] and (number(requested.get('period_s')) is None or abs(requested['period_s']-period)>max(1e-8,period*1e-8)):physical='Actual wave period differs from registry'
     if physical:failure=physical;reason=reason or 'physical_guard'
     if self.stop_requested(folder):reason=reason or 'user_stop'
     if resources['memory']<8*GIB or resources['disk']<8*GIB:failure='Resource reserve guard';reason=reason or 'resource_guard'
     if elapsed>plan['settings']['wall_limit_s']:reason=reason or 'wall_budget'
     if (last_pt<=0 and elapsed>900) or (last_pt>0 and now-last_progress>600):failure='No physical-time progress within guarded interval';reason=reason or 'progress_guard'
     if now-last_analysis>=5 and (folder/'history.csv').exists() and not failure:
      if case['height_m']:
       from wave_cycle_repeatability import evaluate
       screen=evaluate([folder/'history.csv'],period,4,20);write(folder/'cycle_repeatability.json',screen)
       if screen.get('stop_for_repeatability'):reason=reason or 'four_cycle_repeatability'
       elif screen.get('cap_reached'):reason=reason or 'twenty_cycle_review_cap'
      else:
       screen=calm_screen(folder/'history.csv');write(folder/'calm_settling.json',screen)
       if screen.get('pass'):reason=reason or 'calm_settled'
      last_analysis=now
     if reason:
      if stop_at is None:
       stop_at=now;write(folder/'stop_decision.json',{'at':stamp(),'reason':reason,'failure':failure});(folder/'STOP').touch()
      if resources['memory']<4*GIB or resources['disk']<4*GIB or now-stop_at>600:
       self.b.kill_owned(p);failure=failure or 'Owned-process save grace expired';break
     self.status('running' if not reason else 'stopping',case=case['id'],directory=str(folder),progress=progress,elapsed_s=elapsed,stop_reason=reason,period_s=period,resources_GiB={k:v/GIB for k,v in resources.items()},accuracy_admitted=False)
     self.refresh_report();self.b.sleep(2)
    if p.poll() is None:
     self.keep_locks=True;raise ReviewRequired('Owned solver remains alive; retain locks for review')
    th.join(10)
   done=read(folder/'completed.json');screen=read(folder/('cycle_repeatability.json' if case['height_m'] else 'calm_settling.json'))
   if case['height_m']:
    from wave_cycle_repeatability import evaluate
    screen=evaluate([folder/'history.csv'],period,4,20)
   else:screen=calm_screen(folder/'history.csv')
   write(folder/('cycle_repeatability.json' if case['height_m'] else 'calm_settling.json'),screen)
   error=(folder/'macro_error.txt').read_text(encoding='utf8',errors='replace') if (folder/'macro_error.txt').exists() else None
   final=folder/'final.sim';preserved=digest(source)==sha and digest(folder/'input.sim')==sha and digest(info['audit'])==info['audit_sha256']
   diagnostics=native_audit(folder,done.get('steps',0))
   healthy=diagnostics['pass'] and p.returncode==0 and done.get('status') in ('target_reached','stopped_by_marker') and not error and not failure and preserved and final.is_file() and history_guard(folder/'history.csv') is None
   passed=healthy and (screen.get('stop_for_repeatability') if case['height_m'] else screen.get('pass'))
   status=('repeatability_screen_pass' if case['height_m'] else 'calm_settled') if passed else 'needs_review'
   means=cycle_summary(screen) if case['height_m'] else {'window_s':screen.get('current_window_s'),**{k:v['mean'] for k,v in screen.get('coefficients',{}).items()}}
   result={'id':case['id'],'domain_id':case['domain_id'],'height_m':case['height_m'],'status':status,'directory':str(folder),'time_s':done.get('time_s',last_pt),'elapsed_wall_s':time.time()-started,'completed':done,'stop_reason':reason,'error':self.b.redact(error or failure) if error or failure else None,'returncode':p.returncode,'source_unchanged':preserved,'final_sim':str(final) if final.is_file() else None,'final_sha256':digest(final) if final.is_file() else None,'checkpoints':[str(x) for x in sorted(folder.glob('*.sim')) if x.name not in ('input.sim','final.sim')],'screen':screen,'independent_diagnostics':diagnostics,'means':means,'history_paths':[str(folder/'history.csv')],'accuracy_admitted':False,'completed_at':stamp()}
   write(folder/'controller_result.json',result);self.save_result(plan,result);return result
  except BaseException as ex:
   if folder.exists():
    (folder/'STOP').touch();write(folder/'controller_error.json',{'at':stamp(),'error':self.b.redact(str(ex)),'checkpoints_preserved':True})
   if p is not None and p.poll() is None:self.keep_locks=True
   raise
  finally:
   self.process=None
   if not self.keep_locks:self.release(self.queue)
 def run(self,plan,once=False):
  blocked=configuration_failure(self.root,plan)
  if blocked:
   self.status('unarmed_configuration_guard_failure',failure=blocked);self.refresh_report();return 2
  self.claim(self.own,'Autonomous wave campaign controller')
  try:
   while True:
    blocked=configuration_failure(self.root,plan)
    if blocked:self.status('unarmed_configuration_guard_failure',failure=blocked);self.refresh_report();return 2
    if self.stop_requested():self.status('stopped_by_user');return 0
    results=read(self.results_path,{'cases':{}}).get('cases',{})
    case=next((c for c in plan['cases'] if not self.verified_result(results.get(c['id'],{}))),None)
    if case is None:self.status('campaign_complete',accuracy_admitted=False);self.refresh_report();return 0
    try:
     if any(not self.verified_result(results.get(k,{})) for k in case['prerequisites']):raise ReviewRequired('Parent prerequisites unresolved')
     if case['height_m'] and not any(c['domain_id']==case['domain_id'] and c['height_m']==0 and self.verified_result(results.get(c['id'],{})) for c in plan['cases']):raise ReviewRequired('Matched-domain calm result is not settled')
     if self.reconcile(plan,case):continue
     if case.get('adopt_existing'):
      adopted=self.adoption(case)
      if adopted:self.save_result(plan,adopted);self.refresh_report();continue
      self.status('waiting_existing_session',case=case['id'],directory=case['adopt_existing']['directory']);self.refresh_report()
      if once:return 0
      self.b.sleep(30);continue
     info=self.inputs(case);conflict=self.conflict()
     if conflict:
      self.status(conflict,case=case['id']);self.refresh_report()
      if once:return 0
      self.b.sleep(30);continue
     self.check_resources();result=self.run_case(plan,case,info);self.refresh_report()
     if result['status'] not in GOOD:self.status('needs_review',case=case['id'],reason='First unresolved attempt preserved; later configurations remain pending');return 2
     if once:return 0
    except ReviewRequired as ex:
     self.status('needs_review',case=case['id'],reason=self.b.redact(str(ex)));self.refresh_report();return 2
  finally:
   if not self.keep_locks:self.release(self.own)
def main():
 parser=argparse.ArgumentParser(description=__doc__);mode=parser.add_mutually_exclusive_group();mode.add_argument('--dry-run',action='store_true');mode.add_argument('--run',action='store_true');parser.add_argument('--once',action='store_true',help='With --run, perform at most one ready case or one waiting check')
 args=parser.parse_args();plan=validate_plan(read(ROOT/'campaign_plan.json'));controller=Controller()
 if not args.run:print(json.dumps(controller.audit(plan),indent=2,ensure_ascii=False));return 0
 return controller.run(plan,args.once)
if __name__=='__main__':
 try:raise SystemExit(main())
 except ReviewRequired as ex:print('Campaign requires review: '+str(ex));raise SystemExit(2)