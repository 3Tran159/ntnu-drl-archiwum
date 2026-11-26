from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import time

D=Path(__file__).resolve().parent
OUT=D.parent
ROOT=OUT.parent
sys.path.insert(0,str(OUT.parents[2]))
import stokes_coexistence as coex
from run_day import HERE, LOCK, STOP, OWNER, READ, independent_jobs, new_job, query, sha

sys.path.insert(0,r"F:\ntnu\flap_control\hydro_validation_2606_20261102\tools")
from benchmark_telemetry import topology


class ProtectedTwoRanks(coex.W06Protection):
    def check_foreign(self, owned):
        processes=query(READ)
        known={p["ProcessId"] for p in processes if p["ProcessId"] in coex.EXPECTED
               and "21.02.007-R8" in (p.get("ExecutablePath") or "")}
        if not {coex.RANK,coex.W06_LAUNCHER}<=known or independent_jobs()!=[("W06","running")]:
            raise RuntimeError("W06 identity or independent CFD queue changed")
        self.unowned_pids=sorted(p["ProcessId"] for p in processes
                                if p["ProcessId"] not in known and p["ProcessId"] not in owned)

    def preflight(self):
        self.check_foreign(set())
        if query(OWNER) or shutil.disk_usage(HERE).free<7*2**30:
            raise RuntimeError("Mini port occupied or insufficient disk space")
        snapshot=coex.host_snapshot()
        initial={p["pid"]:p for p in self.snapshot["processes"]}
        if snapshot["free_GiB"]<8 or any(p["mask"]&coex.MASK or p["birth"]!=initial[p["pid"]]["birth"]
                                      for p in snapshot["processes"]):
            raise RuntimeError("W06 identity, E-core overlap, or RAM preflight failure")

    def bind_native_ranks(self, ranks, cpus):
        rows=[]
        for i,cpu in enumerate(cpus):
            pid=ranks[i]
            mask=1<<cpu
            row=query(f"""
$ErrorActionPreference='Stop'
$c=Get-CimInstance Win32_Process -Filter 'ProcessId={pid}'
if($c.Name -ne 'star-ccm+.exe' -or $c.ExecutablePath -notlike '*21.04.009-R8*'){{throw 'Not a Mini 2606 rank'}}
$p=Get-Process -Id {pid}
$p.ProcessorAffinity=[IntPtr]{mask}
[pscustomobject]@{{pid=$p.Id;mask=$p.ProcessorAffinity.ToInt64()}}|ConvertTo-Json -Compress
""")[0]
            if row["mask"]!=mask:
                raise RuntimeError("Mini rank affinity readback failed")
            rows.append(dict(rank=i,logical_cpu=cpu,**row))
            self.process_ids.add(pid)
        return rows


class QuiescentW06(ProtectedTwoRanks):
    case=Path(r"E:\ntnu_mesh_optimization_20261030\nwar_automation_20261102\runs\W06_20261104_100235_3b75bb")
    known=(18156,12224,13592,1336,1884,22656)

    def snapshot_now(self):
        return query(r"""
$ids=18156,12224,13592,1336,1884,22656
$process=@(Get-Process -Id $ids -ErrorAction SilentlyContinue | ForEach-Object {
    [pscustomobject]@{pid=$_.Id;cpu=[double]$_.CPU;mask=$_.ProcessorAffinity.ToInt64();
        birth=$_.StartTime.ToFileTimeUtc()}
})
$os=Get-CimInstance Win32_OperatingSystem
[pscustomobject]@{process=$process;free_GiB=$os.FreePhysicalMemory/1MB}|ConvertTo-Json -Compress -Depth 4
""")[0]

    def stamps(self):
        return tuple((p.stat().st_size,p.stat().st_mtime_ns) for p in
                     (self.case/"history.csv",self.case/"star.log",self.case/"latest_checkpoint.json"))

    def seed_idle(self):
        with (self.case/"star.log").open("rb") as f:
            f.seek(max(0,(self.case/"star.log").stat().st_size-8192))
            tail=f.read().decode("utf8",errors="replace")
        if "Connection reset" not in tail or "Server process exited with code : 1" not in tail:
            raise RuntimeError("No terminal failure record for the prior W06 run")
        self.fingerprint=self.stamps()
        self.anchor=self.snapshot_now()
        time.sleep(10)
        self.preflight()

    def preflight(self):
        if query(OWNER) or shutil.disk_usage(HERE).free<7*2**30:
            raise RuntimeError("Mini port occupied or insufficient disk space")
        self.check_inactive()

    def check_inactive(self):
        if independent_jobs():
            raise RuntimeError("An independent solver job became active")
        if self.stamps()!=self.fingerprint:
            raise RuntimeError("W06 resumed writing output")
        now=self.snapshot_now()
        initial={p["pid"]:p for p in self.anchor["process"]}
        if now["free_GiB"]<8:
            raise RuntimeError("Insufficient free RAM")
        if any(p["pid"] not in initial or p["birth"]!=initial[p["pid"]]["birth"] or
               p["cpu"]-initial[p["pid"]]["cpu"]>.35 or p["mask"]&coex.MASK for p in now["process"]):
            raise RuntimeError("W06 process activity or affinity changed")

    def poll(self, owned, out, phase):
        if self.stopped:
            return
        try:
            self.check_inactive()
        except Exception as exc:
            self.stopped=str(exc)
            if not STOP.exists():
                STOP.write_text(self.stopped,encoding="utf8")

