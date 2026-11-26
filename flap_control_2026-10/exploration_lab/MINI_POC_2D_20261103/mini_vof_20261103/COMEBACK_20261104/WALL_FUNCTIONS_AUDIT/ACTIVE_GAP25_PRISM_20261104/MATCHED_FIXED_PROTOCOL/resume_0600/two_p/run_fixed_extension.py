from pathlib import Path
import csv
import json
import os
import sqlite3
import statistics
import sys
import time

D=Path(__file__).resolve().parent
R=D.parent
sys.path.insert(0,str(R))
from run_two_e_coex import coex, ResourceGuard, HERE, LOCK, STOP, FOREIGN_QUEUE, new_job, query, sha, topology


def running_w06():
    with sqlite3.connect(FOREIGN_QUEUE.as_uri()+"?mode=ro",uri=True,timeout=3) as db:
        return [(Path(folder), json.loads(spec).get("mpi_processes")) for folder,spec in db.execute(
            "select folder,spec from jobs where case_id='W06' and status='running'")]


def samples(folder,n):
    p=folder/"history.csv"
    if not p.is_file() or time.time()-p.stat().st_mtime>12:
        return []
    with p.open("rb") as f:
        f.seek(0,2)
        f.seek(max(0,f.tell()-30000))
        raw=f.read().decode("utf8",errors="replace").splitlines()[1:]
    rows=[]
    for line in raw:
        v=line.split(",")
        try:
            rows.append((int(v[1]),float(v[2])))
        except (IndexError,ValueError):
            continue
    rows=rows[-n-1:]
    if len(rows)!=n+1 or any(b[0]!=a[0]+1 or b[1]<=a[1] for a,b in zip(rows,rows[1:])):
        return []
    return rows


class GuardP(ResourceGuard):
    def __init__(self, folder, baseline):
        super().__init__()
        self.folder=folder
        self.baseline_s=baseline

    def observe_w06(self):
        jobs=running_w06()
        if not jobs:
            return
        if jobs!=[(self.folder,1)]:
            raise RuntimeError("The measured one-rank W06 session changed")
        process=json.loads((self.folder/"process.json").read_text())
        if process.get("workers")!=1 or not process.get("gpu"):
            raise RuntimeError("W06 no longer uses the measured one-rank GPU setup")
        recent=samples(self.folder,7)
        if not recent or recent[-1][0]==self.last_sample:
            return
        self.last_sample=recent[-1][0]
        median=statistics.median(b[1]-a[1] for a,b in zip(recent,recent[1:]))
        slowdown=median/self.baseline_s-1
        self.peak=max(self.peak,slowdown)
        if self.watch:
            with self.watch.open("a",encoding="ascii",newline="") as f:
                csv.writer(f).writerow((time.strftime("%H:%M:%S"),self.last_sample,median,slowdown))


    def bind_native_ranks(self,ranks,cpus):
        rows=super().bind_native_ranks(ranks,cpus)
        for row in rows:
            pid=row["pid"]
            priority=query(f"""
$ErrorActionPreference='Stop'
$p=Get-Process -Id {pid}
$p.PriorityClass='High'
$p.PriorityClass.ToString()|ConvertTo-Json -Compress
""")[0]
            if priority!="High":
                raise RuntimeError("Mini priority readback failed")
            row["priority"]=priority
        return rows


def choose_p():
    topo=topology()
    levels={r["efficiency_class"] for r in topo}
    if len(levels)<2:
        raise RuntimeError("P/E CPU topology unavailable")
    p=[r["logical_cpu"] for r in topo if r["group"]==0 and r["efficiency_class"]==max(levels)]
    load={cpu:[] for cpu in p}
    for _ in range(3):
        rows=query("Get-CimInstance Win32_PerfFormattedData_Counters_ProcessorInformation | Select-Object Name,PercentProcessorTime | ConvertTo-Json -Compress")
        counter={str(r["Name"]):float(r["PercentProcessorTime"]) for r in rows}
        for cpu in p:
            if f"0,{cpu}" in counter:
                load[cpu].append(counter[f"0,{cpu}"])
        time.sleep(1)
    if len(p)<4 or any(len(v)<3 for v in load.values()):
        raise RuntimeError("P-core utilization readback incomplete")
    return sorted(p,key=lambda cpu:(statistics.mean(load[cpu]),cpu))[:2],load


