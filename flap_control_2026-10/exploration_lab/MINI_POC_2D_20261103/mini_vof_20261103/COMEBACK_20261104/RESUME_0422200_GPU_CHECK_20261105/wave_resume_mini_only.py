"""Resume the existing Mini campaign with checks scoped to Mini and host headroom."""
import math
import os
from pathlib import Path
import shutil
import sys
import time

import wave_phase_map_campaign as campaign
from wave_phase_map_after_transport import WAIT_LOCK
from wave_phase_map_analysis import finish_fixed_and_run_active
from resume import CPUS, D, P, c, run_day

STATUS = D / "WAVE_MINI_ONLY_RESUME.json"


class MiniGuard(c.NightGuard):
    def __init__(self):
        super().__init__(None, 1.777749)
        self.bindings = []
        self.checked_at = 0

    def headroom(self):
        if shutil.disk_usage(P).free < 7 * 2**30 or self.resources()["free_GiB"] < 8:
            raise RuntimeError("Insufficient disk space or RAM for Mini")

    def preflight(self):
        if c.STOP.exists() or run_day.query(run_day.OWNER):
            raise RuntimeError("Mini STOP requested or Mini port occupied")
        self.headroom()

    def bind_native_ranks(self, ranks, cpus):
        if list(cpus) != [22, 23]:
            raise RuntimeError("Mini must use P22/P23")
        self.bindings = super().bind_native_ranks(ranks, cpus)
        return self.bindings

    def poll(self, owned, out, phase):
        if self.stopped or time.monotonic() - self.checked_at < 10:
            return
        self.checked_at = time.monotonic()
        try:
            self.headroom()
            if self.bindings:
                ids = ",".join(str(row["pid"]) for row in self.bindings)
                rows = run_day.query(f"""
$rows=@(Get-Process -Id {ids} -ErrorAction SilentlyContinue | ForEach-Object {{
    [pscustomobject]@{{pid=$_.Id; mask=$_.ProcessorAffinity.ToInt64(); priority=$_.PriorityClass.ToString()}}
}})
ConvertTo-Json -InputObject $rows -Compress
exit 0
""")
                expected = {row["pid"]: row["mask"] for row in self.bindings}
                if any(row["mask"] != expected[row["pid"]] or row["priority"] != "High" for row in rows):
                    raise RuntimeError("Mini MPI affinity or priority changed")
        except Exception as error:
            self.stopped = str(error)
            if not c.STOP.exists():
                c.STOP.write_text(self.stopped, encoding="utf8")


def production_source(state):
    segments = state["segments"]
    for segment in segments:
        if c.sha(Path(segment["checkpoint"])) != segment["sha256"]:
            raise RuntimeError("Archived phase-identification checkpoint checksum mismatch")
    latest = segments[-1]
    base = Path(latest["checkpoint"])
    folder = base.parent
    if folder != Path(latest["folder"]) or folder.parent != P / "runs":
        raise RuntimeError("Unexpected checkpoint folder")
    job = c.read(folder / "job.json")
    source, t, history, _ = campaign.recover(folder, float(job["expected_time"]), int(job["steps"]))
    if source != base or abs(t - latest["end_s"]) > 1e-8:
        raise RuntimeError("Recorded production checkpoint provenance mismatch")

    day = c.read(P / "DAY_STATUS.json")
    result = day.get("result", {})
    if result.get("samples", 0) > 0 and result["state"]["time_s"] > t + 1e-8:
        if (day["stage"] != campaign.FIXED_STAGE or day["solver_state"] != "STOPPED"
                or result["status"] != "HOLD_STOP_OR_DEADLINE" or not result["transport_ok"]
                or result["checkpoint_sha256_input"] != latest["sha256"]):
            raise RuntimeError("Newer checkpoint requires review")
        new_folder = Path(day["output"])
        job = c.read(new_folder / "job.json")
        candidate, end, hist, n = campaign.recover(new_folder, float(job["expected_time"]), int(job["steps"]))
        if (str(candidate) != result["checkpoint"] or c.sha(candidate) != result["checkpoint_sha256"]
                or n != result["samples"] or abs(float(job["expected_time"]) - t) > 1e-8):
            raise RuntimeError("Newer checkpoint failed lineage verification")
        segments.append(dict(stage=campaign.FIXED_STAGE, folder=str(new_folder), end_s=end,
            status="PAUSED_VERIFIED", checkpoint=str(candidate), sha256=result["checkpoint_sha256"]))
        source, t, history = candidate, end, hist
    return source, t, history


def mini_job(stage, source, start, macro_source, **config):
    settings = dict(stokes=True, foil=True, expected_cells=25617, matched_calm=True,
                    pressure_diagnostic_only=True, af_native=True, source=source,
                    expected_time=start, gpu_requested=False)
    return run_day.new_job(stage, {**settings, **config}, protection=MiniGuard(),
                           macro_source=macro_source, mpi_cpu_indices=CPUS, gpu=False)


def main(preflight_only):
    if c.LOCK.exists() or WAIT_LOCK.exists():
        raise RuntimeError("Another Mini controller still owns the job")
    MiniGuard().preflight()
    state = c.read(campaign.STATE)
    source, t, history = production_source(state)
    if preflight_only:
        print(f"Mini-only preflight PASS, checkpoint at {t:.7f} s")
        return

    with c.LOCK.open("x", encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        c.coex.save(STATUS, dict(mode="mini_only", mini_cpus=CPUS, priority="High",
                                 gpu=False, checkpoint=str(source), checkpoint_sha256=c.sha(source)))
        campaign.STATE_DATA.update(state)
        campaign.job = mini_job
        # Existing transport recovery calls this preflight again before retrying.
        run_day.protected_idle = MiniGuard().preflight
        campaign.status(operation="RESUMING_WAVE_FIXED", reason=None, resource_mode="mini_only",
                        physical_time_s=t, last_checkpoint=str(source))
        remaining = math.ceil((campaign.START_GATE + campaign.CYCLES * campaign.PERIOD - t) / campaign.DT)
        source, t, history = campaign.integrate(campaign.FIXED_STAGE, source, t, history, remaining)
        finish_fixed_and_run_active(source, t, history)
    except Exception as error:
        reason = c.STOP.read_text(encoding="utf8").strip() if c.STOP.exists() else str(error)
        campaign.status(operation="HOLD", reason=reason)
        raise
    finally:
        if not c.filtered_query(c.OWNER):
            c.LOCK.unlink()


if __name__ == "__main__":
    main("--preflight" in sys.argv)
