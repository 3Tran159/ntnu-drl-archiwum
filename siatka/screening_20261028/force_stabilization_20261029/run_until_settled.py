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
    # Readers on Windows may briefly hold the destination; never share a staging file across processes.
    temp=p.with_name(p.name+'.'+str(os.getpid())+'.tmp')
    temp.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf-8')
    for attempt in range(50):
        try:
            temp.replace(p)
            return
        except PermissionError:
            if attempt==49: raise
            time.sleep(.1)
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
    out=ROOT/j['id']
    storage=Path('E:/ntnu/mesh_stabilization_20261029')/j['id']
    storage.parent.mkdir(parents=True,exist_ok=True)
    storage.mkdir(exist_ok=False)
    if out.exists():raise RuntimeError('Output already exists')
    cmd="New-Item -ItemType Junction -Path '"+str(out)+"' -Target '"+str(storage)+"' | Out-Null"
    subprocess.run(['powershell','-NoProfile','-Command',cmd],check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
    write(out/'storage.json',{'physical_directory':str(storage),'dashboard_link':str(out)})
    source=Path(j['source']).resolve()
    if not (source.is_relative_to(BASE) or source.is_relative_to(Path('E:/ntnu/mesh_stabilization_20261029')) or source.is_relative_to(Path('E:/ntnu/mesh_builds_20261029'))):raise ValueError('Source outside authorized campaign')
    if free_memory()<16*GIB:raise RuntimeError('Insufficient free RAM for starting another case')
    if shutil.disk_usage(out).free<10*GIB:raise RuntimeError('Insufficient disk reserve: at least 10 GiB required; expected case footprint below 4 GiB')
    copied=out/'input_copy.sim';shutil.copy2(source,copied)
    source_hash=digest(source)
    if digest(copied)!=source_hash:raise RuntimeError('Source copy mismatch')
    shutil.copy2(ROOT/'ContinueUntilSettled.java',out/'ContinueUntilSettled.java')
    write(out/'source_identity.json',{'original_source':str(source),'sha256':source_hash,'copied_sha256':digest(copied),'macro_sha256':digest(out/'ContinueUntilSettled.java')})
    env=dict(os.environ)
    for key,val in {'OUT':str(out),'DT':j['dt'],'TARGET':j['target'],'INNER':j['inner'],'CELLS':j['cells'],'START':j['start'],'ORDER':j['order'],'BUDGET':j['wall_budget_s'],'INIT':str(j.get('initialize',False)).lower(),'PRIOR_HISTORY':j.get('prior_history','')}.items():env['NTNU_STAB_'+key]=str(val)
    started=time.time();soft=False;state='running';resources=[]
    with (out/'star.log').open('x',encoding='utf-8') as log:
        p=subprocess.Popen([str(STAR),*saved_options(1),'-gpgpu','auto:1','-batch',str(out/'ContinueUntilSettled.java'),str(copied)],cwd=str(out),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
        write(out/'process.json',{'launcher_pid':p.pid,'started_at':stamp(),'start_unix':started,'source':str(copied),'gpu':True,'workers':1})
        def drain():
            for line in p.stdout:log.write(redact(line));log.flush()
        reader=threading.Thread(target=drain,daemon=True);reader.start()
        last=0
        while p.poll() is None:
            free=free_memory()
            if free<8*GIB or shutil.disk_usage(out).free<4*GIB or time.time()-started>j['wall_budget_s']+600:
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
    if state=='running':state='completed' if rc==0 and completed.get('status')=='stabilized' else 'needs_review'
    result={'id':j['id'],'status':state,'returncode':rc,'elapsed_wall_s':time.time()-started,'completed':completed,'original_unchanged':digest(source)==source_hash}
    write(out/'controller_result.json',result);return result

def main():
    lock=ROOT/'queue.lock'
    if lock.exists():raise RuntimeError('Another campaign controller still holds the lock')
    with lock.open('x') as f:json.dump({'pid':os.getpid(),'created_at':stamp(),'purpose':'force settling'},f)
    write(ROOT/'controller_process.json',{'pid':os.getpid(),'created_at':stamp(),'mode':'until_settled'})
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    results=[]
    try:
        for mesh,prior in [('M03','M03_FO1_dt1ms_to1p2_r1'),('M02','M02_FO1_dt1ms_to1p2'),('M04',None)]:
            if (ROOT/'STOP_ALL').exists():break
            accepted=read(ROOT/(mesh+'_until_settled_r1')/'acceptance.json',{})
            if accepted.get('status')=='settled':
                results.append({'id':mesh+'_until_settled_r1','status':'completed','acceptance':accepted});continue
            if prior:
                c=read(ROOT/prior/'completed.json',{})
                if c.get('status')!='target_reached':raise RuntimeError('Prior continuation incomplete: '+mesh)
                j={'id':mesh+'_until_settled_r1','source':str(ROOT/prior/'final.sim'),'start':c['time_s'],'prior_history':str(ROOT/prior/'history.csv'),'cells':123256 if mesh=='M03' else 66707}
            else:
                folder=BASE/'quasi2d_012_20261029/M04'
                repair_start=time.time()
                while (ROOT/'M04_REPAIR_IN_PROGRESS').exists():
                    if time.time()-repair_start>3600:raise RuntimeError('M04 repair still incomplete')
                    write(ROOT/'queue_state.json',{'status':'running','active':'M04 mesh repair','updated_at':stamp()});refresh();time.sleep(20)
                start=time.time()
                while not (folder/'mesh_build.exit.json').exists():
                    if time.time()-start>1800:raise RuntimeError('M04 meshing did not finish within expected time')
                    write(ROOT/'queue_state.json',{'status':'running','active':'M04 mesh quality checks','updated_at':stamp()});refresh();time.sleep(20)
                if read(folder/'mesh_build.exit.json',{}).get('returncode')!=0:raise RuntimeError('M04 meshing failed; inspect log')
                env=dict(os.environ,PYTHONIOENCODING='utf-8')
                plotpy=r'E:\Program Files\Siemens\21.02.007-R8\STAR-CCM+21.02.007-R8\star\lib\python\python.exe'
                p=subprocess.run([plotpy,str(folder.parent/'audit_topology.py'),'M04'],capture_output=True,env=env,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
                if p.returncode:raise RuntimeError('M04 topology audit failed: '+p.stderr.decode(errors='replace')[-500:])
                a=read(folder/'topology_audit.json',{});m=read(folder/'measurement.json',{}).get('metrics',{})
                if not a.get('single_layer_topology'):raise RuntimeError('M04 is not one spanwise cell')
                if any(m.get(k,1)!=0 for k in ['NegativeVolumeCells','UnclosedCells','DegeneratedFeCells']):raise RuntimeError('M04 invalid-cell audit failed')
                if m.get('min_cell_quality',0)<.001 or m.get('min_face_validity',0)<.5:raise RuntimeError('M04 mesh quality requires inspection')
                j={'id':'M04_until_settled_r1','source':str(folder/'mesh.sim'),'start':0,'cells':m['cell_count'],'initialize':True}
            j.update({'dt':.001,'inner':20,'order':'FIRST_ORDER','target':10.0,'wall_budget_s':10800,'termination':'two consecutive passing force-settling checks'})
            jobs=read(ROOT/'queue.json',[])
            if not any(k['id']==j['id'] for k in jobs):jobs.append(j);write(ROOT/'queue.json',jobs)
            r=run_job(j);results.append(r);write(ROOT/'settled_queue_results.json',results)
            refresh()
            post=ROOT/'refresh_settled.py'
            if post.exists():
                p=subprocess.run([sys.executable,str(post)],capture_output=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
                if p.returncode:write(ROOT/'settled_post_error.json',{'case':mesh,'error':p.stderr.decode(errors='replace')[-1000:]})
            if r['status']!='completed':break
        write(ROOT/'queue_state.json',{'status':'stabilized' if len(results)==3 and all(r['status']=='completed' for r in results) else 'needs_review','updated_at':stamp(),'results':results})
    except Exception as e:
        write(ROOT/'queue_state.json',{'status':'controller_error','updated_at':stamp(),'error':str(e),'results':results});raise
    finally:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        refresh()
        if lock.exists():lock.unlink()
if __name__=='__main__':main()