def main():
    output=D/"FIXED_EXTENSION_RESULT.json"
    old=json.loads((D/"NO_W06_STOP_RESULT.json").read_text())
    status=json.loads((HERE/"DAY_STATUS.json").read_text())
    source=Path(old["checkpoint"])
    if (output.exists() or STOP.exists() or old["status"]!="HOLD_FIXED_NOT_SETTLED" or not old["transport_ok"]
        or status["solver_state"]!="STOPPED" or status["stage"]!="MATCHED_FIXED_SHARP_SEALED_TWO_P_MONITOR_W06"
        or source.parent!=Path(status["output"]) or sha(source)!=old["checkpoint_sha256"]
        or abs(old["state"]["time_s"]-1)>1e-8):
        raise RuntimeError("Sharp sealed stabilization extension preflight blocked")
    checkpoint=json.loads((source.parent/"LATEST_CHECKPOINT.json").read_text())
    if not checkpoint["complete_write"] or checkpoint["bytes"]!=source.stat().st_size:
        raise RuntimeError("Mini checkpoint write incomplete")
    t=old["state"]["time_s"]
    mesh=json.loads((R.parents[1]/"SEALED_SHARP_MATCHED_OUTER"/"MESH_AUDIT.json").read_text())
    with LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        coex.save(output,dict(status="PREFLIGHT",checkpoint_source=str(source),initial_time_s=t))
        deadline=time.monotonic()+410
        while time.monotonic()<deadline:
            jobs=running_w06()
            if len(jobs)==1 and jobs[0][1]==1:
                folder=jobs[0][0]
                recent=samples(folder,25)
                if recent:
                    baseline=old["W06"]["baseline_s"]
                    break
            time.sleep(8)
        else:
            raise RuntimeError("No fresh one-rank W06 baseline within the preflight window")
        cpus=old["cpu_indices"]
        if cpus!=[12,22]:
            raise RuntimeError("Unexpected prior P-core binding")
        load=None
        coex.MASK=sum(1<<cpu for cpu in cpus)
        guard=GuardP(folder,baseline)
        guard.watch=D/"EXTENSION_W06_WATCH.csv"
        with guard.watch.open("x",encoding="ascii") as f:
            f.write("time,W06_step,median_step_s,slowdown_fraction\n")
        guard.preflight()
        coex.save(D/"EXTENSION_PREFLIGHT.json",dict(p_logical_indices=cpus,p_usage_percent=load,
                   w06_folder=str(folder),w06_baseline_s=baseline,w06_slowdown_gate_enabled=False,mini_priority="High"))
        coex.save(output,dict(status="RUNNING",checkpoint_source=str(source),initial_time_s=t,cpu_indices=cpus,mpi_ranks=2))
        result=new_job("MATCHED_FIXED_SHARP_SEALED_TWO_P_EXTEND",dict(
            source=source,stokes=True,foil=True,moving=True,single_phase=True,
            coarse_2d_active=True,flow_cycle=True,expected_cells=mesh["cells"],expected_time=t,
            amplitude=0,old_amplitude=0,inner=20,u_diagnostic_m_s=18,dt=.00025,steps=0,
            fixed_protocol=True,fixed_cap_s=1.5,seeded_single_phase=True,fixed_from_unsteady=True,restore_fixed_history=True,
            fixed_prefix_directory=source.parent.as_posix(),after_fixed_motion=False,limit_seconds=5600),
            protection=guard,macro_source=D/"MiniVofStokesExtend.java.txt",mpi_cpu_indices=cpus)
        result["fixed"]=json.loads((Path(result["checkpoint"]).parent/"FIXED_PROTOCOL.json").read_text())
        result["W06"]=dict(baseline_s=baseline,peak=guard.peak,stop=guard.stopped,slowdown_gate_enabled=False)
        result["cpu_indices"]=cpus
        coex.save(output,result)
    except Exception as exc:
        coex.save(output,dict(status="HOLD",error=str(exc),checkpoint=str(source),time_s=t))
        raise
    finally:
        LOCK.unlink()

if __name__=="__main__":
    main()




