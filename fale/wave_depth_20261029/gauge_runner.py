"""Short VOF wave gauge test for built Stokes-V CFD cases."""
from pathlib import Path
import os,re,subprocess,sys,time,json
job=Path(sys.argv[1]).resolve(); case=job.parent
root=Path(r'F:\ntnu\wave_depth_20261029')
if case.parent!=root/'fifth_cases':raise RuntimeError('Case not from fixed fifth_cases workspace')
star=Path(r'E:\Program Files\Siemens\21.02.007-R8\STAR-CCM+21.02.007-R8\star\lib\win64\clang20.1vc14.2-r8\lib\starccm+.exe')
source=case/'built.sim'
macro=root/'WaveGaugeRun.java'
log=case/'gauge.log'
if log.exists() or not source.exists():raise RuntimeError('Absent source or previous gauge log')
env=dict(os.environ,NTNU_WAVE_GAUGE_JOB=str(job))
with log.open('x',encoding='utf-8') as fo:
 p=subprocess.Popen([str(star),'-config','bs','-np','2','-batch',str(macro),str(source)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,cwd=str(case),encoding='utf-8',errors='replace',text=True)
 (case/'gauge_pid.json').write_text(json.dumps({'pid':p.pid,'start':time.time()}))
 for line in p.stdout:
  fo.write(re.sub(r'(?i)(-podkey\s+)(?:"[^"]*"|\S+)',r'\1REDACTED',line));fo.flush()
 code=p.wait()
 (case/'gauge_exit.json').write_text(json.dumps({'returncode':code,'end':time.time()}))
 print('WAVE_GAUGE_RESULT',case.name,code)
