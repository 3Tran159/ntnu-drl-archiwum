"""Diagnose STAR-CCM wave startup on disposable in-memory model. Never save."""
from pathlib import Path
import os,re,subprocess,sys,time,json
variant=sys.argv[1]
if variant not in ("zone_none","zone_none_v2","flat_only","new_length","deep","full"):raise SystemExit("bad variant")
root=Path(r'F:\ntnu\wave_depth_20261029')
base=root/'W20_H16_X3'/'built.sim'
macro=root/'WaveTankDiagnose.java'
exe=Path(r'E:\Program Files\Siemens\21.02.007-R8\STAR-CCM+21.02.007-R8\star\lib\win64\clang20.1vc14.2-r8\lib\starccm+.exe')
log=root/f'diagnose_{variant}.log'
if log.exists():raise RuntimeError("No overwrite for "+str(log))
env=dict(os.environ,NTNU_WAVE_DIAG_VARIANT=variant)
with log.open('x',encoding='utf-8') as out:
 p=subprocess.Popen([str(exe),'-config','bs','-np','2','-batch',str(macro),str(base)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8',errors='replace',text=True,env=env,cwd=str(root))
 (root/f'diagnose_{variant}_pid.json').write_text(json.dumps({'pid':p.pid,'start':time.time()}))
 for line in p.stdout:
  out.write(re.sub(r'(?i)(-podkey\s+)(?:"[^"]*"|\S+)',r'\1REDACTED',line));out.flush()
 code=p.wait()
 (root/f'diagnose_{variant}_exit.json').write_text(json.dumps({'returncode':code,'end':time.time()}))
 print(variant,code)
