from pathlib import Path
import json
import os
import sys
import time

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D.parents[1]))
import stokes_coexistence as coex
from run_day import LOCK, STOP, new_job, sha
from run_recovery_calm_komega import protect_w06

result = D/"NOSE_READBACK_RESULT.json"
record = json.loads((D/"RESULT.json").read_text())["BASELINE"]
source = Path(record["checkpoint"])
if STOP.exists() or result.exists() or sha(source) != record["checkpoint_sha256"]:
    raise RuntimeError("Nose readback blocked by STOP, duplicate, or checkpoint identity")
with LOCK.open("x", encoding="ascii") as f:
    f.write(str(os.getpid()))
try:
    guard = protect_w06("ACTIVE_GAP25_NOSE_READ_" + time.strftime("%H%M%S"))
    readback = new_job("ACTIVE_GAP25_NOSE_READ", dict(verify=True, source=source, limit_seconds=460),
                       protection=guard, macro_source=D/"VerifyComeback.java")
    readback["W06"] = dict(peak=guard.peak, stop=guard.stopped) if guard else None
    readback["original_hash_verified"] = sha(source)==record["checkpoint_sha256"]
    coex.save(result, readback)
except Exception as e:
    coex.save(result, dict(status="HOLD",error=str(e)))
    raise
finally:
    LOCK.unlink()

