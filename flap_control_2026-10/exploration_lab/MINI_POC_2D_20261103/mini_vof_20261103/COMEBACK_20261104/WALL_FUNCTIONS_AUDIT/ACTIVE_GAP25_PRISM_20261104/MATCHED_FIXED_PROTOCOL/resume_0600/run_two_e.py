from pathlib import Path
import json
import os
import shutil
import sys
import time

D=Path(__file__).resolve().parent
OUT=D.parent
ROOT=OUT.parent
sys.path.insert(0,str(OUT.parents[2]))
import stokes_coexistence as coex
from run_day import HERE, LOCK, STOP, OWNER, READ, independent_jobs, new_job, query, sha
from run_recovery_calm_komega import protect_w06
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


def main():
    output=D/"TWO_E_RESULT.json"
    original=json.loads((D/"RESULT.json").read_text())
    retry=json.loads((D/"RETRY_RESULT.json").read_text())
    status=json.loads((HERE/"DAY_STATUS.json").read_text())
    marker="Independent queue/process set changed"
    if (output.exists() or not STOP.exists() or STOP.read_text().strip()!=marker
        or original.get("W06",{}).get("stop")!=marker or retry["status"]!="HOLD"
        or status["solver_state"]!="STOPPED" or status["stage"]!="MATCHED_FIXED_SHARP_SEALED_RESUME0600"
        or independent_jobs()!=[("W06","running")]):
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
    w06=query("(Get-Process -Id 18156,12224 | ForEach-Object {$_.ProcessorAffinity.ToInt64()}) | ConvertTo-Json -Compress")
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
        guard=protect_w06("MATCHED_FIXED_SHARP_SEALED_TWO_E_"+time.strftime("%H%M%S"))
        audit=json.loads(coex.BASELINE_FILE.read_text())
        audit.update(mini_cpu_logical=cpus,mini_affinity_mask=coex.MASK,mpi_ranks=2,
                     extra_processes_observed=guard.unowned_pids,process_presence_only_stop=False)
        coex.save(coex.BASELINE_FILE,audit)
        archived_stop=D/"STOP_FOREIGN_PROCESS_TWO_E_SUPERSEDED.txt"
        if archived_stop.exists() or STOP.read_text().strip()!=marker:
            raise RuntimeError("Unexpected Mini stop marker")
        STOP.rename(archived_stop)
        coex.save(output,dict(status="RUNNING",checkpoint_source=str(source),initial_time_s=.6,
                              cpu_indices=cpus,mpi_ranks=2))
        result=new_job("MATCHED_FIXED_SHARP_SEALED_RESUME0600_TWO_E",dict(
            source=source,stokes=True,foil=True,moving=True,single_phase=True,
            coarse_2d_active=True,flow_cycle=True,expected_cells=mesh["cells"],
            expected_time=.6,amplitude=0,old_amplitude=0,inner=20,u_diagnostic_m_s=18,
            dt=.00025,steps=800,fixed_protocol=True,seeded_single_phase=True,
            fixed_from_unsteady=True,restore_fixed_history=True,
            fixed_prefix_directory=prefix.as_posix(),after_fixed_motion=True,limit_seconds=5600),
            protection=guard,macro_source=D/"MiniVofStokes.java",mpi_cpu_indices=cpus)
        case=Path(result["checkpoint"]).parent
        result["fixed"]=json.loads((case/"FIXED_PROTOCOL.json").read_text())
        result["W06"]=dict(peak=guard.peak,stop=guard.stopped)
        result["cpu_indices"]=cpus
        coex.save(output,result)
    except Exception as e:
        coex.save(output,dict(status="HOLD",error=str(e),cpu_indices=cpus))
        raise
    finally:
        LOCK.unlink()

if __name__=="__main__":
    main()

