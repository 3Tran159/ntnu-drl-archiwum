"""One 25-step Stokes V concurrency trial, monitored against the live W06 run."""
import csv
import datetime as dt
import json
import math
from pathlib import Path
import shutil
import statistics
import time

from run_day import HERE, LOCK, STOP, PORT, OWNER, READ, query, independent_jobs, new_job
from export_trajectory import csv_rows

CASE = Path(r"E:\ntnu_mesh_optimization_20261030\nwar_automation_20261102\runs\W06_20261104_083026_624dd4")
RANK = 18060
W06_LAUNCHER = 2220
BASELINE_FILE = HERE / "W06_STOKES_BASELINE.json"
REPORT = HERE / "W06_STOKES_TRIAL.json"
WATCH = HERE / "W06_STOKES_WATCH.csv"
EXPECTED = {2220,20584,27404,7948,22636,18060}
MASK = 16

def history():
    with (CASE/"history.csv").open(encoding="utf-8-sig",newline="") as f:
        rows=[r for r in csv.DictReader(f) if r.get("interface_CFL") and None not in r.values()]
    return [(int(r["step"]),float(r["wall_s"]),float(r["time_s"])) for r in rows]

def window(rows,n):
    data=rows[-n-1:]
    if len(data)!=n+1 or any(b[0]!=a[0]+1 or b[1]<=a[1] for a,b in zip(data,data[1:])):
        raise RuntimeError("Noncontiguous W06 step history")
    return [b[1]-a[1] for a,b in zip(data,data[1:])]

def save(path,value):
    temp=path.with_suffix(".tmp")
    temp.write_text(json.dumps(value,indent=2,allow_nan=False),encoding="utf8")
    temp.replace(path)

def host_snapshot():
    cmd = r"""
$ErrorActionPreference='Stop'
$p=Get-Process -Id __W06_RANK__,__W06_LAUNCHER__
$os=Get-CimInstance Win32_OperatingSystem
[pscustomobject]@{
  free_GiB=$os.FreePhysicalMemory/1MB
  processes=@($p|ForEach-Object{[pscustomobject]@{pid=$_.Id;cpu_s=$_.CPU;rss_MiB=$_.WorkingSet64/1MB;mask=$_.ProcessorAffinity.ToInt64();birth=$_.StartTime.ToFileTimeUtc()}})
}|ConvertTo-Json -Compress -Depth 4
"""
    return query(cmd.replace("__W06_RANK__",str(RANK)).replace("__W06_LAUNCHER__",str(W06_LAUNCHER)))[0]

class W06Protection:
    def __init__(self):
        self.baseline=None
        self.start_step=None
        self.last_step=None
        self.last_update=time.monotonic()
        self.peak=0.
        self.solving=[]
        self.process_ids=set()
        self.snapshot=None
        self.stopped=None
        self.license_granted=False

    def make_baseline(self):
        initial=host_snapshot()
        start=time.monotonic()
        time.sleep(10)
        final=host_snapshot()
        elapsed=time.monotonic()-start
        a={p["pid"]:p for p in initial["processes"]}
        for p in final["processes"]:
            p["avg_cpu_cores_10s"]=(p["cpu_s"]-a[p["pid"]]["cpu_s"])/elapsed
        self.snapshot=final
        h=history()
        if h[-1][0]<75 or time.time()-(CASE/"history.csv").stat().st_mtime>8:
            raise RuntimeError("W06 is not actively progressing")
        dur=window(h,60)
        self.baseline=statistics.median(dur)
        self.start_step=self.last_step=h[-1][0]
        self.last_update=time.monotonic()
        save(BASELINE_FILE,dict(w06_run=str(CASE),last_step=self.start_step,t_s=h[-1][2],
            median_s=self.baseline,mean_s=statistics.mean(dur),max_s=max(dur),window=60,
            w06_cpu_ram=final,declared_W06_license="Power on Demand (1 rank, GPU); W06 active",
            mini_cpu_logical=4,mini_affinity_mask=16,mini_gpu=False,threshold_review=.10,threshold_stop=.15))

    def check_foreign(self,owned):
        processes=query(READ)
        known={p["ProcessId"] for p in processes if p["ProcessId"] in EXPECTED and
               "21.02.007-R8" in (p.get("ExecutablePath") or "")}
        if not {RANK,W06_LAUNCHER}<=known:
            raise RuntimeError("Pinned W06 identity is no longer present")
        extras=[p["ProcessId"] for p in processes if p["ProcessId"] not in known and
                p["ProcessId"] not in owned and "21.04.009-R8" not in (p.get("ExecutablePath") or "")]
        if extras or independent_jobs()!=[("W06","running")]:
            raise RuntimeError("Independent queue/process set changed")

    def preflight(self):
        self.check_foreign(set())
        if any(p["ProcessId"] not in EXPECTED for p in query(READ)):
            raise RuntimeError("Another STAR/MPI process already active")
        if query(OWNER) or shutil.disk_usage(HERE).free<7*2**30:
            raise RuntimeError("Port or disk conflict")
        snapshot=host_snapshot()
        pin={p["pid"]:p for p in self.snapshot["processes"]}
        if snapshot["free_GiB"]<8 or any(p["mask"]&MASK or p["birth"]!=pin[p["pid"]]["birth"] for p in snapshot["processes"]):
            raise RuntimeError("W06 identity, E-core overlap or RAM preflight failure")

    def bind_native(self,rank):
        command=f"""
$ErrorActionPreference='Stop'
$c=Get-CimInstance Win32_Process -Filter 'ProcessId={rank}'
if($c.ExecutablePath -notlike '*21.04.009-R8*'){{throw 'Not the Mini 2606 rank'}}
$p=Get-Process -Id {rank}
$p.ProcessorAffinity=[IntPtr]16
[pscustomobject]@{{pid=$p.Id;mask=$p.ProcessorAffinity.ToInt64()}}|ConvertTo-Json -Compress
"""
        if query(command)[0]["mask"]!=MASK:
            raise RuntimeError("Mini rank did not bind to E4")
        self.process_ids.add(rank)

    def poll(self,owned,out,phase):
        if self.stopped:
            return
        try:
            self.check_foreign(owned)
            h=history()
            if h[-1][0]<self.last_step:
                raise RuntimeError("W06 step reset")
            if h[-1][0]>self.last_step:
                self.last_update=time.monotonic()
            if time.monotonic()-self.last_update>max(16,9*self.baseline):
                raise RuntimeError("W06 progress stalled")
            self.last_step=h[-1][0]
            if self.last_step<self.start_step+7:
                return
            med=statistics.median(window(h,7))
            rel=med/self.baseline-1
            self.peak=max(self.peak,rel)
            current=(out/"native_status.json")
            state=json.loads(current.read_text(encoding="utf8")) if current.exists() else {}
            if state.get("operation")=="SOLVING":
                self.solving.append((self.last_step,med,rel))
            serverlog=out/"server.log"
            if serverlog.exists():
                self.license_granted |= "ccmppower checked out" in serverlog.read_text(encoding="utf8",errors="replace").lower()
            with WATCH.open("a",encoding="ascii",newline="") as f:
                csv.writer(f).writerow((dt.datetime.now().astimezone().isoformat(),phase,self.last_step,h[-1][2],med,rel,state.get("steps","")))
            if rel>.15:
                raise RuntimeError(f"W06 seven-step median slower by {rel:.1%}")
        except Exception as err:
            self.stopped=str(err)
            STOP.write_text(self.stopped,encoding="utf8")

