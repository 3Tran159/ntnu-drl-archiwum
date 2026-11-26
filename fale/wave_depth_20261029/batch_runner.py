"""Safely build all 10 no-foil wave candidates in ONE STAR-CCM+ server."""
from pathlib import Path
import os,re,subprocess,time,json
root=Path(r'F:\ntnu\wave_depth_20261029')
base=root/'batch_baseline_copy.sim'
macro=root/'WaveTankBatch.java'
star=Path(r'E:\Program Files\Siemens\21.02.007-R8\STAR-CCM+21.02.007-R8\star\lib\win64\clang20.1vc14.2-r8\lib\starccm+.exe')
log=root/'batch_build.log'
if not base.exists():raise RuntimeError('Disposable baseline not found')
if log.exists():raise RuntimeError('Build log already exists, no overwrite')
cmd=[str(star),'-config','bs','-np','2','-batch',str(macro),str(base)]
with log.open('x',encoding='utf-8') as fh:
 p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8',errors='replace',text=True,cwd=str(root))
 (root/'batch_launcher_pid.json').write_text(json.dumps({'pid':p.pid,'start_unix':time.time()},indent=2))
 try:
  for line in p.stdout:
   fh.write(re.sub(r'(?i)(-podkey\s+)(?:"[^"]*"|\S+)',r'\1REDACTED',line));fh.flush()
  code=p.wait(timeout=900)
 except subprocess.TimeoutExpired:
  p.terminate()
  try:code=p.wait(timeout=30)
  except subprocess.TimeoutExpired:p.kill();code=p.wait()
 (root/'batch_exit.json').write_text(json.dumps({'returncode':code,'end_unix':time.time()},indent=2))
 print('BATCH_FINISH code=',code)
