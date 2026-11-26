"""Resume Mini on P22/P23 alongside the verified, pinned NWAR sessions."""
import math
import os
from pathlib import Path
import sqlite3
import sys
import time

import wave_phase_map_campaign as campaign
from wave_phase_map_after_transport import WAIT_LOCK
from wave_phase_map_analysis import finish_fixed_and_run_active
from resume import CPUS, D, P, c, run_day

MINI_MASK = sum(1 << n for n in CPUS)
STATUS = D / "WAVE_ISOLATED_RESUME.json"
NWAR = Path("E:/ntnu_mesh_optimization_20261030/nwar_automation_20261102")
SOURCE = P / "runs/PHASE_MAP_WAVE_FIXED_20261106_104930/FINAL.sim"
DIGEST = "1e789d3fc7d7976cade9930ba6418653dc593174b35bc6aed3b3851be3b92b80"
EXPECTED_PARENT = "744e131de23d2b987bc10046541422e1d396bf36fdc2b6cdc19416b379a2f4b6"
SNAPSHOT = r"""
$ErrorActionPreference='Stop'
$candidate='__W04B_INPUT__'
$all=Get-CimInstance Win32_Process
$index=@{}
foreach($row in $all){ $index[[int]$row.ProcessId]=$row }
$results=foreach($row in $all){
    if($row.Name -notmatch '^(starccm[+w]|star-ccm\+|smpd|mpiexec|impi)'){continue}
    $p=Get-Process -Id $row.ProcessId -ErrorAction SilentlyContinue
    if(!$p){continue}
    $ids=@()
    $branch=$row
    $case=''
    while($null -ne $branch -and $branch.ProcessId -notin $ids){
        $ids+= [int]$branch.ProcessId
        if($branch.CommandLine -and $candidate -and $branch.CommandLine.IndexOf($candidate,[StringComparison]::OrdinalIgnoreCase) -ge 0){$case='W04b'}
        if($branch.CommandLine -like '*\wake_history_native_qa_20261106\cpu_snapshot\input.sim*'){$case='NWAR-QA'}
        if($branch.CommandLine -like '*\mesh_W04a_channel_native_20261106\attempt_01\input.sim*'){$case='W04a'}
        if($branch.CommandLine -like '*\mesh_W04a_channel_native_20261106\attempt_02\input.sim*'){$case='W04a-attempt02'}
        $branch=$index[[int]$branch.ParentProcessId]
    }
    [pscustomobject]@{pid=$row.ProcessId; name=$row.Name; mask=$p.ProcessorAffinity.ToInt64();
        born=$p.StartTime.ToFileTimeUtc(); ancestry=$ids; case_id=$case}
}
@($results) | ConvertTo-Json -Depth 4 -Compress
"""


def inventory():
    with sqlite3.connect((NWAR / "queue.sqlite").as_uri() + "?mode=ro", uri=True, timeout=3) as db:
        jobs = db.execute("SELECT folder,controller_pid FROM jobs WHERE case_id='W04b' AND status='running'").fetchall()
    candidate = ""
    if len(jobs) == 1:
        folder, pid = jobs[0]
        folder = Path(folder).resolve()
        if folder.parent == NWAR / "runs" and folder.name.startswith("W04b_"):
            receipt = c.read(folder / "process.json")
            if receipt["controller_pid"] == pid and receipt["mask"] == 1 << 11 and receipt["workers"] == 1:
                candidate = str(folder / "input.sim").replace("'", "''")
    return run_day.query(SNAPSHOT.replace("__W04B_INPUT__", candidate))


def restore_verified_rank_affinity(row, expected):
    # Only an identified NWAR meshing or QA native rank may be adjusted.
    # Match process birth time and its observed mask before changing anything.
    command = f"""
$ErrorActionPreference='Stop'
$p=Get-Process -Id {row['pid']}
if($p.StartTime.ToFileTimeUtc() -ne {row['born']} -or
   $p.ProcessorAffinity.ToInt64() -ne {row['mask']}) {{ throw 'STAR identity or affinity changed' }}
$p.ProcessorAffinity=[IntPtr]{expected}
$p.ProcessorAffinity.ToInt64() | ConvertTo-Json -Compress
"""
    if run_day.query(command) != [expected]:
        raise RuntimeError(f"Affinity readback failed for PID {row['pid']}")
    row["previous_mask"] = row["mask"]
    row["mask"] = expected
    with (D / "WAVE_ISOLATED_AFFINITY_CHANGES.log").open("a", encoding="utf8") as stream:
        stream.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {row['case_id']} "
                     f"PID={row['pid']} birth={row['born']} {row['previous_mask']:#x} -> {expected:#x}\n")


