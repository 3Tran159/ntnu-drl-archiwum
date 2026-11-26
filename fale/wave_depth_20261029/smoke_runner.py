"""One short reference-case CFD smoke test; never changes built.sim."""
import json,re,time,subprocess
from pathlib import Path
root=Path(r'F:\ntnu\wave_depth_20261029');folder=root/'W20_H16_X3'
star=Path(r'E:\Program Files\Siemens\21.02.007-R8\STAR-CCM+21.02.007-R8\star\lib\win64\clang20.1vc14.2-r8\lib\starccm+.exe')
src=folder/'built.sim';macro=root/'WaveTankSmoke.java';log=folder/'smoke.log'
if not src.is_file():raise RuntimeError('Reference wave SIM missing')
if log.exists():raise RuntimeError('Do not overwrite smoke attempt')
with log.open('x',encoding='utf-8') as fh:
 p=subprocess.Popen([str(star),'-config','bs','-np','2','-batch',str(macro),str(src)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8',errors='replace',text=True,cwd=str(folder))
 (folder/'smoke_pid.json').write_text(json.dumps({'pid':p.pid,'start_unix':time.time()}))
 try:
  for line in p.stdout:
   fh.write(re.sub(r'(?i)(-podkey\s+)(?:"[^"]*"|\S+)',r'\1REDACTED',line));fh.flush()
  code=p.wait(timeout=900)
 except subprocess.TimeoutExpired:
  p.terminate()
  try:code=p.wait(timeout=30)
  except subprocess.TimeoutExpired:p.kill();code=p.wait()
 (folder/'smoke_exit.json').write_text(json.dumps({'returncode':code,'end_unix':time.time()}))
 print('SMOKE FINISHED',code)
