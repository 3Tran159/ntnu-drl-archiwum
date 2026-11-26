from pathlib import Path
import json,hashlib,shutil,os,datetime
H=Path(r"F:\ntnu\flap_control\hydro_validation_2606_20261102")
ROOT=H.parent
D=ROOT/"independent_cfd_diagnostics"/"C0_speed_down_20261103"
exp="C0_SPEED_DOWN_20261103"
jid="C0_SPEED_DOWN_20261103_SMOKE"
s=json.loads((H/"NIGHT_QUEUE_STATE.json").read_text(encoding="utf-8"))
cfg=json.loads((H/"NIGHT_QUEUE.json").read_text(encoding="utf-8"))
if s.get("active") is not None:raise RuntimeError("Owned solver active; refusing install")
if cfg.get("accept_new_jobs") is not False:raise RuntimeError("Queue must be on HOLD before installing")
pending=[j["id"] for j in cfg["jobs"] if j["id"] not in s["jobs"] and not j.get("disabled")]
if pending:raise RuntimeError("Other pending jobs: "+str(pending))
failure=s.get("failure_hold")
if failure!="SPEED_SWEEP_PLUS2_20261103_SMOKE":raise RuntimeError("Unexpected HOLD state: "+str(failure))
if exp in cfg.get("experiment_authorizations",{}) or any(j["id"]==jid for j in cfg["jobs"]):raise RuntimeError("Diagnostic already registered")
src=H/"cases/SP_C_split0_overset/relocation_reopen_20261103_082325/C0_recovered_t065.sim"
if not src.is_file():raise FileNotFoundError(src)
macro_src=D/"C0SpeedDownSmoke.java";macro_dest=H/"macros/C0SpeedDownSmoke.java"
if not macro_src.is_file() or macro_dest.exists():raise RuntimeError("Candidate missing or macro collision")
audit=json.loads((D/"PRELAUNCH_AUDIT.json").read_text())
if not all(audit["checks"].values()):raise RuntimeError("Prelaunch checks failed")
if not (D/"compiled/macro/C0SpeedDownSmoke.class").is_file():raise RuntimeError("Missing compiled macro")
def sha(p):
    with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
macrosha=sha(macro_src);srcsha=sha(src)
files={}
for name in ["night_queue.py","night_native.py","ramp_authorization.py"]:
    files[name]=(H/"tools"/name).read_text(encoding="utf-8")
def patch(t,a,b,label):
    if t.count(a)!=1:raise RuntimeError(f"{label}: expected one match, found {t.count(a)}")
    return t.replace(a,b)
n=files["night_queue.py"]
n=patch(n,
"ALLOWED.update(['SpeedSweepPlus2Smoke.java','SpeedSweepPlus2Run.java'])",
"ALLOWED.update(['SpeedSweepPlus2Smoke.java','SpeedSweepPlus2Run.java'])\nALLOWED.add('C0SpeedDownSmoke.java')","queue allowed")
key="if receipt['macro'] in ['SpeedSweepPlus2Smoke.java','SpeedSweepPlus2Run.java']:return H/'cases/SP_C_split0_overset'/('speed_plus2_'+receipt['run_id'])"
n=patch(n,key,
"if receipt['macro']=='C0SpeedDownSmoke.java':return H.parent/'independent_cfd_diagnostics/C0_speed_down_20261103'/('run_'+receipt['run_id'])\n "+key,
"queue output")
n=patch(n,"status.get('status') in ['speed_smoke_passed'","status.get('status') in ['speed_down_smoke_passed_not_scientific_validation','speed_smoke_passed'","queue status")
files["night_queue.py"]=n
n=files["night_native.py"]
n=patch(n,"allowed['SpeedSweepPlus2Run.java']=8","allowed['SpeedSweepPlus2Run.java']=8\nallowed['C0SpeedDownSmoke.java']=8","native allowed")
files["night_native.py"]=n
n=files["ramp_authorization.py"]
n=patch(n,"[EXPERIMENT,'SPEED_SWEEP_PLUS2_20261103']",
"[EXPERIMENT,'SPEED_SWEEP_PLUS2_20261103','C0_SPEED_DOWN_20261103']","hold approval")
files["ramp_authorization.py"]=n
evidence=D/"USER_AUTHORIZATION.json"
content=dict(approved_by_user=True,source="Explicit user request 'okej to jazda' to diagnose and safely proceed without Work",
experiment_id=exp,previous_blocked_job=failure,previous_case_remains_failed=True,approved_job_ids=[jid],
scope="20-step diagnostic only, start existing C0 t=.65 iter=11560, flap 0deg; reduce U18→10 by 0.4s quintic; 8 CPU, no GPU; guarded pressure/mass/turbulence/mesh; no other jobs; no automatic speed sweep",
created_at=datetime.datetime.now().astimezone().isoformat(),not_full_sweep_approval=True)
job=dict(id=jid,kind="c0_speeddown",experiment_id=exp,approved=True,macro="C0SpeedDownSmoke.java",
macro_sha256=macrosha,input=str(src),input_sha256=srcsha,initial_time_s=.65,cpu_processes=8,angle_deg=0,
progress_timeout_s=900,maximum_runtime_s=1800,runtime_guards=dict(minimum_absolute_pressure_Pa=12339.214766776897,
maximum_mass_imbalance_relative=1e-4,maximum_omega_floor_cells=0,maximum_k_floor_cells=0,
maximum_overset_error_cells=0,maximum_turbulent_viscosity_ratio=99999))
cfg["jobs"].append(job)
cfg.setdefault("experiment_authorizations",{})[exp]=dict(approved=True,previous_blocked_job=failure,evidence=str(evidence))
cfg["accept_new_jobs"]=False
cfg["controller_exit_requested"]=False
backup=D/"backup_before_queue_integration";backup.mkdir(exist_ok=False)
for name in files:shutil.copy2(H/"tools"/name,backup/name)
shutil.copy2(H/"NIGHT_QUEUE.json",backup/"NIGHT_QUEUE.json")
# All preconditions and source replacements checked before any mutation.
evidence.write_text(json.dumps(content,indent=2),encoding="utf-8")
shutil.copy2(macro_src,macro_dest)
for name,body in files.items():
    dest=H/"tools"/name; tmp=dest.with_suffix(dest.suffix+".manual_tmp")
    tmp.write_text(body,encoding="utf-8");os.replace(tmp,dest)
tmp=(H/"NIGHT_QUEUE.json").with_suffix(".json.manual_tmp")
tmp.write_text(json.dumps(cfg,indent=2,ensure_ascii=False),encoding="utf-8");os.replace(tmp,H/"NIGHT_QUEUE.json")
record=dict(status="INSTALLED_HOLD_NOT_LAUNCHED",job=jid,
macro_sha256=macrosha,source_checkpoint=str(src),source_sha256=srcsha,
source_bytes=src.stat().st_size,failure_hold=failure,backup=str(backup),
controller_must_restart_to_reload_python=True,job_registered=True,accept_new_jobs=False)
(D/"QUEUE_INTEGRATION.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
print(json.dumps(record,indent=2))
