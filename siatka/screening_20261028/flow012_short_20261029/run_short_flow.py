import sys,os,json,time,threading,subprocess,shutil,hashlib,datetime
from pathlib import Path
root=Path(r"F:\ntnu\mesh_screening_20261028")
out=root/"flow012_short_20261029"
sys.path.insert(0,str(root/"night_20261028"))
from night_queue import STAR,saved_options,redact,free_memory
source=root/"coarse012_C003/HF_012_C003_mesh.sim"
copy=out/"working_copy.sim"
assert not (out/"star.log").exists(),"Preserve earlier run"
assert free_memory()>12*1024**3,"Insufficient free RAM"
assert shutil.disk_usage(out).free>5*1024**3,"Insufficient disk space"
shutil.copy2(source,copy)
identity={"original":str(source),"working_copy":str(copy),"sha256":hashlib.sha256(copy.read_bytes()).hexdigest(),"source_unchanged":hashlib.sha256(source.read_bytes()).hexdigest()==hashlib.sha256(copy.read_bytes()).hexdigest()}
(out/"source_identity.json").write_text(json.dumps(identity,indent=2))
started=time.time()
env=dict(os.environ)
with (out/"star.log").open("x",encoding="utf-8") as log:
    p=subprocess.Popen([str(STAR),*saved_options(24),"-batch",str(out/"ShortFlow012.java"),str(copy)],cwd=str(out),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace")
    (out/"process.json").write_text(json.dumps({"launcher_pid":p.pid,"workers_requested":24,"gpu":False,"start_unix":started,"source":str(copy),"project_phase":"2.0"}))
    def drain():
        for line in p.stdout:log.write(redact(line));log.flush()
    th=threading.Thread(target=drain,daemon=True);th.start()
    samples=[];lastbuild=0;status="running"
    while p.poll() is None:
        free=free_memory();samples.append({"unix":time.time(),"free_gib":free/1024**3})
        (out/"resources.json").write_text(json.dumps(samples))
        if free<6*1024**3 or time.time()-started>1500:
            (out/"STOP_ALL").touch();status="resource_or_timeout_stop"
        if time.time()-started>1800:
            subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],capture_output=True)
            status="hard_timeout";break
        if time.time()-lastbuild>10:
            builder=Path(r"F:\ntnu\phase2_012_20261029\build_dashboard.py")
            if builder.exists():
                result=subprocess.run([sys.executable,str(builder)],capture_output=True,text=True)
                if result.returncode:(out/"dashboard_error.log").write_text(result.stderr,encoding="utf-8")
            lastbuild=time.time()
        time.sleep(3)
    rc=p.wait();th.join(timeout=10)
if not (out/"sequence_completed.json").exists():status="macro_failed_or_incomplete"
(out/"run_exit.json").write_text(json.dumps({"returncode":rc,"controller_status":status if status!="running" else "finished","finish_unix":time.time(),"min_free_gib":min(x["free_gib"] for x in samples)}))
builder=Path(r"F:\ntnu\phase2_012_20261029\build_dashboard.py")
if builder.exists():subprocess.run([sys.executable,str(builder)],check=False)
print(json.dumps({"returncode":rc,"output":str(out)}))