def main():
    output=D/"TWO_E_QUIESCENT_RESULT.json"
    original=json.loads((D/"RESULT.json").read_text())
    retry=json.loads((D/"RETRY_RESULT.json").read_text())
    status=json.loads((HERE/"DAY_STATUS.json").read_text())
    marker="W06 progress stalled"
    if (output.exists() or not STOP.exists() or STOP.read_text().strip()!=marker
        or json.loads((D/"TWO_E_RESULT.json").read_text())["status"]!="HOLD" or retry["status"]!="HOLD"
        or status["solver_state"]!="STOPPED" or status["stage"]!="MATCHED_FIXED_SHARP_SEALED_RESUME0600_TWO_E"
        or independent_jobs()):
        raise RuntimeError("Protected two-rank resume preflight blocked")
    prefix=Path(original["checkpoint"]).parent
    source=Path(r"T:\FLAPS_ARCHIVE\SEALED_GAP_2D_U18_20261104\SHARP_SEALED_FIXED_0P600S.sim")
    if (sha(source)!=original["checkpoint_sha256_input"] or not (prefix/"fixed_history.csv").is_file()
        or not (prefix/"fixed_windows.csv").is_file()):
        raise RuntimeError("Saved sharp sealed checkpoint or force history mismatch")
    mesh=json.loads((ROOT/"SEALED_SHARP_MATCHED_OUTER"/"MESH_AUDIT.json").read_text())
    topo=topology()
    classes={r["efficiency_class"] for r in topo}
    if len(classes)<2:
        raise RuntimeError("Windows did not identify distinct performance and efficiency classes")
    w06=query("(Get-Process -Id 18156,12224 -ErrorAction SilentlyContinue | ForEach-Object {$_.ProcessorAffinity.ToInt64()}) | ConvertTo-Json -Compress")
    mask=0
    for value in w06:
        mask|=value
    e=sorted(r["logical_cpu"] for r in topo if r["group"]==0 and r["efficiency_class"]==min(classes)
             and not (mask & (1<<r["logical_cpu"])))
    if len(e)<2:
        raise RuntimeError("Two unshared E-cores are unavailable")
    cpus=e[:2]
    coex.MASK=sum(1<<cpu for cpu in cpus)
    coex.W06Protection=ProtectedTwoRanks
    with LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        guard=QuiescentW06()
        guard.seed_idle()
        coex.save(D/"QUIESCENT_W06_PREFLIGHT.json",dict(w06_queue=independent_jobs(),
                  fingerprints=guard.fingerprint,initial_processes=guard.anchor,cpu_indices=cpus))
        archived_stop=D/"STOP_W06_STALL_ARCHIVED.txt"
        if archived_stop.exists() or STOP.read_text().strip()!=marker:
            raise RuntimeError("Unexpected Mini stop marker")
        STOP.rename(archived_stop)
        coex.save(output,dict(status="RUNNING",checkpoint_source=str(source),initial_time_s=.6,
                              cpu_indices=cpus,mpi_ranks=2))
        result=new_job("MATCHED_FIXED_SHARP_SEALED_RESUME0600_TWO_E_IDLE_W06",dict(
            source=source,stokes=True,foil=True,moving=True,single_phase=True,
            coarse_2d_active=True,flow_cycle=True,expected_cells=mesh["cells"],
            expected_time=.6,amplitude=0,old_amplitude=0,inner=20,u_diagnostic_m_s=18,
            dt=.00025,steps=800,fixed_protocol=True,seeded_single_phase=True,
            fixed_from_unsteady=True,restore_fixed_history=True,
            fixed_prefix_directory=prefix.as_posix(),after_fixed_motion=True,limit_seconds=5600),
            protection=guard,macro_source=D/"MiniVofStokes.java",mpi_cpu_indices=cpus)
        case=Path(result["checkpoint"]).parent
        result["fixed"]=json.loads((case/"FIXED_PROTOCOL.json").read_text())
        result["W06"]=dict(mode="quiescent_after_independent_failure",stop=guard.stopped)
        result["cpu_indices"]=cpus
        coex.save(output,result)
    except Exception as e:
        coex.save(output,dict(status="HOLD",error=str(e),cpu_indices=cpus))
        raise
    finally:
        LOCK.unlink()

if __name__=="__main__":
    main()

