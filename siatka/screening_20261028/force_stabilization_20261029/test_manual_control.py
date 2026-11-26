"""Control verification without launching or stopping any CFD process."""
import tempfile,threading,urllib.request,urllib.error,json,time,types,sys
from pathlib import Path
from unittest.mock import patch
import manual_control_server as s
import manual_control_common as c
tests=[]
def check(name,fn):
 fn();tests.append(name)
for bad in ({'preset':'W02','target_s':1.2,'wall_minutes':30},{'preset':'W01_M10','target_s':float('nan'),'wall_minutes':30},{'preset':'W01_M10','target_s':True,'wall_minutes':30},{'preset':'W01_M10','target_s':1.2345,'wall_minutes':30},{'preset':'W01_M10','target_s':1.2,'wall_minutes':30,'source':'C:/anything'}):
 try:c.validate_request(bad);raise AssertionError('Accepted invalid input')
 except ValueError:pass
tests.append('Reject unprepared, nonfinite, boolean, fractional-step and arbitrary-source requests')
assert c.validate_request(dict(preset='W01_M10',target_s=8.5,wall_minutes=360))['target_s']==8.5
# Isolated HTTP server and mocked subprocess; no actual solver can be launched.
real_R=c.R;mockcalls=[]
with tempfile.TemporaryDirectory(prefix='ntnu_control_test_') as td:
 root=Path(td);case=root/'test_case';case.mkdir()
 s.R=root;s.B=root;s.PENDING=None
 s.active=lambda:(False,{'case':case.name,'directory':str(case)},None)
 class FakeProcess:
  pid=999999
  def poll(self):return None
 def fake_popen(*args,**kwargs):mockcalls.append(args);return FakeProcess()
 with patch.object(s.subprocess,'Popen',fake_popen):
  srv=s.http.server.ThreadingHTTPServer(('127.0.0.1',0),s.Handler);c.PORT=srv.server_address[1];s.ORIGIN='http://127.0.0.1:'+str(c.PORT)
  th=threading.Thread(target=srv.serve_forever,daemon=True);th.start()
  def post(path,data,auth=True,origin=None):
   h={'Content-Type':'application/json'}
   if auth:h.update({'X-NTNU-Control':s.TOKEN,'Origin':origin or s.ORIGIN})
   req=urllib.request.Request(s.ORIGIN+path,json.dumps(data).encode(),h,method='POST')
   try:
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=10) as r:return r.status,json.load(r)
   except urllib.error.HTTPError as e:return e.code,json.load(e)
  cfg=dict(preset='W01_M10',target_s=1.2,wall_minutes=180)
  assert post('/api/start',cfg,False)[0]==403
  assert post('/api/start',cfg,True,'http://malicious.invalid')[0]==403
  tests.append('Reject missing token and foreign origin')
  assert post('/api/start',cfg)[0]==202 and len(mockcalls)==1
  assert post('/api/start',cfg)[0]==409 and len(mockcalls)==1
  tests.append('One start request only; repeat start blocked (mock process)')
  s.PENDING=None;s.active=lambda:(True,{'case':case.name,'directory':str(case),'computation_active':False},case)
  assert post('/api/stop',{'case':case.name})[0]==400 and not (case/'STOP').exists()
  tests.append('Saved paused server cannot receive a new stop action')
  s.active=lambda:(True,{'case':case.name,'directory':str(case),'computation_active':True},case)
  assert post('/api/stop',{'case':'another'})[0]==400 and not (case/'STOP').exists()
  assert post('/api/schedule',{'case':case.name,'physical_time_s':.8,'after_minutes':5})[0]==200
  assert float((case/'manual_stop_at_time.txt').read_text())==.8
  assert post('/api/cancel-schedule',{'case':case.name})[0]==200 and not (case/'manual_stop_at_time.txt').exists()
  assert post('/api/stop',{'case':case.name})[0]==200 and (case/'STOP').exists()
  tests.append('Owned stop, combined schedule and cancellation work in isolated folder; wrong-case stop rejected')
  srv.shutdown();srv.server_close()
out=dict(status='passed',tests=tests,solver_processes_started=0,real_case_stop_markers_written=0,scope='Isolated mocked launch + temporary stop files; actual CFD macro compiled, not flow-tested in new manual presets')
(real_R/'manual_control_test_review.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out,indent=2))
