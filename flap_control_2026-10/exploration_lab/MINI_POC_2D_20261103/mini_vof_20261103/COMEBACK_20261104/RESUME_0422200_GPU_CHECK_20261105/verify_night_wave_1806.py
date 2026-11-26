import os
from pathlib import Path
from resume import c, D, P, CPUS, run_day

run_day.protected_idle()
if c.STOP.exists():
    raise RuntimeError("Stop requested")
source=P/"runs/N01_WAVE_FIXED_H010_CFL_FALLBACK_20261106_061954/CP_000300_t1.806000.sim"
expected="5c8786f63bb79fc1c2627fd2e374eb7ae77697c994c366b5f7f2c8df582dab10"
if c.sha(source)!=expected:
    raise RuntimeError("Source checksum mismatch")
with c.LOCK.open("x", encoding="ascii") as lock:
    lock.write(str(os.getpid()))
try:
    c.local.night_flap.MASK=c.coex.MASK=sum(1<<n for n in CPUS)
    result=run_day.new_job("N01_WAVE_1806000_READBACK",dict(verify=True,source=source,limit_seconds=480),
                           protection=c.NightGuard(None,1.777749),mpi_cpu_indices=CPUS)
    evidence=c.read(Path(result["run_directory"])/"REOPEN.json")
    if abs(evidence["time_s"]-1.806)>1e-9 or evidence["cells"]!=25617 or c.sha(source)!=expected:
        raise RuntimeError("Readback did not match source")
    c.coex.save(D/"NIGHT_WAVE_FINAL_READBACK.json",
                dict(status="VERIFIED", source=str(source), sha256=expected,
                     readback=result, evidence=evidence))
finally:
    if not c.filtered_query(c.OWNER):
        c.LOCK.unlink()
