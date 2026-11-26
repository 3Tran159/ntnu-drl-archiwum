from pathlib import Path
import sys,json,hashlib,shutil,datetime,subprocess,os,re
H=Path(r"F:\ntnu\flap_control\hydro_validation_2606_20261102");R=H.parent
A=R/"checkpoints/RELOCATION_20261103_073441"
exe=Path(r"E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\win64\clang20.1vc14.2-r8\lib\starccm+.exe")
mode=sys.argv[1] if len(sys.argv)>1 else "--check-only"
assert mode in ("--check-only","--user-resume")
m=json.loads((A/"CHECKPOINTS.json").read_text())[0];source=A/m["archive"]
def sha(p):
 d=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(8388608),b""):d.update(b)
 return d.hexdigest()
assert source.stat().st_size==m["bytes"] and sha(source)==m["sha256"]
assert exe.is_file() and (R/"PAUSED_FOR_HOME.json").is_file() and (R/"STOP_OWNED_CFD.json").is_file()
q=json.loads((H/"NIGHT_QUEUE.json").read_text())
assert not q["scientific_gates"]["C0_bias_explained_and_approved"] and q.get("controller_exit_requested") and q.get("accept_new_jobs") is False
approval=json.loads((H/"audit/LICENSE_USE_APPROVAL.json").read_text());assert approval.get("approved") is True
lic=Path(approval["source_log"]).resolve();assert lic==H/"runs/RunURANSFromSteady_SP_C_20261102_203650.log" and lic.is_file()
if mode=="--check-only":
 print(json.dumps(dict(status="CHECK_ONLY_PASSED",checkpoint=str(source),sha256=m["sha256"],time_s=.65,iteration=11560,cpu=8,gpu=False,solver_started=False,queue_stays_paused=True)));sys.exit(0)
ps="Get-CimInstance Win32_Process | Where-Object { ($_.Name -match 'starccm|starserver|mpiexec|smpd|pmi_proxy|^python') -and $_.CommandLine -match 'F:\\\\ntnu\\\\flap_control' -and $_.CommandLine -notmatch 'resume_relocation.py' } | Select-Object ProcessId,Name | ConvertTo-Json -Compress"
r=subprocess.run(["powershell","-NoProfile","-Command",ps],capture_output=True,text=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert not r.stdout.strip(),"Solver/queue exists: inspect before resume"
assert shutil.disk_usage(H).free>15*1024**3
out=H/"cases/SP_C_split0_overset"/("relocation_reopen_"+datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
out.mkdir(exist_ok=False);dst=out/"C0_recovered_t065.sim";shutil.copy2(source,dst);assert sha(dst)==m["sha256"]
env=dict(os.environ)
with lic.open(encoding="utf8") as f:line=f.readline()
assert line.startswith("Starting local server: starserver.bat -power ")
for flag,key in [("-podkey","LM_PROJECT"),("-licpath","CDLMD_LICENSE_FILE")]:
 match=re.search(re.escape(flag)+r'\s+(\"[^\"]+\"|\S+)',line);assert match
 env[key]=match.group(1).strip('"')
with (out/"reopen.log").open("w",encoding="utf8") as f:
 p=subprocess.Popen([str(exe),"-power","-np","8","-mpi","ms","-cpubind","off",str(dst)],stdout=f,stderr=subprocess.STDOUT,cwd=out,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
v=dict(pid=p.pid,case=str(dst),cpu=8,gpu=False,mpi="ms",solver_auto_run=False,queue_stays_paused=True)
(out/"reopen_receipt.json").write_text(json.dumps(v,indent=2),encoding="utf8")
print(json.dumps(v,indent=2))
print("Recovery process launched; native loading still requires verification. Do not initialize/remesh.",flush=True)
rc=p.wait()
print("STAR launcher exited with code "+str(rc),flush=True)
