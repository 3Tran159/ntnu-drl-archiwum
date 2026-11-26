import sys,json,time,threading,subprocess,shutil
from pathlib import Path
root=Path(r"F:\ntnu\mesh_screening_20261028")
out=root/"quasi2d_012_20261029"
sys.path.insert(0,str(root/"night_20261028"))
from night_queue import STAR,saved_options,redact,free_memory
job=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
source=Path(job["source"]);macro=Path(job["macro"]);logfile=Path(job["log"])
assert not logfile.exists()
assert free_memory()>8*1024**3
start=time.time()
with logfile.open("x",encoding="utf-8") as log:
 p=subprocess.Popen([str(STAR),*saved_options(job.get("np",8)),"-batch",str(macro),str(source)],cwd=str(out),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace")
 logfile.with_suffix(".pid.json").write_text(json.dumps({"pid":p.pid,"start_unix":start,"np":job.get("np",8)}))
 def drain():
  for line in p.stdout:log.write(redact(line));log.flush()
 t=threading.Thread(target=drain,daemon=True);t.start()
 while p.poll() is None:
  if time.time()-start>job.get("timeout_s",1800) or free_memory()<4*1024**3:
   subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],capture_output=True);break
  time.sleep(2)
 rc=p.wait();t.join(10)
 logfile.with_suffix(".exit.json").write_text(json.dumps({"returncode":rc,"wall_s":time.time()-start}))
print(json.dumps({"returncode":rc,"log":str(logfile)}))
