from pathlib import Path
import sys,json
H=Path(r"F:\ntnu\flap_control\hydro_validation_2606_20261102")
sys.path.insert(0,str(H/"tools"))
import night_queue as q
from queue_safety import launch_integrity
from ramp_authorization import blocks
st=q.read(q.STATE);cfg=q.read(q.CFG)
jobs=[j for j in cfg["jobs"] if j["id"] not in st["jobs"] and not j.get("disabled")]
assert len(jobs)==1 and jobs[0]["id"]=="C0_SPEED_DOWN_20261103_SMOKE", "Other pending jobs"
job=jobs[0]
assert st.get("active") is None and st.get("failure_hold")=="SPEED_SWEEP_PLUS2_20261103_SMOKE"
assert not blocks(st,cfg,job), "Scientific HOLD is not authorized for separate diagnostic"
assert job["approved"] and job["angle_deg"]==0 and job["cpu_processes"]==8
assert cfg.get("accept_new_jobs") is False
for name in ("STOP_OWNED_CFD.json","PAUSED_FOR_HOME.json"):
 assert not (H.parent/name).exists(), "Safety/pause marker exists "+name
launch_integrity(H,job)
proc=q.processes()
owned=[p for p in proc if p.get("ownedBatch")]
assert not owned, "Another solver owned by campaign"
res=q.resources()
assert res["disk_free_GiB"]>=18 and res["ram_available_GiB"]>=16, "Insufficient resource headroom"
print(json.dumps({"preflight":"PASS","job":job["id"],"approved":True,
 "separate_previous_failure_hold":st["failure_hold"],"other_jobs_pending":0,
 "active_owned_solver":False,"resources":res,"new_controller_needed":True},indent=2))
