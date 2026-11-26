import argparse
import csv
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from run_day import LOCK, OWNER, READ, STOP, new_job, query, sha

sys.path.insert(0, str(next(HERE.parent.rglob("run_active_resume_1064.py")).parent))
from run_active_resume_1064 import GuardResume, coex, topology

ARCHIVE = Path(r"T:/FLAPS_ARCHIVE/SEALED_GAP_2D_U18_20261104")
OUT = ARCHIVE / "NIGHT_FLAP_20261104"
STATUS = HERE / "STATUS.json"
DT = .00025
VP = 2339.214766776897
CPUS = [12, 22]
MASK = sum(1 << cpu for cpu in CPUS)
coex.MASK = MASK
END = dt.datetime(2026, 11, 5, 7, 0, tzinfo=dt.timezone(dt.timedelta(hours=1))).timestamp()
PLAN = ("GAP_PLUS_MINUS_2", "SHARP_SEALED_PLUS_MINUS_5", "GAP_PLUS_MINUS_5", "CALM_VOF_PAIR", "SURROGATE_PILOT")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def archive(src, dest):
    shutil.copy2(src, dest)
    if sha(src) != sha(dest):
        raise RuntimeError(f"Archive checksum mismatch for {src.name}")


def history(path):
    with path.open(newline="") as file:
        reader = csv.DictReader(file)
        return reader.fieldnames, list(reader)


class NightGuard(GuardResume):
    headroom_checked_at=0.0
    def check_affinity(self, owned):
        processes = query(READ)
        pids = [p["ProcessId"] for p in processes if p["Name"]=="star-ccm+.exe" and p["ProcessId"] not in owned]
        if not pids:
            return
        values = query("(Get-Process -Id "+",".join(map(str,pids))+
                       " -ErrorAction SilentlyContinue | ForEach-Object {$_.ProcessorAffinity.ToInt64()}) | ConvertTo-Json -Compress")
        host_mask = sum(1 << item["logical_cpu"] for item in topology() if item["group"]==0)
        if any(value & MASK and value != host_mask for value in values):
            raise RuntimeError("An independent STAR compute rank overlaps the assigned Mini CPUs")
        if host_mask in values and time.monotonic()-NightGuard.headroom_checked_at>45:
            measurement=query(r"""
$old=@{}
Get-Process | ForEach-Object { $old[$_.Id]=$_.CPU }
$timer=[Diagnostics.Stopwatch]::StartNew()
Start-Sleep -Seconds 5
$sum=0.
Get-Process | ForEach-Object {
  if ($old.ContainsKey($_.Id) -and $null -ne $_.CPU -and $_.ProcessName -notin @('Idle','System')) {
    $sum += [Math]::Max(0,$_.CPU-$old[$_.Id])
  }
}
[pscustomobject]@{used_cores=$sum/$timer.Elapsed.TotalSeconds; cores=[Environment]::ProcessorCount} | ConvertTo-Json -Compress
""")
            if not measurement or measurement[0]["cores"]-measurement[0]["used_cores"]<4:
                raise RuntimeError("Unpinned independent STAR ranks and fewer than four spare CPU equivalents")
            NightGuard.headroom_checked_at=time.monotonic()

    def preflight(self):
        super().preflight()
        self.check_affinity(set())



def await_resources(state,stage):
    last_error=None
    while not STOP.exists() and time.time()<END-420:
        try:
            NightGuard(None,1.777749).preflight()
            return True
        except RuntimeError as exc:
            last_error=str(exc)
            soft=("assigned Mini CPUs" in last_error or "spare CPU equivalents" in last_error)
            if not soft:
                raise
            state.update(status="WAITING_RESOURCES",active=stage,resource_wait=last_error)
            coex.save(STATUS,state)
            time.sleep(60)
    if last_error:
        state["resource_wait"]=last_error
    return False