def main():
    if REPORT.exists() or BASELINE_FILE.exists():
        raise RuntimeError("Concurrency trial already attempted")
    with LOCK.open("x",encoding="ascii") as f:
        import os
        f.write(str(os.getpid()))
    p=W06Protection()
    try:
        p.make_baseline()
        p.preflight()
        result=new_job("STOKES_H050_COEX25",dict(fresh=True,stokes=True,foil=False,amplitude=.25,
                         old_amplitude=.25,expected_time=0,steps=25,limit_seconds=540),protection=p)
        case=Path(result["checkpoint"]).parent
        rows=csv_rows(case/"history.csv")
        readback=json.loads((case/"STOKES_AFTER_FIRST_STEP.json").read_text(encoding="utf8")) if rows else {}
        setup=json.loads((case/"STOKES_READBACK.json").read_text(encoding="utf8")) if rows else {}
        peak_solve=max((x[2] for x in p.solving),default=None)
        same_lifetime_steps=len({x[0] for x in p.solving})
        phys=all(float(r["pABSmin_Pa"])>12339.214766776897 and 0<=float(r["interface_CFL"])<=.5 and
                 float(r["max_CFL"])<=25 and float(r["volume_min"])>0 and
                 (i<5 or float(r["mass_relative"])<=1e-4) for i,r in enumerate(rows))
        transport=result["transport_ok"] and result["samples"]==25 and result["status"] in ("NUMERICAL_END_PASS","HOLD_RESIDUAL_WINDOW")
        grant=p.license_granted or "ccmppower checked out" in (case/"server.log").read_text(encoding="utf8",errors="replace").lower()
        passed=transport and phys and not p.stopped and grant and same_lifetime_steps>=4 and p.peak<=.10
        step_wall=csv_rows(case/"step_wall.csv") if (case/"step_wall.csv").exists() else []
        metrics=dict(p_min_Pa=min(float(r["pABSmin_Pa"]) for r in rows) if rows else None,
            interface_CFL_max=max(float(r["interface_CFL"]) for r in rows) if rows else None,
            mass_max_after_5=max((float(r["mass_relative"]) for r in rows[5:]),default=None),
            mean_wall_s_step=statistics.mean(float(r["step_wall_s"]) for r in step_wall[5:]) if len(step_wall)>5 else None)
        save(REPORT,dict(status="PASS_CONCURRENCY_SMOKE" if passed else "HOLD",
             baseline_s=p.baseline,max_rolling_slowdown=p.peak,active_phase_max_slowdown=peak_solve,
             distinct_active_W06_measurements=same_lifetime_steps,license_granted=grant,
             reason=p.stopped,result=result,stokes_setup=setup,stokes_after_first_step=readback,
             metrics=metrics,scientific_wave_validated=False,night_authorized=False))
    except Exception as err:
        save(REPORT,dict(status="HOLD",error=str(err),baseline_s=p.baseline,max_rolling_slowdown=p.peak,
                         reason=p.stopped,license_granted=p.license_granted,night_authorized=False))
        raise
    finally:
        LOCK.unlink()

if __name__=="__main__":
    with WATCH.open("x",encoding="ascii",newline="") as f:
        csv.writer(f).writerow(("time","phase","w06_step","w06_physical_s","w06_rolling_median_s","slowdown_fraction","mini_steps"))
    main()


