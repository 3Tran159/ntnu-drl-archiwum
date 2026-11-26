"""Sequential, checkpointed GPU continuation. Original sources are read-only."""
import csv, datetime, hashlib, json, os, shutil, subprocess, sys, threading, time, ctypes
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
sys.path.insert(0,str(BASE/'night_20261028'))
from night_queue import STAR,saved_options,redact,free_memory
GIB=1024**3
def stamp():return datetime.datetime.now().astimezone().isoformat()
def write(p,obj):
    temp=p.with_suffix(p.suffix+'.tmp');temp.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf-8');temp.replace(p)
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()
def read(p,default=None):
    try:return json.loads(p.read_text(encoding='utf-8-sig'))
    except (OSError,ValueError):return default
def refresh():
    try:subprocess.run([sys.executable,str(ROOT/'update_status.py')],capture_output=True,timeout=25,creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:write(ROOT/'dashboard_error.json',{'error':str(e)})
def run_job(j):
    out=ROOT/j['id'];out.mkdir(exist_ok=False)
    source=Path(j['source']).resolve()
    if not source.is_relative_to(BASE):raise ValueError('Source outside authorized campaign')
    if free_memory()<16*GIB:raise RuntimeError('Insufficient free RAM for starting another case')
    if shutil.disk_usage(ROOT).free<10*GIB:raise RuntimeError('Insufficient disk reserve: at least 10 GiB required; expected case footprint below 4 GiB')
    copied=out/'input_copy.sim';shutil.copy2(source,copied)
    source_hash=digest(source)
    if digest(copied)!=source_hash:raise RuntimeError('Source copy mismatch')
    shutil.copy2(ROOT/'ContinueForces.java',out/'ContinueForces.java')
    write(out/'source_identity.json',{'original_source':str(source),'sha256':source_hash,'copied_sha256':digest(copied),'macro_sha256':digest(out/'ContinueForces.java')})
    env=dict(os.environ)
    for key,val in {'OUT':str(out),'DT':j['dt'],'TARGET':j['target'],'INNER':j['inner'],'CELLS':j['cells'],'START':j['start'],'ORDER':j['order'],'BUDGET':j['wall_budget_s']}.items():env['NTNU_STAB_'+key]=str(val)
    started=time.time();soft=False;state='running';resources=[]
    with (out/'star.log').open('x',encoding='utf-8') as log:
        p=subprocess.Popen([str(STAR),*saved_options(1),'-gpgpu','auto:1','-batch',str(out/'ContinueForces.java'),str(copied)],cwd=str(out),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
        write(out/'process.json',{'launcher_pid':p.pid,'started_at':stamp(),'start_unix':started,'source':str(copied),'gpu':True,'workers':1})
        def drain():
            for line in p.stdout:log.write(redact(line));log.flush()
        reader=threading.Thread(target=drain,daemon=True);reader.start()
        last=0
        while p.poll() is None:
            free=free_memory()
            if free<8*GIB or shutil.disk_usage(ROOT).free<4*GIB or time.time()-started>j['wall_budget_s']+600:
                (out/'STOP').touch();soft=True
            if free<4*GIB or time.time()-started>j['wall_budget_s']+1200:
                state='emergency_stop_owned_process'
                subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW);break
            if time.time()-last>20:
                resources.append({'time':stamp(),'free_GiB':free/GIB,'elapsed_s':time.time()-started})
                write(out/'resources.json',resources)
                write(ROOT/'queue_state.json',{'status':'running','active':j['id'],'updated_at':stamp(),'soft_stop':soft})
                refresh();last=time.time()
            time.sleep(3)
        rc=p.wait();reader.join(15)
    completed=read(out/'completed.json',{})
    if state=='running':state='completed' if rc==0 and completed.get('status')=='target_reached' else 'needs_review'
    result={'id':j['id'],'status':state,'returncode':rc,'elapsed_wall_s':time.time()-started,'completed':completed,'original_unchanged':digest(source)==source_hash}
    write(out/'controller_result.json',result);return result
def main():
    jobs=read(ROOT/'queue.json')
    lock=ROOT/'queue.lock'
    with lock.open('x',encoding='utf-8') as f:json.dump({'pid':os.getpid(),'created_at':stamp()},f)
    write(ROOT/'controller_process.json',{'pid':os.getpid(),'created_at':stamp()})
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    results=[]
    try:
        for j in jobs:
            if (ROOT/'STOP_ALL').exists():break
            prior=read(ROOT/j['id']/'controller_result.json')
            if prior and prior.get('status')=='completed':results.append(prior);continue
            if (ROOT/j['id']).exists():raise RuntimeError('Unfinished existing attempt; inspect checkpoint and create new job ID')
            r=run_job(j);results.append(r);write(ROOT/'queue_results.json',results)
            if r['status']!='completed':break
        write(ROOT/'queue_state.json',{'status':'finished' if len(results)==len(jobs) and all(r['status']=='completed' for r in results) else 'needs_review','updated_at':stamp(),'results':results})
    except Exception as e:
        write(ROOT/'queue_state.json',{'status':'controller_error','updated_at':stamp(),'error':str(e),'results':results});raise
    finally:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        refresh()
        if lock.exists():lock.unlink()
if __name__=='__main__':main()
