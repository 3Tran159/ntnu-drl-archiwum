"""Local-only CFD controls. No network exposure, no automatic solver start."""
import ctypes,datetime,hashlib,http.server,json,mimetypes,os,secrets,subprocess,sys,threading,time,uuid
from pathlib import Path
from urllib.parse import urlsplit,unquote
import manual_control_common as c
import local_control_model as workflow
import wave_side_view_refresh
import run_until_settled as e
R=c.R;B=R.parent/'dashboard_work_20261030';ORIGIN=f'http://127.0.0.1:{c.PORT}'
MUTEX=threading.Lock();PENDING=None;TOKEN=secrets.token_urlsafe(32)
def alive(pid):
 if type(pid)!=int or pid<=0:return False
 k=ctypes.windll.kernel32;k.OpenProcess.restype=ctypes.c_void_p;k.CloseHandle.argtypes=[ctypes.c_void_p];k.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
 h=k.OpenProcess(0x1000,False,pid)
 if not h:return False
 try:
  code=ctypes.c_ulong();return bool(k.GetExitCodeProcess(h,ctypes.byref(code))) and code.value==259
 finally:k.CloseHandle(h)
def active():
 lock=c.read(R/'queue.lock');s=c.read(R/'wave_foil_run_state.json')
 busy=(R/'queue.lock').exists()
 match=busy and lock.get('pid')==s.get('controller_pid') and alive(lock.get('pid'))
 case=None
 if match:
  try:case=c.safe_case(s['directory'])
  except (KeyError,ValueError):pass
 return busy,s,case
def files(s):
 try:p=c.safe_case(s['directory'])
 except (KeyError,ValueError):return []
 rows=[]
 done=c.read(p/'completed.json');cp=c.read(p/'latest_checkpoint.json');startup=c.read(p/'startup_acceptance.json')
 candidates=[]
 if done.get('time_s',0)>0:candidates.append(('final.sim',done['time_s'],'Computed state · '+str(done.get('status'))))
 if cp.get('completed_save') and cp.get('time_s',0)>0:candidates.append((Path(cp.get('file','')).name,cp['time_s'],'Completed checkpoint'))
 if startup.get('status')=='guarded_startup_completed':candidates.append(('checkpoint_startup_t0.020.sim',.02,'Completed startup checkpoint'))
 for name,t,label in candidates:
  file=p/name
  if file.is_file():rows.append(dict(path=str(file),name=name,time_s=t,label=label,size_mb=round(file.stat().st_size/1024**2,1)))
 return sorted(rows,key=lambda x:x['time_s'],reverse=True)
def status():
 global PENDING
 busy,s,case=active()
 pending=None
 if PENDING:
  p,request=PENDING
  if p.poll() is None:pending=dict(pid=p.pid,request=request.name)
  elif c.read(request.with_suffix('.error.json')):pending=dict(error=c.read(request.with_suffix('.error.json')).get('error'))
 current=case
 if current is None:
  try:current=c.safe_case(s['directory']) if s.get('directory') else None
  except (ValueError,KeyError):current=None
 schedule=c.read(current/'manual_stop_schedule.json') if current else {}
 result=dict(server_time=e.stamp(),busy=busy,controllable=case is not None and s.get('computation_active') is not False,stop_requested=bool(case and (case/'STOP').exists()),blocked_by_stop=(R/'STOP_ALL').exists(),pending=pending,state=s,files=files(s),schedule=schedule,computer=c.read(R/'control_computer_status.json'))
 try:
  import wave_arrival_dashboard_panel as arrival_panel
  result["arrival"]=arrival_panel.forecast(dict(s,computation_active=case is not None and s.get("computation_active") is not False))
 except Exception:
  result["arrival"]={"available":False,"case":s.get("case"),"status":"unavailable","reason":"Arrival forecast unavailable"}
 return result

def owned(data):
 busy,s,case=active()
 if case is None or s.get('computation_active') is False or data.get('case')!=case.name:raise ValueError('The active case changed or is not owned by this panel. Refresh first.')
 return case
