"""Unique CPU1/noGPU bounded three-step disposable W01a ramp API audit. Maximum three guarded CFD time steps."""
import os,sys,json,shutil,subprocess,threading,time,hashlib,datetime
from pathlib import Path
import run_until_settled as e
R=Path(__file__).resolve().parent;W=Path("E:/ntnu/quasi2d_waves_20261029")
SOURCE=W/"W01a_W20L4_M10_calm_start_r1/final.sim"
A=W/"W01a_inlet_ramp_step_audit_r2";LOCK=W/"preparation.lock"
MACRO=R/"AuditW01aInletRampStepR2.java"
JAVAC=Path("C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe")
EXT=Path("E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/star/lib/java/platform/modules/ext")
def stamp():return datetime.datetime.now().astimezone().isoformat()
def digest(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
 return h.hexdigest()
def state(status,**kw):e.write(R/"w01a_inlet_ramp_step_audit_state.json",dict(status=status,updated_at=stamp(),controller_pid=os.getpid(),directory=str(A),workers=1,gpu=False,maximum_flow_steps=3,**kw))
def main():
 if A.exists():raise RuntimeError("Unique audit attempt already exists; preserve it")
 if LOCK.exists():raise RuntimeError("CPU preparation lock exists; do not race")
 if not SOURCE.is_file():raise RuntimeError("Computed source checkpoint missing")
 completed=e.read(SOURCE.parent/"completed.json",{})
 if completed.get("status")!="stopped_by_marker" or abs(completed.get("time_s",0)-.587)>1e-10:raise RuntimeError("Source must be completed W01a t.587")
 if e.free_memory()<24*1024**3 or shutil.disk_usage(W).free<8*1024**3:raise RuntimeError("Insufficient resources for CPU1 file audit")
 with LOCK.open("x") as f:json.dump(dict(pid=os.getpid(),purpose="W01a bounded three-step CPU1 inlet-ramp API and native-vorticity audit; noGPU/max3flowsteps",case=A.name),f)
 try:
  A.mkdir();shutil.copy2(MACRO,A/MACRO.name);(A/"compiled").mkdir()
  text=(A/MACRO.name).read_text()
  for forbidden in ["initializeSolution(", "clearSolution(", "clearSolutionWithoutMeshReset(", ".run("]:
   if forbidden in text:raise RuntimeError("Forbidden flow/reset call in bounded three-step macro: "+forbidden)
  state("offline_compiling")
  q=subprocess.run([str(JAVAC),"-proc:none","--release","21","-cp",str(EXT/"*"),"-d",str(A/"compiled"),str(A/MACRO.name)],capture_output=True,text=True,encoding="utf-8",errors="replace",creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS,timeout=180)
  (A/"compile.log").write_text(e.redact(q.stdout+"\n"+q.stderr))
  if q.returncode:raise RuntimeError("Offline compilation failed; no STAR launched")
  srcsha=digest(SOURCE);shutil.copy2(SOURCE,A/"input.sim")
  if digest(A/"input.sim")!=srcsha:raise RuntimeError("Source-copy hash mismatch")
  e.write(A/"source_identity.json",dict(source=str(SOURCE),source_sha256=srcsha,source_case=SOURCE.parent.name,physical_time_s=.587,computed_checkpoint=True,copy_sha256=srcsha,maximum_flow_steps=3,initialization_allowed=False,compiled_before_STAR_launch=True,macro_sha256=digest(A/MACRO.name)))
  if e.free_memory()<24*1024**3:raise RuntimeError("Memory no longer sufficient")
  env=os.environ.copy();env["NTNU_W01A_RAMP_AUDIT_OUT"]=A.as_posix()
  state("bounded_step_STAR_audit")
  with (A/"star.log").open("x",encoding="utf-8") as log:
   p=subprocess.Popen([str(e.STAR),*e.saved_options(1),"-batch",str(A/MACRO.name),str(A/"input.sim")],cwd=str(A),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
   e.write(A/"process.json",dict(launcher_pid=p.pid,workers=1,gpu=False,maximum_flow_steps=3,started_at=stamp()))
   def drain():
    for line in p.stdout:log.write(e.redact(line));log.flush()
   th=threading.Thread(target=drain,daemon=True);th.start()
   try:rc=p.wait(timeout=1200)
   except subprocess.TimeoutExpired:
    subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
    raise RuntimeError("Owned bounded three-step audit timeout; attempt preserved")
   th.join(10)
  unchanged=digest(SOURCE)==srcsha and digest(A/"input.sim")==srcsha
  result=e.read(A/"audit.json",{})
  result.update(controller_finished_at=stamp(),returncode=rc,source_unchanged=unchanged,source=str(SOURCE),source_sha256=srcsha,directory=str(A))
  if (A/"physical_fields_before.csv").is_file() and (A/"physical_fields.csv").is_file():
   result["physical_field_csv_sha256_before"]=digest(A/"physical_fields_before.csv");result["physical_field_csv_sha256_after"]=digest(A/"physical_fields.csv")
   result["physical_field_csv_bitwise_equal"]=result["physical_field_csv_sha256_before"]==result["physical_field_csv_sha256_after"]
  e.write(A/"controller_result.json",result);e.write(R/"w01a_inlet_ramp_step_audit_result.json",result)
  if rc or not unchanged or not result.get("configuration_fingerprint_unchanged") or result.get("flow_steps")!=3:raise RuntimeError("Zero-step audit requires review")
  state("completed_bounded_step_audit",source_unchanged=True,ramp_expression_tests_pass=result.get("ramp_expression_tests_pass"),vorticity_found=result.get("native_vorticity",{}).get("found"),field_csv_bitwise_equal=result.get("physical_field_csv_bitwise_equal"))
 except BaseException as ex:
  state("needs_review",error=str(ex))
  raise
 finally:
  if e.read(LOCK,{}).get("pid")==os.getpid():LOCK.unlink()
if __name__=="__main__":main()
