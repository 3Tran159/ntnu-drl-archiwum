"""Run an isolated wave-tank macro. Does not touch other STAR sessions."""
import json,os,subprocess,sys,time,re
from pathlib import Path
job=Path(sys.argv[1]).resolve()
case=job.parent
spec=json.loads(job.read_text(encoding='utf-8'))
root=Path(r'F:\ntnu\wave_depth_20261029').resolve()
if root not in job.parents or case!=job.parent: raise RuntimeError("Outside wave workspace")
source=case/'baseline_copy.sim'
macro=root/'WaveTankBuild.java'
star=Path(r'E:\Program Files\Siemens\21.02.007-R8\STAR-CCM+21.02.007-R8\star\lib\win64\clang20.1vc14.2-r8\lib\starccm+.exe')
log=case/'build.log'
if log.exists(): raise RuntimeError("Refusing to overwrite "+str(log))
env=dict(os.environ,NTNU_WAVE_JOB=str(job))
cmd=[str(star),'-config','bs','-np','2','-batch',str(macro),str(source)]
with log.open('x',encoding='utf-8') as w:
 p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,cwd=str(case),encoding='utf-8',errors='replace',text=True)
 (case/'launcher_pid.json').write_text(json.dumps({'pid':p.pid,'command_exe':str(star),'started_epoch':time.time()},indent=2))
 try:
  for line in p.stdout:
   w.write(re.sub(r'(?i)(-podkey\s+)(?:"[^"]*"|\S+)',r'\1REDACTED',line));w.flush()
  code=p.wait(timeout=900)
 except subprocess.TimeoutExpired:
  p.terminate()
  try: code=p.wait(timeout=30)
  except subprocess.TimeoutExpired: p.kill();code=p.wait()
 (case/'exit.json').write_text(json.dumps({'returncode':code,'end_epoch':time.time()},indent=2))
 print('FINISH',case.name,'code',code)