def check_foreign(owned, retained):
    found = []
    for row in inventory():
        if owned.intersection(row["ancestry"]):
            continue
        identity = (row["pid"], row["born"])
        expected = {"W04a": 1 << 14, "W04b": 1 << 11, "NWAR-QA": 1 << 15, "W04a-attempt02": 1 << 11}.get(row["case_id"])
        if expected is None:
            expected = retained.get(identity)
        if (row["case_id"] in {"W04a", "W04a-attempt02", "NWAR-QA"}
                and row["name"] == "star-ccm+.exe" and row["mask"] == 0xFFFFFF):
            restore_verified_rank_affinity(row, expected)
        if expected is None or row["mask"] != expected or row["mask"] & MINI_MASK:
            raise RuntimeError(f"Unverified foreign STAR affinity or identity: PID {row['pid']}")
        retained[identity] = expected
        found.append(row)
    jobs = run_day.independent_jobs()
    if any(case != "W04b" for case, _ in jobs):
        raise RuntimeError(f"Other independent STAR jobs: {jobs}")
    return found


class IsolatedGuard(c.NightGuard):
    def __init__(self, retained):
        super().__init__(None, 1.777749)
        self.retained = retained
        self.last_identity_check = 0

    def preflight(self):
        super().preflight()
        check_foreign(set(), self.retained)

    def poll(self, owned, out, phase):
        super().poll(owned, out, phase)
        if self.stopped or time.monotonic() - self.last_identity_check < 5:
            return
        self.last_identity_check = time.monotonic()
        try:
            check_foreign(set(owned), self.retained)
        except Exception as error:
            self.stopped = str(error)
            if not c.STOP.exists():
                c.STOP.write_text(self.stopped, encoding="utf8")


def main(preflight_only):
    state = c.read(campaign.STATE)
    if state["operation"] not in ("WAITING_FOR_RESOURCES", "HOLD"):
        raise RuntimeError("Expected the verified, resource-waiting Mini checkpoint")
    if (c.STOP.exists() and not preflight_only) or c.LOCK.exists():
        raise RuntimeError("Existing Mini STOP or solver ownership lock")
    # The W04b launcher exited after a transport error. Only the exact surviving
    # P11 processes verified against its observed MPI tree may be grandfathered.
    detached_w04b = {19048, 12340, 31484, 32120, 30692}
    retained = {(r["pid"], r["born"]): 1 << 11 for r in inventory()
                if r["pid"] in detached_w04b and r["mask"] == 1 << 11}
    if STATUS.exists():
        previous = c.read(STATUS)
        for row in previous["foreign_processes"]:
            if row["mask"] in (1 << 11, 1 << 14, 1 << 15):
                retained[(row["pid"], row["born"])] = row["mask"]
    guard = IsolatedGuard(retained)
    c.coex.MASK = c.local.night_flap.MASK = MINI_MASK
    guard.preflight()
    foreign = check_foreign(set(), retained)
    if WAIT_LOCK.exists():
        raise RuntimeError("Old Mini resource waiter still owns its lock")
    if c.sha(SOURCE) != DIGEST:
        raise RuntimeError("Production checkpoint checksum mismatch")
    folder = SOURCE.parent
    cfg = c.read(folder / "job.json")
    source, t, history, n = campaign.recover(folder, float(cfg["expected_time"]), int(cfg["steps"]))
    if source != SOURCE or n != 9 or cfg["input_sha256"] != EXPECTED_PARENT:
        raise RuntimeError("Unexpected recovery lineage")
    for segment in state["segments"]:
        if c.sha(campaign.Path(segment["checkpoint"])) != segment["sha256"]:
            raise RuntimeError("Archived phase-identification lineage changed")

    if preflight_only:
        print(f"Verified checkpoint: {t:.4f} s, {n} steps, SHA-256 {DIGEST}")
        print([(r["pid"], r["case_id"], r["mask"]) for r in foreign])
        return
    if not any(segment["checkpoint"] == str(source) for segment in state["segments"]):
        state["segments"].append(dict(stage=campaign.FIXED_STAGE, folder=str(folder), end_s=t,
            status="PAUSED_VERIFIED", checkpoint=str(source), sha256=DIGEST))

    def isolated_job(stage, source, start, macro_source, **config):
        settings = dict(stokes=True, foil=True, expected_cells=25617, matched_calm=True,
                        pressure_diagnostic_only=True, af_native=True, source=source,
                        expected_time=start, gpu_requested=False)
        return run_day.new_job(stage, {**settings, **config}, protection=IsolatedGuard(retained),
                               macro_source=macro_source, mpi_cpu_indices=CPUS, gpu=False)

    with c.LOCK.open("x", encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        c.coex.save(STATUS, dict(mode="isolated_cpu_resume", mini_cpus=CPUS, w04b_cpu=11,
                                 gpu=False, foreign_processes=foreign, checkpoint_sha256=DIGEST))
        campaign.STATE_DATA.update(state)
        campaign.job = isolated_job
        campaign.status(operation="RESUMING_WAVE_FIXED", reason=None, resource_mode="isolated_cpu_resume", physical_time_s=t, last_checkpoint=str(source))
        remaining = math.ceil((campaign.START_GATE + campaign.CYCLES * campaign.PERIOD - t) / campaign.DT)
        source, t, history = campaign.integrate(campaign.FIXED_STAGE, source, t, history, remaining)
        finish_fixed_and_run_active(source, t, history)
    except Exception as error:
        campaign.status(operation="HOLD", reason=str(error))
        raise
    finally:
        if not c.filtered_query(c.OWNER):
            c.LOCK.unlink()


if __name__ == "__main__":
    main("--preflight" in sys.argv)
