from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'local_control_model.py';s=p.read_text()
s=s.replace(" j.update(status='cancelled',updated_at=stamp());write(p,j)"," (p.parent/'CANCEL').touch(exist_ok=True)\n j.update(status='cancelled',updated_at=stamp());write(p,j)")
s=s.replace("def start_worker():\n lock=","""def readiness():
 a=read(R/'local_control_macro_receipt.json');b=read(R/'local_control_zero_step_review.json');t=read(R/'local_control_test_review.json')
 ready=a.get('status')=='javac_passed' and b.get('status')=='zero_step_API_audit_passed' and a.get('macro_sha256')==b.get('macro_sha256') and t.get('status')=='passed'
 return dict(ready=ready,macro=a.get('status'),api_audit=b.get('status'),tests=t.get('status'),message='Ready for exploratory local jobs; full propagation and force accuracy remain separate checks' if ready else 'Local recipe checks are still in progress')
def acknowledge(jobid):
 if not isinstance(jobid,str) or not all(c.isalnum() or c=='_' for c in jobid):raise ValueError('Invalid job')
 p=D/'jobs'/jobid/'job.json';j=read(p)
 if j.get('status')!='needs_review':raise ValueError('Job is not awaiting review')
 j.update(status='reviewed_archived',review_acknowledged_at=stamp(),message='User acknowledged review; attempt preserved and never resumed');write(p,j)
def start_worker():
 if not readiness()['ready']:raise ValueError('Local recipe checks are still in progress')
 if any(j.get('status')=='needs_review' for j in jobs()):raise ValueError('A failed/stopped job needs review acknowledgement before more work')
 lock=""")
s=s.replace("report=str(R.parent/'local_campaign_results.html'))","report=str(R.parent/'local_campaign_results.html'),readiness=readiness())")
p.write_text(s,encoding='utf-8');compile(s,p.name,'exec')
p=R/'local_control_worker.py';s=p.read_text()
s=s.replace(" if m.read(D/'jobs'/j['id']/'job.json').get('status')=='cancelled'"," if (D/'jobs'/j['id']/'CANCEL').exists() or m.read(D/'jobs'/j['id']/'job.json').get('status')=='cancelled'")
s=s.replace("def status(j,text,**kw):\n j.update","def status(j,text,**kw):\n if kw.get('status')!='cancelled':ensure_not_cancelled(j)\n j.update")
s=s.replace(" ensure_not_cancelled(j)\n s=j['spec'];t0"," ensure_not_cancelled(j)\n if pause():raise Halt('Queue paused; no new solver launch')\n s=j['spec'];t0")
s=s.replace(" if not psrc.is_file() or e.digest(psrc)!=source['sha256']"," if not psrc.resolve().is_relative_to(W.resolve()) or not psrc.is_file() or e.digest(psrc)!=source['sha256']")
s=s.replace(" own_lock(lock,token,folder.name);folder.mkdir()\n j['attempts'].append(dict(mode=mode,directory=str(folder),source=str(psrc),source_time_s=t0));status(j,'Loading '+phase+' from verified saved state',status='running')\n try:",""" try:
  ensure_not_cancelled(j)
  if pause():raise Halt('Queue paused before solver claim')
  own_lock(lock,token,folder.name);folder.mkdir()
  j['attempts'].append(dict(mode=mode,directory=str(folder),source=str(psrc),source_time_s=t0));status(j,'Loading '+phase+' from verified saved state',status='running')""")
s=s.replace("  with (folder/'star.log').open('x',encoding='utf-8') as log:\n   proc=","""  with (folder/'star.log').open('x',encoding='utf-8') as log:
   ensure_not_cancelled(j)
   if pause():raise Halt('Queue paused before STAR launch')
   proc=""")
s=s.replace("  m.write(folder/'local_error.json',dict(error=e.redact(str(ex)),at=m.stamp()))","  if folder.exists():m.write(folder/'local_error.json',dict(error=e.redact(str(ex)),at=m.stamp()))")
s=s.replace("def process_job(j):\n s=","def process_job(j):\n ensure_not_cancelled(j)\n s=")
s=s.replace("  calm=execute_solver(j,'calm',prepared)","  ensure_not_cancelled(j)\n  if pause():raise Halt('Queue paused after domain preparation; no calm solver started')\n  calm=execute_solver(j,'calm',prepared)")
p.write_text(s,encoding='utf-8');compile(s,p.name,'exec')
p=R/'local_domain_preparation.py';s=p.read_text().replace('from prepare_campaign_domain import cpu,P,Q','from prepare_campaign_domain import cpu as _cpu,P,Q')
s=s.replace("R=m.R;W=m.W","""R=m.R;W=m.W
def cpu(*a,**kw):
 if (m.D/'PAUSE').exists():raise RuntimeError('Queue paused before preparation phase')
 result=_cpu(*a,**kw)
 if (m.D/'PAUSE').exists():raise RuntimeError('Queue paused; completed current preparation phase, no further work')
 return result""")
p.write_text(s,encoding='utf-8');compile(s,p.name,'exec')
print('Durable cancellation, phase pause and readiness gates added')
