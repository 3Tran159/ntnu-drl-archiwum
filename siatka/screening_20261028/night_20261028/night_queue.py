"""Resource-bounded Windows STAR queue; source files are never overwritten.

Uses the user's saved bs authentication options in memory. Never writes the key.
"""
import argparse,base64,ctypes,hashlib,json,os,re,shlex,shutil,subprocess,sys,threading,time,xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(r'F:\ntnu\mesh_screening_20261028')
DEST=Path(r'E:\ntnu_cfd_night_20261028')
STAR=Path(r'E:\Program Files\Siemens\21.02.007-R8\STAR-CCM+21.02.007-R8\star\lib\win64\clang20.1vc14.2-r8\lib\starccm+.exe')
GIB=1024**3
class Memory(ctypes.Structure):
    _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('page_total',ctypes.c_ulonglong),('page_free',ctypes.c_ulonglong),('virtual_total',ctypes.c_ulonglong),('virtual_free',ctypes.c_ulonglong),('extended',ctypes.c_ulonglong)]
def free_memory():
    m=Memory();m.length=ctypes.sizeof(m)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):raise OSError('Memory query failed')
    return m.free
def saved_options(np):
    config=Path(os.environ['LOCALAPPDATA'])/'Siemens/STAR-CCM+ 21.02.007/config/serverConf.xml'
    node=ET.parse(config).getroot().find(".//*[@name='bs']/command")
    if node is None or not node.text:raise ValueError('Saved bs configuration missing')
    return parse_saved_command(node.text,np)
def parse_saved_command(command,np):
    if not isinstance(np,int) or not 1<=np<=24:raise ValueError('Invalid process allocation')
    args=shlex.split(command,posix=False)[1:];out=[];i=0
    while i<len(args):
        if args[i]=='-server':i+=1;continue
        if args[i] in ['-np','-gpgpu','-cpubind']:
            i+=2;continue
        out.append(args[i].strip('"'));i+=1
    return out+['-np',str(np),'-cpubind','off']
def classify_outcome(rc,summary,status='running'):
    if status!='running':return status
    if rc!=0 or not summary:return 'failed'
    if summary.get('status')=='unstable_or_no_progress':return 'failed_stability'
    if summary.get('status') not in ['wall_budget_completed','step_budget_completed','stopped_by_marker']:return 'failed_unrecognized_result'
    return 'completed'
def redact(line):return re.sub(r'(?i)(-podkey\s+)(?:"[^"]*"|\S+)',r'\1REDACTED',line)
def kill_owned(proc,source):
    enc=base64.b64encode(str(source).encode()).decode()
    script="$e='"+enc+"'; Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^star-?ccm\\+\\.exe$' -and $_.CommandLine -like ('*'+$e+'*')} | ForEach-Object {Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue}"
    subprocess.run(['powershell.exe','-NoProfile','-Command',script],capture_output=True,timeout=30)
    subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,timeout=30)