def write_schedule(case,data):
 allowed={'case','physical_time_s','after_minutes'}
 if set(data)-allowed:raise ValueError('Unexpected schedule fields.')
 pt=data.get('physical_time_s');minutes=data.get('after_minutes')
 if pt is None and minutes is None:raise ValueError('Set a physical time or a wall-time delay.')
 if pt is not None:pt=c.number(pt,0,120,'Stop time [s]')
 if minutes is not None:minutes=c.number(minutes,0.1,720,'Stop delay [min]')
 deadline=time.time()+minutes*60 if minutes is not None else None
 v=dict(case=case.name,physical_time_s=pt,deadline_epoch=deadline,requested_at=e.stamp(),state='scheduled')
 for name,val in [('manual_stop_at_time.txt',pt),('manual_stop_at_epoch.txt',deadline)]:
  f=case/name
  if val is not None:
   tmp=case/(name+'.'+uuid.uuid4().hex+'.tmp');tmp.write_text(str(val),encoding='ascii');os.replace(tmp,f)
  elif f.exists():f.unlink()
 e.write(case/'manual_stop_schedule.json',v);return v
def watch():
 while True:
  try:
   _,s,case=active()
   if case:
    v=c.read(case/'manual_stop_schedule.json');p=c.read(case/'progress.json');pt=p.get('time_s',0)
    due=(v.get('physical_time_s') is not None and pt>=v['physical_time_s']-1e-9) or (v.get('deadline_epoch') is not None and time.time()>=v['deadline_epoch'])
    if v.get('state')=='scheduled' and due:
     workflow.D.mkdir(exist_ok=True);(workflow.D/'PAUSE').touch();(case/'STOP').touch();v.update(state='stop_requested',requested_stop_at=e.stamp());e.write(case/'manual_stop_schedule.json',v)
  except Exception:pass
  time.sleep(1)
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def headers_ok(self,mutation=False):
  if self.headers.get('Host')!=f'127.0.0.1:{c.PORT}':return False
  if mutation:
   return self.headers.get('Origin')==ORIGIN and secrets.compare_digest(self.headers.get('X-NTNU-Control',''),TOKEN) and self.headers.get('Content-Type','').split(';')[0]=='application/json'
  return True
 def send(self,obj,code=200):
  b=json.dumps(obj,allow_nan=False,default=str).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def do_POST(self):
  if not self.headers_ok(True):
   try:
    n=int(self.headers.get('Content-Length','0'))
    if 0<n<=4096:self.rfile.read(n)
   except ValueError:pass
   return self.send({'error':'Local same-origin control token required.'},403)
  try:
   n=int(self.headers.get('Content-Length','0'))
   if not 0<n<=4096:raise ValueError('Invalid request length.')
   d=json.loads(self.rfile.read(n))
   if not isinstance(d,dict):raise ValueError('JSON object required.')
   with MUTEX:
    global PENDING
    if self.path in ('/api/mesh-study/pause','/api/mesh-study/resume'):
     import mesh_study_control
     action=self.path.rsplit('/',1)[1]
     return self.send(getattr(mesh_study_control,action)(d),202)
    if self.path.startswith('/api/workflow/'):
     action=self.path.rsplit('/',1)[1]
     if action=='inspect-mesh':
      if set(d)!={'path'} or not isinstance(d['path'],str):raise ValueError('Paste an absolute prepared .sim path')
      return self.send(workflow.mesh_inputs().inspect_request(d['path']),202)
     if action=='select-mesh':
      if set(d)!={'id'}:raise ValueError('Choose an inspected mesh')
      workflow.mesh_inputs().set_selected(d['id']);return self.send({'message':'Selected mesh saved. No calculation started.'})
     if action=='release-hold':
      if d:raise ValueError('Unexpected fields')
      return self.send(workflow.release_hold())
     if action=='validate-recipe':
      if d:raise ValueError('Unexpected fields')
      import local_recipe_validation
      return self.send(local_recipe_validation.request(),202)
     if action=='export-handover':
      if d:raise ValueError('Unexpected fields')
      import build_standalone_handover
      return self.send(build_standalone_handover.build())
     if action=='continue-job':
      if set(d)!={'id'}:raise ValueError('Choose a saved paused job')
      return self.send(workflow.continue_job(d['id']))
     if action in ('queue','queue-all'):
      raw=d if action=='queue' else d.get('jobs')
      if action=='queue-all' and (set(d)!={'jobs'} or not isinstance(raw,list) or not 1<=len(raw)<=12):raise ValueError('Choose1?12 bounded jobs')
      items=[raw] if action=='queue' else raw
      for item in items:workflow.validate(item)
      if any(j.get('status')=='needs_review' for j in workflow.jobs()):raise ValueError('A prior job requires review acknowledgement')
      if (R/'STOP_ALL').exists():raise ValueError('Campaign stop marker present; inspect before starting')
      made=[workflow.enqueue(item) for item in items]
      return self.send({'accepted':True,'message':str(len(made))+' configuration(s) saved to queue. Press Start explicitly when ready. No calculation launched.','ids':[j['id'] for j in made]},202)
     if action in ('pause','resume'):
      if d:raise ValueError('Unexpected fields')
      if action=='resume':
       result=workflow.start_worker();return self.send({'message':'Queued jobs enabled; existing attempts are never restarted.','worker':result})
      workflow.D.mkdir(exist_ok=True);(workflow.D/'PAUSE').touch()
      _,state,case=active()
      if case is not None and state.get('computation_active') is not False:
       (case/'STOP').touch();e.write(case/'manual_stop_request.json',dict(at=e.stamp(),reason='Local queue paused by user; save current physical step'))
      return self.send({'message':'Queue paused. Active owned flow stops and saves; an ongoing preparation phase finishes before halting.'})
     if action in ('cancel','acknowledge'):
      if set(d)!={'id'}:raise ValueError('A job id is required')
      (workflow.cancel if action=='cancel' else workflow.acknowledge)(d['id'])
      return self.send({'message':'Queued job cancelled' if action=='cancel' else 'Review acknowledged; preserved attempt archived. Continue explicitly when ready.'})
     if action=='open':
      if set(d)-{'path','folder'} or 'path' not in d or not isinstance(d.get('folder',False),bool):raise ValueError('Choose a listed saved file')
      return self.send(workflow.open_file(d['path'],d.get('folder',False)))
     return self.send({'error':'Unknown workflow action'},404)
    if self.path=='/api/start':
     return self.send({'error':'Legacy start disabled. Use inspected-mesh controls and explicit Start queued jobs.'},400)
     if workflow.hold().get('active'):raise ValueError('Campaign paused for mesh review')
     cfg=c.validate_request(d)
     busy,_,_=active()
     if busy or (PENDING and PENDING[0].poll() is None):return self.send({'error':'An owned calculation or start request is already active.'},409)
     if (R/'STOP_ALL').exists():return self.send({'error':'Campaign stop marker is present. Inspect the stop reason before enabling new runs.'},409)
     reqdir=R/'manual_requests';reqdir.mkdir(exist_ok=True);req=reqdir/(uuid.uuid4().hex+'.json')
     with req.open('x',encoding='utf8') as f:json.dump(dict(**cfg,requested_at=e.stamp()),f)
     out=req.with_suffix('.stdout.log').open('x',encoding='utf8');err=req.with_suffix('.stderr.log').open('x',encoding='utf8')
     try:p=subprocess.Popen([sys.executable,str(R/'run_manual_wave.py'),str(req)],cwd=str(R),stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
     finally:out.close();err.close()
     PENDING=(p,req);return self.send({'accepted':True,'message':'Launch requested; checking source identity, process ownership and resources.','pid':p.pid},202)
    if self.path=='/api/stop':
     if set(d)!={'case'}:raise ValueError('Unexpected stop fields.')
     case=owned(d);workflow.D.mkdir(exist_ok=True);(workflow.D/'PAUSE').touch();(case/'STOP').touch();e.write(case/'manual_stop_request.json',dict(at=e.stamp(),reason='User pressed Stop and save in local panel'))
     return self.send({'message':'Stop requested. Saving begins at a physical-step boundary; wait for the saved result.'})
    if self.path=='/api/schedule':
     case=owned(d);write_schedule(case,d);return self.send({'message':'Stop schedule saved. The earliest selected limit wins; the original run target still applies.'})
    if self.path=='/api/cancel-schedule':
     if set(d)!={'case'}:raise ValueError('Unexpected fields.')
     case=owned(d)
     for name in ('manual_stop_at_time.txt','manual_stop_at_epoch.txt'):
      f=case/name
      if f.exists():f.unlink()
     e.write(case/'manual_stop_schedule.json',dict(state='cancelled',at=e.stamp()));return self.send({'message':'Schedule cancelled. A stop already requested cannot be undone.'})
    return self.send({'error':'Unknown action.'},404)
  except (ValueError,KeyError,TypeError) as ex:return self.send({'error':str(ex)},400)
  except Exception as ex:return self.send({'error':e.redact(str(ex))},500)
 def do_GET(self):
  if not self.headers_ok():return self.send({'error':'Invalid host'},403)
  path=urlsplit(self.path).path
  if path=='/api/mesh-study':
   import mesh_study_control
   return self.send(mesh_study_control.snapshot())
  if path=='/api/status':return self.send(status())
  if path=='/api/workflow':return self.send(dict(workflow.public_status(),files=workflow.file_choices()))
  if path=='/api/catalog':return self.send({'presets':c.catalog(),'startup_policy':c.wave_startup_policy(),'domain':{'x_m':[-35,45],'z_m':[-22,8],'depth_m':24,'span_m':.02},'target_range_s':[.05,12]})
  if path=='/':path='/dashboard.html'
  # Serve only public dashboard assets, never private scripts/configuration/logs.
  file=(B/unquote(path).lstrip('/')).resolve()
  if B.resolve() not in file.parents or file.suffix.lower() not in ('.html','.png','.svg','.jpg','.jpeg','.css','.js','.woff2'):return self.send({'error':'Not public'},404)
  archived_html=file.parent==B/'archive_runs' and file.stem and all(ch.isalnum() or ch in '_-' for ch in file.stem)
  if file.suffix=='.html' and not archived_html and file.name not in ('dashboard.html','professor_dashboard.html','local_campaign_results.html','standalone_control_guide.html','chat_rescue.html'):return self.send({'error':'Not public'},404)
  if not file.is_file():return self.send({'error':'Not found'},404)
  data=file.read_bytes()
  if file.name in ('dashboard.html','professor_dashboard.html'):
   # Token is session-local, never written into shared dashboard files or logs.
   marker='<script>window.NTNU_LOCAL_TOKEN='+json.dumps(TOKEN)+';</script>'
   data=data.replace(b'</head>',marker.encode()+b'</head>')
  self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(str(file))[0] or 'application/octet-stream');self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
