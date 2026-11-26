"""Sequential two-CPU zero-step audits of copied saved states; no GPU work."""
from pathlib import Path
import json,shutil,hashlib,subprocess,sys,datetime,os
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029';A=Path('E:/ntnu/temporal_conservation_20261029/r1');T=R/'temporal_order_20261029'
def write(p,d):p.write_text(json.dumps(d,indent=2),encoding='utf-8')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()
if A.exists():raise RuntimeError('Existing audit preserved; use a new revision')
if shutil.disk_usage('E:/').free<3*1024**3:raise RuntimeError('Need storage')
A.mkdir(parents=True)
write(R/'temporal_mass_audit_state.json',{'status':'running','pid':os.getpid(),'folder':str(A),'np':2,'steps':0})
try:
 outputs=[]
 for name,src in [('M04_start',R/'M04_until_settled_r2/final.sim'),('T01_final',T/'T01_M04_FO_dt1ms_r1/final.sim'),('T02_final',T/'T02_M04_SO_dt1ms_r1/final.sim')]:
  dst=A/(name+'.sim');before=sha(src);shutil.copy2(src,dst)
  if sha(dst)!=before:raise RuntimeError('Copy mismatch')
  job={'source':str(dst),'macro':str(R/'AuditTemporalMassR1.java'),'log':str(A/(name+'.log')),'np':2,'timeout_s':600};jp=A/(name+'_job.json');write(jp,job)
  p=subprocess.run([sys.executable,str(Q/'run_job.py'),str(jp)],capture_output=True,timeout=650,creationflags=subprocess.CREATE_NO_WINDOW)
  (A/(name+'_runner.log')).write_bytes(p.stdout+b'\n'+p.stderr)
  result=A/(name+'_audit.json')
  exit_status=json.loads((A/(name+'.exit.json')).read_text())
  if exit_status['returncode']!=0 or not result.exists():raise RuntimeError(name+': audit failed; inspect redacted log')
  unchanged=sha(src)==before and sha(dst)==before
  if not unchanged:raise RuntimeError('Source/copy changed')
  outputs.append({'name':name,'source_unchanged':unchanged,'sha256':before,'audit':json.loads(result.read_text())})
 write(A/'verification.json',outputs)
 write(R/'temporal_mass_audit_state.json',{'status':'completed_zero_step_audits','folder':str(A),'cases':[x['name'] for x in outputs],'np':2,'steps':0,'updated_at':datetime.datetime.now().astimezone().isoformat()})
except BaseException as ex:
 write(R/'temporal_mass_audit_state.json',{'status':'needs_review','folder':str(A),'error':str(ex),'updated_at':datetime.datetime.now().astimezone().isoformat()});raise
