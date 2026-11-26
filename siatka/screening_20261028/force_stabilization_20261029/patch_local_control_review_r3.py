from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'local_control_model.py';s=p.read_text().replace('import json,math,hashlib,datetime,uuid,os,subprocess','import json,math,hashlib,datetime,uuid,os,subprocess,contextlib')
a=s.index('def cancel(jobid):');b=s.index('def catalogue():',a)
s=s[:a]+'''@contextlib.contextmanager
def job_transition(jobid):
 p=D/'jobs'/jobid/'transition.lock'
 try:
  with p.open('x') as f:f.write(str(os.getpid()))
 except FileExistsError:raise ValueError('Job is changing phase; refresh and retry')
 try:yield
 finally:p.unlink(missing_ok=True)
def cancel(jobid):
 if not isinstance(jobid,str) or not all(c.isalnum() or c=='_' for c in jobid):raise ValueError('Invalid job')
 with job_transition(jobid):
  p=D/'jobs'/jobid/'job.json';j=read(p)
  if j.get('status') not in ('queued','waiting'):raise ValueError('Only waiting jobs can be cancelled; use Stop and save for an active calculation')
  (p.parent/'CANCEL').touch(exist_ok=True)
  j.update(status='cancelled',updated_at=stamp());write(p,j)
''' + s[b:]
p.write_text(s,encoding='utf-8');compile(s,p.name,'exec')
p=R/'local_control_worker.py';s=p.read_text()
s=s.replace("  own_lock(lock,token,folder.name);folder.mkdir()\n  j['attempts'].append(dict(mode=mode,directory=str(folder),source=str(psrc),source_time_s=t0));status(j,'Loading '+phase+' from verified saved state',status='running')","""  with m.job_transition(j['id']):
   ensure_not_cancelled(j)
   own_lock(lock,token,folder.name);folder.mkdir()
   j['attempts'].append(dict(mode=mode,directory=str(folder),source=str(psrc),source_time_s=t0));status(j,'Loading '+phase+' from verified saved state',status='running')""")
s=s.replace("any(abs(float(x['evaluated_height_m'])-s['height_m'])>1e-9 for x in tail)","any(not math.isfinite(float(x['evaluated_height_m'])) or abs(float(x['evaluated_height_m'])-s['height_m'])>1e-9 for x in tail)")
p.write_text(s,encoding='utf-8');compile(s,p.name,'exec')
p=R/'build_local_control_macro.py';s=p.read_text().replace('if(Math.abs(h-requestedHeight)>1e-9||activeWave.getFirstWaveFront()', 'if(!Double.isFinite(h)||Math.abs(h-requestedHeight)>1e-9||activeWave.getFirstWaveFront()')
p.write_text(s,encoding='utf-8');compile(s,p.name,'exec')
print('Serialized cancel/launch transitions; finite-height guards strengthened')
