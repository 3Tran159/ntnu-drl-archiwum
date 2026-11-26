from pathlib import Path
import json,hashlib,shutil,datetime,subprocess,sys,ast
H=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102');R=H.parent
A=R/'checkpoints/RELOCATION_20261103_073441'
now=lambda:datetime.datetime.now().astimezone().isoformat()
def put(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf8')
def sha(p):
 d=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8388608),b''):d.update(b)
 return d.hexdigest()
cs=json.loads((A/'CHECKPOINTS.json').read_text())
assert json.loads((A/'ARCHIVE_PROGRESS.json').read_text())['status']=='archive_copy_verified'
for c in cs:assert (A/c['archive']).stat().st_size==c['bytes'] and sha(A/c['archive'])==c['sha256']
resume=r'''from pathlib import Path
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
ps="Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'starccm|starserver|mpiexec|smpd|pmi_proxy' -or ($_.Name -match '^python' -and $_.CommandLine -match 'night_queue.py') } | Select-Object ProcessId,Name | ConvertTo-Json -Compress"
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
print("Opened recovery copy only. Do not initialize/remesh. Follow HOME_RESUME_INSTRUCTIONS.md.")
'''
rp=H/'tools/resume_relocation.py';rp.write_text(resume,encoding='utf8');ast.parse(resume)
py=Path(r'C:\Users\ThinkPad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
(R/'RESUME_CFD.cmd').write_text('@echo off\n"'+str(py)+'" -X utf8 "'+str(rp)+'" --user-resume\nif errorlevel 1 exit /b 1\n',encoding='ascii')
v=subprocess.run([str(py),'-X','utf8',str(rp),'--check-only'],capture_output=True,text=True,timeout=45)
assert v.returncode==0,v.stderr
put(A/'RESUME_SCRIPT_VALIDATION.json',dict(at=now(),python_ast='passed',check_only=json.loads(v.stdout),resume_executed=False,native_reopen_performed=False))
science=dict(at=now(),status='PAUSED_FOR_RELOCATION',scientific_approved=False,training_eligible=False,
last_decision='C0 top-boundary diagnostic positive; matched B0 complete, full residual/far-field review pending. Explicit user pause.',
original_rejected_difference=dict(CL_percent=14.6869,CD_percent=-9.56915),
C0=dict(time_s=.65,iteration=11560,CL_mean25=.32561948776312,CD_mean25=.0072459371243424,Mh_mean25=-12.040069616324,pabs_min_Pa=30097.6945773,mass_relative=2.98365817057e-9),
B0=dict(time_s=.5,iteration=6250,CL_mean25=.32661098046588,CD_mean25=.007191107030274,Mh_mean25=-12.160189508284),
current_difference_percent=dict(CL=100*(.32561948776312/.32661098046588-1),CD=100*(.0072459371243424/.007191107030274-1)),
confirmed=['Original Cp/head spikes near hinge and y+~571 rejected.','isEmpty() audit invalid; replaced with native midspan full Overset extraction.',
'More inner iterations and interpolation alone did not cure original case.',
'Tight numerical cage removed near-wall spikes; physical geometry retained.',
'Top backflow EXTRAPOLATED strongly improved C0 residual plateau and top pressure spikes. Matched B0 completed.'],
not_established=['Wall-distance defect not confirmed by nearest-wall audit.','Full B0 residual review pending.','Far-field velocity memory remains.','Matched original A baseline and motion/grid/time validation pending.'],
next_test='After explicit resume: verify C0 saved t0.650 fields; finish B0 residual review, then bounded25-step C0 continuation to0.700s with unchanged numerics and full pressure/Overset guards. No angles.',
parameters=dict(version='2606.0002 build21.04.009-R8',CPU=8,GPU=False,MPI='ms',U=18,rho=1000,mu=.001,Re=21420000,chord_m=1.19,span_m=.02,hinge_xyz=[.952,.02,.02128173276776986],hinge_x_c=.8,gap_m=.0025,delta=0,model='single phase URANS SST AllYplus',dt=.002,inner=40,URF=[.8,.2],schemes='SECOND_ORDER',top_backflow='EXTRAPOLATED',pref_Pa=101325,water_C=20,vapor_Pa=2339.2147668,required_cavitation_margin_Pa=10000),
C0_mesh=dict(cells=333939,active=255350,inactive=77108,acceptors=1481,errors=0,difficult=0,min_volume=9.128750119e-12,min_quality=.061048186,interpolation='DISTANCE',flux_correction=True,prism_targets=[48,24],collapsed_faces=630,negative_volume=False,formal_validation=False),
unsaved_solver_progress=None,native_reopen_verified=False)
put(A/'SCIENTIFIC_HANDOVER.json',science);put(H/'WORK_CURRENT_REVIEW.json',science)
manual=f"""# HOME RESUME — relocation pause 2026-11-03
PAUSED. Resume only on explicit user instruction. No new angles,waves,W04 or DRL.

## Checkpoints
C0 Overset: {A/cs[0]['archive']}
Saved time0.6500000000000005s; native iteration11560; dt0.002s;40 inner.
Bytes{cs[0]['bytes']}; SHA256 {cs[0]['sha256']}
B0 fixed: {A/cs[1]['archive']}
Saved time0.500s; native iteration6250;dt0.002s;40 inner.
Bytes{cs[1]['bytes']}; SHA256 {cs[1]['sha256']}
Both native saves complete,STAR exit0; source/archive SHA verified.
Native reopening not performed during relocation. No unsaved solver progress identified.
Cases remain scientifically UNVALIDATED.

## Exact restart procedure — only after user resumes
Run F:\\ntnu\\flap_control\\RESUME_CFD.cmd
Validated in --check-only mode; actual resume NOT executed.
It verifies C0 SHA,creates a fresh working copy under
{H}\\cases\\SP_C_split0_overset\\relocation_reopen_TIMESTAMP
and opens it in STAR2606.0002 build21.04.009-R8,8CPU,MPI ms,CPU binding off,noGPU,
using the approved existing campaign license without printing its key.
It opens the saved case WITHOUT pressing Run,resetting fields/time or meshing.
Queue and angle guards stay paused. No Windows autostart is installed.

Work must verify t0.650s,11560 iterations,333939 cells,fields,motions and reports.
Do not initialize,clear solution,reset time or remesh.
Keep dt0.002s,40 inner,URF0.8/0.2,second-order schemes,top EXTRAPOLATED.
Finish matched B0 residual review. Then prepare a bounded25-step C0 continuation
to0.700s with full native Overset/pressure guards and a NEW checkpoint.
Do not blindly replay C0URANSTopDirection.java: its source points to an older case.
Keep STOP_OWNED_CFD.json and PAUSED_FOR_HOME.json until Work configures reviewed
continuation after user instruction. Controller exit requested;accept_new_jobs=false.
C0_bias_explained_and_approved=false; no next angles or automatic queue restart.

## Scientific handover
Original C0 +14.7%CL/-9.6%CD was rejected. Cp/head artifacts near hinge,
local y+~571; more inner iterations/interpolation alone did not fix it.
isEmpty() was invalid for auditing; corrected full native plane extraction used.
Nearest-wall audit did not confirm wall distance as primary cause.
Tight numerical cage removed near-wall spikes without changing physical foil geometry.
Top backflow BOUNDARY_NORMAL to EXTRAPOLATED strongly improved C0 residuals/pressure.
Matched B0 completed. Tail25:
C0 CL0.32561949,CD0.00724594,Mh-12.04007Nm.
B0 CL0.32661098,CD0.00719111,Mh-12.16019Nm.
Current C/B difference CL-0.304%,CD+0.762%; not final validation.
Far-field velocity memory,B0 residual review,matched original A baseline,
mesh/time uncertainty and actual motion on new tight mesh remain pending.
C01 VOF CL0.3156595/CD0.00700232 retained; no forced single-phase match.
Complete parameter/mesh/scientific record: SCIENTIFIC_HANDOVER.json.

## Archive and dependencies
{A}
ARCHIVE_MANIFEST.json:3526 files,14,605,150,347 bytes,all1253CSV plus geometry,
macros,tools,logs,diagnostics and queue snapshots. No .simh found.
Older .sim files remain untouched under campaign. Python deps cache remains installed.
Copied logs redact license key; approved original licensing log stays in place.
External warm table:
{H}\\initialization\\c0_tight_from_flux1850\\warm_fields.csv
Geometry under {H}\\geometry,also copied to archive campaign/.
Final current scripts/status: final_state/. FINAL_STATE_MANIFEST.json has hashes.
No modifications to C01,W01,W03,PRE_W04 or their queues.
"""
(R/'HOME_RESUME_INSTRUCTIONS.md').write_text(manual,encoding='utf8');(A/'HOME_RESUME_INSTRUCTIONS.md').write_text(manual,encoding='utf8')
for name in ['NIGHT_STATUS.json','NIGHT_DASHBOARD.json']:
 p=H/name
 try:d=json.loads(p.read_text())
 except Exception:d={}
 d.update(at=now(),solver_state='STOPPED',queue_state='PAUSED_FOR_RELOCATION',active=None,current_case=None,physical_time_s=.65,checkpoints=cs,scientific_approved=False,work_current_review=science,next_action='WAIT_FOR_EXPLICIT_USER_RESUME')
 put(p,d)
p=H/'NIGHT_QUEUE_STATE.json';d=json.loads(p.read_text());d.update(active=None,queue_state='PAUSED_FOR_RELOCATION',paused_at=now(),relocation_archive=str(A));put(p,d)
p=H/'NIGHT_QUEUE.json';d=json.loads(p.read_text());d.update(controller_exit_requested=True,accept_new_jobs=False);d['scientific_gates']['C0_bias_explained_and_approved']=False;put(p,d)
(H/'NIGHT_DASHBOARD.html').write_text('<!doctype html><meta charset="utf-8"><title>NTNU CFD paused</title><h1>PAUSED FOR RELOCATION</h1><p>STAR STOPPED. Queue blocked. Explicit user resume required.</p><p>C0 checkpoint:0.650s; B0:0.500s. SHA256 verified.</p><p>C0 is NOT validated. Current matched CL difference-0.304%,CD+0.762%. Residual/far-field review pending. Nonzero angles blocked.</p>',encoding='utf8')
with (H/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=now(),event='relocation_archive_verified',archive=str(A),solver='STOPPED',scientific_approved=False))+'\n')
extras=[]
for src in [R/'RESUME_CFD.cmd',R/'HOME_RESUME_INSTRUCTIONS.md',rp,H/'WORK_CURRENT_REVIEW.json',H/'NIGHT_QUEUE.json',H/'NIGHT_QUEUE_STATE.json',H/'NIGHT_STATUS.json',H/'NIGHT_DASHBOARD.json',H/'NIGHT_DASHBOARD.html',H/'NIGHT_DECISIONS.jsonl']:
 dst=A/'final_state'/src.name;dst.parent.mkdir(exist_ok=True);shutil.copy2(src,dst);assert sha(dst)==sha(src)
 extras.append(dict(source=str(src),archive=str(dst.relative_to(A)),bytes=dst.stat().st_size,sha256=sha(dst)))
put(A/'FINAL_STATE_MANIFEST.json',extras)
print(json.dumps(dict(status='PAUSE_DOCUMENTATION_READY',at=now(),resume_executed=False,check_only=json.loads(v.stdout))))