def refresh_copies():
 last_report=0
 while True:
  try:
   import importlib,collect_control_status,build_manual_dashboard_copy
   importlib.reload(collect_control_status);importlib.reload(build_manual_dashboard_copy)
   collect_control_status.collect();build_manual_dashboard_copy.build()
   if time.monotonic()-last_report>=120:
    import build_local_control_report,build_standalone_handover
    importlib.reload(build_local_control_report);importlib.reload(build_standalone_handover)
    build_local_control_report.build();build_standalone_handover.build();last_report=time.monotonic()
  except Exception as ex:e.write(R/'manual_dashboard_copy_error.json',dict(at=e.stamp(),error=e.redact(str(ex))))
  time.sleep(25)
def main():
 k=ctypes.windll.kernel32;k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t];k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
 k.SetProcessAffinityMask(k.GetCurrentProcess(),((1<<os.cpu_count())-1)&~3);k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
 lock=R/'manual_control_server.lock'
 if lock.exists():
  v=c.read(lock)
  if alive(v.get('pid')):raise RuntimeError('Local control service is already running.')
  lock.rename(R/('manual_control_server.stale_'+uuid.uuid4().hex+'.json'))
 server=http.server.ThreadingHTTPServer(('127.0.0.1',c.PORT),Handler)
 with lock.open('x') as f:json.dump(dict(pid=os.getpid(),port=c.PORT,started_at=e.stamp()),f)
 try:
  threading.Thread(target=watch,daemon=True).start();threading.Thread(target=refresh_copies,daemon=True).start();threading.Thread(target=wave_side_view_refresh.watch,daemon=True).start();server.serve_forever()
 finally:
  server.server_close()
  if c.read(lock).get('pid')==os.getpid():lock.unlink()
if __name__=='__main__':main()
