"""Explicit-launch CPU1 zero-step audit of preserved R4 checkpoint report definitions."""
import os,sys,time,json,shutil,subprocess,threading,csv
from pathlib import Path
R=Path(__file__).resolve().parent
W=Path("E:/ntnu/quasi2d_waves_20261029")
C=W/"W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4"
A=W/"W20_H24_X4_R4_t0p750_report_definition_audit_r1"
SOURCE=C/"checkpoint_t0.750.sim"
MACRO="AuditWaveReportDefinitionR1.java"
import run_until_settled as e
own=R/"wave_report_definition_audit_r1.lock"
cpu=R/"queue.lock" # CPU1 diagnostic reservation; preserve separate M10 CPU2 preparation owner
def state(status,**kw):
 e.write(R/"wave_report_definition_audit_state.json",dict(status=status,updated_at=e.stamp(),controller_pid=os.getpid(),directory=str(A),source=str(SOURCE),workers=1,gpu=False,scope="Zero-step report-definition diagnostic; no physics or time changes",**kw))
def main():
 if "--run" not in sys.argv:raise SystemExit("Prepared only. Parent must inspect and explicitly launch with --run.")
 if own.exists():raise RuntimeError("Existing report audit owner; inspect before recovery")
 if not SOURCE.is_file():raise RuntimeError("Required preserved R4 t0.750 checkpoint missing")
 if A.exists():raise RuntimeError("Audit attempt exists; preserve it and use a new ID")
 with own.open("x") as f:json.dump(dict(pid=os.getpid(),purpose="Zero-step report-definition audit"),f)
 claimed=False;p=None
 try:
  if cpu.exists():raise RuntimeError("Existing campaign reservation; inspect before launch")
  prep=e.read(W/"preparation.lock",{})
  if prep and prep.get("purpose")!="Wave free-surface M10 variant CPU2 build; no GPU":raise RuntimeError("Other CPU preparation owner; inspect resources")
  state("reserving_idle_campaign_slot_for_CPU1_audit")
  if (R/"STOP_ALL").exists():state("stopped_by_marker");return
  if e.free_memory()<24*1024**3 or shutil.disk_usage(W).free<8*1024**3:raise RuntimeError("Insufficient resources for CPU1 audit")
  with cpu.open("x") as f:json.dump(dict(pid=os.getpid(),purpose="Zero-step wave report definitions",case=A.name),f)
  claimed=True
  A.mkdir()
  digest=e.digest(SOURCE)
  shutil.copy2(SOURCE,A/"input.sim");shutil.copy2(R/MACRO,A/MACRO)
  if e.digest(A/"input.sim")!=digest:raise RuntimeError("Checkpoint copy mismatch")
  e.write(A/"source_identity.json",dict(source=str(SOURCE),source_sha256=digest,copy_sha256=digest,expected_time_s=.75,scope="Preserved source; disposable CPU-only audit with zero solver steps"))
  with (C/"history.csv").open(newline="") as f:rows=list(csv.DictReader(f))
  nearest=min(rows,key=lambda x:abs(float(x["time_s"])-.75))
  if abs(float(nearest["time_s"])-.75)>1e-7:raise RuntimeError("Saved-history reference at0.750s missing")
  with (C/"boundary_flux.csv").open(newline="") as f:flux=[x for x in csv.DictReader(f) if abs(float(x["time_s"])-.75)<1e-7]
  e.write(A/"saved_history_reference.json",dict(history=nearest,boundary_flux=flux,note="Compare loaded report values to these original-step values; cache/reconstruction differences remain diagnostic, not a replacement history"))
  env=dict(os.environ,NTNU_WAVE_REPORT_AUDIT_OUT=str(A))
  state("auditing_saved_reports_CPU")
  with (A/"star.log").open("x",encoding="utf-8") as log:
   p=subprocess.Popen([str(e.STAR),*e.saved_options(1),"-batch",str(A/MACRO),str(A/"input.sim")],cwd=str(A),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
   e.write(A/"process.json",dict(launcher_pid=p.pid,workers=1,gpu=False))
   def drain():
    for line in p.stdout:log.write(e.redact(line));log.flush()
   th=threading.Thread(target=drain,daemon=True);th.start()
   started=time.time()
   while p.poll() is None:
    if time.time()-started>900:
     subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
     raise RuntimeError("Owned zero-step audit exceeded900s")
    time.sleep(3)
   rc=p.wait();th.join(10)
  preserved=e.digest(SOURCE)==digest and e.digest(A/"input.sim")==digest
  audit=e.read(A/"audit.json",{})
  result=dict(returncode=rc,source_unchanged=preserved,audit=audit)
  e.write(A/"controller_result.json",result)
  if rc or not preserved or audit.get("steps_taken")!=0 or abs(audit.get("time_before_s",-1)-.75)>1e-8 or abs(audit.get("time_after_s",-1)-.75)>1e-8:
   raise RuntimeError("Zero-step report audit failed; inspect preserved outputs")
  state("report_definitions_ready",result=result,next="Compare existing/default and independent unsmoothed reports, then inspect temporal/source settings before revising any diagnostic")
 except BaseException as ex:
  if p is not None and p.poll() is None:
   subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
  state("needs_review",error=str(ex));raise
 finally:
  if claimed and e.read(cpu,{}).get("pid")==os.getpid():cpu.unlink()
  if e.read(own,{}).get("pid")==os.getpid():own.unlink()
if __name__=="__main__":main()