def run_cycle(stage, source, digest, origin, start, amplitude, quarter, cells, gap, prefix):
    if sha(source) != digest:
        raise RuntimeError(f"{stage} input checksum mismatch")
    end = origin+4*quarter
    steps = round((end-start)/DT)
    if steps<=0 or abs(start+steps*DT-end)>1e-9:
        raise RuntimeError("Invalid cycle duration")
    guard = NightGuard(None, 1.777749)
    guard.watch = HERE/(stage+"_W06.csv")
    if not guard.watch.exists():
        guard.watch.write_text("time,W06_step,median_step_s,slowdown_fraction\n",encoding="ascii")
    mode = dict(source=source,expected_time=start,resume_coarse_active=start>origin,
        motion_origin_s=origin, reference_tip_x_m=1.19,reference_tip_y_m=0.0,
        stokes=True,foil=True,moving=True,single_phase=True,coarse_2d_active=True,
        flow_cycle=True,expected_cells=cells,amplitude=0,old_amplitude=0,inner=20,
        u_diagnostic_m_s=18,dt=DT,steps=steps,seeded_single_phase=True,gapped_geometry=gap,
        fixed_from_unsteady=True,pressure_diagnostic_only=True,flap_cycle_deg=amplitude,
        flap_quarter_s=quarter,limit_seconds=min(9000,int(END-time.time()-90)))
    if mode["limit_seconds"]<300:
        return {"status":"HOLD_NIGHT_DEADLINE"}
    try:
        result = new_job(stage,mode,protection=guard,macro_source=HERE/"MiniVofStokes.java",mpi_cpu_indices=CPUS)
    except Exception:
        state = read(HERE.parent/"DAY_STATUS.json")
        run = Path(state.get("output",""))
        if (state.get("stage") != stage or STOP.exists() or query(OWNER)
            or not (run/"LATEST_CHECKPOINT.json").is_file() or not (run/"client.log").is_file()):
            raise
        log = (run/"client.log").read_text(encoding="utf-8",errors="replace")
        receipt = read(run/"LATEST_CHECKPOINT.json")
        if "Connection reset" not in log or not receipt["complete_write"]:
            raise
        cp = Path(receipt["path"])
        saved = float(receipt["time_s"])
        if saved <= start+1e-9 or saved >= end-1e-9 or cp.parent!=run or cp.stat().st_size!=receipt["bytes"]:
            raise
        _, old = history(run/"single_phase.csv")
        kept = [row for row in old if float(row["time_s"]) <= saved+1e-9]
        if len(kept)!=round((saved-start)/DT):
            raise RuntimeError("Transport recovery history does not match checkpoint")
        mode.update(source=cp,expected_time=saved,resume_coarse_active=True,steps=round((end-saved)/DT),
                    limit_seconds=min(9000,int(END-time.time()-90)))
        if mode["limit_seconds"]<300:
            raise RuntimeError("Night deadline prevents transport recovery")
        result = new_job(stage+"_TRANSPORT_RESUME",mode,protection=guard,
                         macro_source=HERE/"MiniVofStokes.java",mpi_cpu_indices=CPUS)
        prefix = prefix+kept
        result["transport_recovery"] = {"previous_run":str(run),"checkpoint":str(cp),"time_s":saved}
    run = Path(result["checkpoint"]).parent
    fields, tail = history(run/"single_phase.csv")
    rows = prefix+tail
    if not rows or any(abs(float(row["time_s"])-(origin+i*DT))>1e-8 for i,row in enumerate(rows,1)):
        raise RuntimeError("Noncontinuous cycle history")
    dest = OUT/stage
    dest.mkdir()
    for name in ("FINAL.sim","LATEST_CHECKPOINT.json","single_phase.csv","residual_per_step.csv","PRESSURE_BELOW_VAPOR.csv",
                 "PRESSURE_SCOPE.json","SOLVE_STATUS.json","DAY_RESULT.json","vertices_final.csv"):
        if (run/name).is_file():
            archive(run/name,dest/name)
    with (dest/"cycle_full_available.csv").open("x",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    pressure = [min(float(row["pflap_min_Pa"]),float(row["pgap_min_Pa"])) for row in rows]
    angle = [float(row["delta_measured_deg"]) for row in rows]
    result.update(total_steps=len(rows),angle_range_deg=[min(angle),max(angle)],
                  flap_pmin_Pa=min(float(row["pflap_min_Pa"]) for row in rows),
                  hinge_pmin_Pa=min(float(row["pgap_min_Pa"]) for row in rows),
                  samples_at_or_below_vapor=sum(p<=VP for p in pressure),
                  p_vapor_Pa=VP,archive=str(dest),training_approved=False,
                  cycle_complete=(result["transport_ok"] and result["status"]=="PASS_DIAGNOSTIC_SMOKE"
                      and len(rows)==round(4*quarter/DT) and min(angle)<-.995*amplitude
                      and max(angle)>.995*amplitude and abs(angle[-1])<.01))
    coex.save(dest/"RESULT.json",result)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--resume-resource-hold",action="store_true")
    resume=parser.parse_args().resume_resource_hold
    previous = ARCHIVE/"GAP_MATCHED_STABILIZE_THEN_ACTIVE_RESUME0600"
    old = read(previous/"RESULT.json")
    if old["status"]!="HOLD_FLAP_PRESSURE_MARGIN":
        raise RuntimeError("Unexpected parent case status")
    fixed = {row["name"]: row["sha256"] for row in read(ARCHIVE/"MANIFEST.json")}
    gap0 = "GAP_FIXED_STABLE_1P000S.sim"
    sealed0 = "SHARP_SEALED_FIXED_STABLE_1P050S.sim"
    _, prefix = history(previous/"single_phase.csv")
    cases = (
        (PLAN[0],previous/"FINAL.sim",old["checkpoint_sha256"],1.,float(old["state"]["time_s"]),2.,.05,19502,True,prefix),
        (PLAN[1],ARCHIVE/sealed0,fixed[sealed0],1.05,1.05,5.,.125,17462,False,[]),
        (PLAN[2],ARCHIVE/gap0,fixed[gap0],1.,1.,5.,.125,19502,True,[]),
    )
    with LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    state={"status":"STARTED","plan":list(PLAN),"active":None,"runs":{},"pressure_policy":"WARN_AT_2339.214766776897_PA",
           "mpi_logical_cpu":CPUS,"night_end":"2026-11-05T07:00:00+01:00"}
    try:
        if resume:
            saved=read(STATUS)
            complete=saved["runs"].get(PLAN[0],{})
            if saved["status"]!="REVIEW" or not complete.get("cycle_complete") or sha(OUT/PLAN[0]/"FINAL.sim")!=complete["checkpoint_sha256"]:
                raise RuntimeError("Resource restart requires verified completed gap +/-2")
            keep={PLAN[0]:complete}
            for name in PLAN[1:3]:
                previous_result=saved["runs"].get(name,{})
                if (OUT/name).exists():
                    if not previous_result.get("checkpoint_sha256") or sha(OUT/name/"FINAL.sim")!=previous_result["checkpoint_sha256"]:
                        raise RuntimeError("Existing cycle result failed restart verification: "+name)
                    keep[name]=previous_result
            if any((OUT/name).exists() for name in ("CALM_VOF_FIXED_SEALED","CALM_VOF_FIXED_GAP","SURROGATE_PILOT")):
                raise RuntimeError("Resource restart would duplicate an existing VOF result")
            snapshot=OUT/("RESOURCE_HOLD_BEFORE_RESUME_"+dt.datetime.now().strftime("%H%M%S")+".json")
            archive(STATUS,snapshot)
            state["runs"].update(keep)
            state["resource_policy"]="Wait for measured host CPU headroom; protect fixed foreign affinity."
            cases=tuple(case for case in cases if case[0] not in keep)
        else:
            OUT.mkdir()
        for case in cases:
            if STOP.exists() or query(OWNER) or time.time()>=END-390:
                break
            stage=case[0]
            if not await_resources(state,stage):
                state["runs"][stage]={"status":"HOLD_RESOURCE_OR_DEADLINE"}
                break
            state.pop("resource_wait",None)
            state.update(status="RUNNING",active=stage)
            coex.save(STATUS,state)
            try:
                state["runs"][stage]=run_cycle(*case)
            except Exception as exc:
                state["runs"][stage]={"status":"HOLD","reason":str(exc)}
            coex.save(STATUS,state)
        if not STOP.exists() and not query(OWNER) and time.time()<END-390:
            hook=HERE/"calm_pair_ready.py"
            until=min(END-390,time.time()+1800)
            while not hook.is_file() and not STOP.exists() and time.time()<until:
                state.update(status="WAITING",active="CALM_VOF_PAIR_PREPARATION")
                coex.save(STATUS,state)
                time.sleep(20)
            if hook.is_file() and not STOP.exists():
                from calm_pair_ready import run_vof_pair
                run_vof_pair(state)
            else:
                state["runs"]["CALM_VOF_PAIR"]={"status":"HOLD","reason":"Matched VOF preparation missing or deadline"}
        state["status"]="STOPPED" if STOP.exists() else "REVIEW"
    except Exception as exc:
        state.update(status="HOLD",reason=str(exc))
        raise
    finally:
        state["active"]=None
        coex.save(STATUS,state)
        if not query(OWNER):
            LOCK.unlink()


if __name__ == "__main__":
    main()

