import time
from run_day import HERE, LOCK, STOP
from run_sprint import run

# Separate small-wave qualification for the requested integration pilot.
end=time.monotonic()+900
proof=HERE/"B_SEEDED_URANS_DT25US_SPRINT.json"
while time.monotonic()<end and (LOCK.exists() or not proof.exists()) and not STOP.exists():
    time.sleep(6)
if LOCK.exists() or STOP.exists() or not proof.exists():
    raise RuntimeError("Previous Mini job/protection unresolved")
run("A_STOKES_H010_QUAL40",dict(fresh=True,stokes=True,foil=False,expected_time=0,
    amplitude=.05,old_amplitude=.05,steps=40,limit_seconds=720))

