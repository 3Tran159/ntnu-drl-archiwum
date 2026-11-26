"""Run one isolated STAR task; redact license keys while streaming its log."""
import json,os,re,subprocess,sys,time,threading
from pathlib import Path

ROOT=Path(r'F:\ntnu\mesh_screening_20261028')
STAR=Path(r'E:\Program Files\Siemens\21.02.007-R8\STAR-CCM+21.02.007-R8\star\lib\win64\clang20.1vc14.2-r8\lib\starccm+.exe')
def main():
    spec=Path(sys.argv[1]);j=json.loads(spec.read_text(encoding='utf-8-sig'));dest=Path(j['log']).resolve();source=Path(j['source']).resolve();macro=Path(j['macro']).resolve()
    for p in (dest,source,macro):
        if not p.is_relative_to(ROOT):raise ValueError('Outside task scope')
    if dest.exists():raise ValueError('Preserve existing log')
    env=dict(os.environ);env.update(j.get('env',{}));cmd=[str(STAR),'-config','bs',*j.get('extra',[]),'-batch',str(macro),str(source)]
    with dest.open('x',encoding='utf-8') as log:
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,cwd=str(macro.parent),text=True,encoding='utf-8',errors='replace')
        (dest.parent/(dest.stem+'_pid.json')).write_text(json.dumps({'launcher_pid':proc.pid,'source':str(source),'start_unix':time.time()}))
        timed_out=threading.Event()
        def watchdog():
            try:proc.wait(timeout=j.get('timeout_s',1800))
            except subprocess.TimeoutExpired:
                timed_out.set();subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True)
        t=threading.Thread(target=watchdog,daemon=True);t.start()
        for line in proc.stdout:
            log.write(re.sub(r'(?i)(-podkey\s+)(?:"[^"]*"|\S+)',r'\1REDACTED',line));log.flush()
        rc=proc.wait();(dest.parent/(dest.stem+'_exit.json')).write_text(json.dumps({'returncode':rc,'timeout':timed_out.is_set(),'finish_unix':time.time()}))
    print('Task finished:',dest.name,'returncode',rc,'timeout',timed_out.is_set())
if __name__=='__main__':main()