def run_case(job_path,resources):
    j=json.loads(job_path.read_text(encoding='utf-8-sig'));source=Path(j['source']).resolve();out=Path(j['output']).resolve();macro=Path(j['macro']).resolve()
    if not source.is_relative_to(ROOT) or not macro.is_relative_to(ROOT) or not out.is_relative_to(DEST):raise ValueError('Path guard')
    if not source.is_file():raise ValueError('Missing saved mesh')
    if j.get('source_sha256'):
        h=hashlib.sha256()
        with source.open('rb') as f:
            for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
        if h.hexdigest()!=j['source_sha256']:raise ValueError('Mesh identity changed')
    out.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(out).free<max(20*GIB,source.stat().st_size*5):raise ValueError('Insufficient output disk reserve')
    if (out/'star.log').exists():raise ValueError('Preserve previous attempt')
    original_source=source
    source=out/'working_copy.sim'
    if source.exists():raise ValueError('Working copy already exists')
    shutil.copy2(original_source,source)
    runtime=dict(j,source=str(source),original_source=str(original_source))
    frozen_macro=out/macro.name;shutil.copy2(macro,frozen_macro)
    runtime['executed_macro']=str(frozen_macro);runtime['macro_sha256']=hashlib.sha256(frozen_macro.read_bytes()).hexdigest()
    runtime_path=out/'runtime_job.json';runtime_path.write_text(json.dumps(runtime,indent=2))
    env=dict(os.environ);env['NTNU_CFD_JOB']=str(runtime_path)
    args=[str(STAR),*saved_options(j.get('processes',8)),'-batch',str(frozen_macro),str(source)]
    started=time.time();low_count=0;status='running';samples=[];last_sample=0;minimum_free=None
    with (out/'star.log').open('x',encoding='utf-8') as log:
        proc=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,cwd=str(out),encoding='utf-8',errors='replace',text=True)
        (out/'process.json').write_text(json.dumps({'launcher_pid':proc.pid,'source':str(source),'processes':j.get('processes',8),'gpu':False,'start_unix':started}))
        def drain():
            for line in proc.stdout:log.write(redact(line));log.flush()
        reader=threading.Thread(target=drain,daemon=True);reader.start()
        while proc.poll() is None:
            free=free_memory()
            minimum_free=free if minimum_free is None else min(minimum_free,free)
            if time.time()-last_sample>=10:
                samples.append({'time_unix':time.time(),'free_physical_bytes':free})
                (out/'resources.json').write_text(json.dumps(samples));last_sample=time.time()
            if free<resources.get('soft_reserve_gib',10)*GIB:
                (out/'STOP').touch();status='memory_soft_stop'
            low_count=low_count+1 if free<resources.get('hard_reserve_gib',6)*GIB else 0
            if low_count>=1 or time.time()-started>j['wall_seconds']+resources.get('timeout_grace_s',1800):
                status='memory_emergency_stop' if low_count>=1 else 'hard_timeout';kill_owned(proc,source);break
            time.sleep(2)
        try:rc=proc.wait(timeout=30)
        except subprocess.TimeoutExpired:kill_owned(proc,source);rc=-1
        reader.join(timeout=10)
    measured=out/'completed.json'
    summary=json.loads(measured.read_text()) if measured.exists() else {}
    status=classify_outcome(rc,summary,status)
    result={'status':status,'returncode':rc,'measurement':summary,'end_unix':time.time(),'min_free_gib':minimum_free/GIB if minimum_free is not None else None}
    (out/'controller_result.json').write_text(json.dumps(result,indent=2));return result
def main():
    ap=argparse.ArgumentParser();ap.add_argument('manifest',type=Path);a=ap.parse_args();m=json.loads(a.manifest.read_text(encoding='utf-8-sig'));dest=Path(m['status_dir']);dest.mkdir(parents=True,exist_ok=True)
    # Sequential is intentional until a measured solver memory budget permits overlap.
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    results=[]
    for index,path in enumerate(m['jobs']):
        if (DEST/'STOP_ALL').exists():break
        (dest/'active_job.json').write_text(json.dumps({'job':path,'index':index+1,'total':len(m['jobs']),'state':'waiting_for_resources','updated_unix':time.time()}))
        deadline=time.time()+m.get('wait_for_memory_s',600)
        while free_memory()<m.get('required_free_gib',40)*GIB and time.time()<deadline:time.sleep(10)
        if free_memory()<m.get('required_free_gib',40)*GIB:
            results.append({'job':path,'status':'blocked_insufficient_free_memory'});break
        (dest/'active_job.json').write_text(json.dumps({'job':path,'index':index+1,'total':len(m['jobs']),'state':'running','updated_unix':time.time()}))
        try:r=run_case(Path(path),m)
        except Exception as exc:r={'status':'failed_controller','error':type(exc).__name__+': '+str(exc)}
        results.append({'job':path,**r});(dest/'queue_status.json').write_text(json.dumps(results,indent=2))
        if m.get('write_night_summary',len(m['jobs'])==4):
            try:
                from summarize_night import summarize
                summarize(m)
            except Exception as exc:(dest/'summary_error.txt').write_text(type(exc).__name__+': '+str(exc))
        if r['status'] in ['memory_emergency_stop','memory_soft_stop','hard_timeout']:break
    (dest/'queue_finished.json').write_text(json.dumps({'finished_unix':time.time(),'results':results},indent=2));ctypes.windll.kernel32.SetThreadExecutionState(0x80000000);print('Queue finished; attempted records:',len(results))
if __name__=='__main__':main()
