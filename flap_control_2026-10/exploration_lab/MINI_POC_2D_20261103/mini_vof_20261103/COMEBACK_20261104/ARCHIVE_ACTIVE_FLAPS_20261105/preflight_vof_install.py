from pathlib import Path
import json
import os
import shutil
import subprocess
import time
from run import D,H,T,P,setup_cpu,read,sha,CLI,day_chain,filtered_query

prior=35592
pid_query=f"ConvertTo-Json -InputObject @(Get-Process -Id {prior} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id) -Compress"
while filtered_query(pid_query):
    time.sleep(12)
archive=T/"NIGHT_FLAP_20261104/CALM_VOF_FIXED_SEALED_DT020_WMI_RESUME"
source=archive/"FINAL.sim"
if sha(source)!=read(archive/"RESULT.json")["checkpoint_sha256"]:
    raise RuntimeError("Fixed VOF reference hash mismatch")
cpu=setup_cpu()
out=D/"VOF_HISTORY_PREFLIGHT_RETRY"
out.mkdir()
env={**os.environ,**day_chain.LIC,"FLAP_POST_DIR":str(out)}
args=[CLI,"-power","-np","1","-cpubind","off","-printpids","-nbuserdir",str(out/"profile"),
      "-batch",str(D/"vof_proposed/VofPlaybackPreflight.java"),str(source)]
with (out/"star.log").open("w",encoding="utf-8") as log:
    p=subprocess.run(args,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
receipt=read(out/"PREFLIGHT.json")
if p.returncode or receipt["states"]!=1 or receipt["solver_steps"] or not (out/"preflight.simh").stat().st_size:
    raise RuntimeError("Native VOF history preflight did not pass")
if any((out/f).stat().st_size<8000 for f in ("pressure.png","speed.png","streamlines.png")):
    raise RuntimeError("VOF playback previews missing data")
controller=P/"FLAP_EXTREMA_VOF5_20261105/STABILIZE_FIRST"
live=read(controller/"STATUS.json")
if live["stage"]!="CALM_VOF_SHARP_SEALED_0_STABILIZE_FIRST" or live["motion_authorized"]:
    raise RuntimeError("Current VOF is no longer on the fixed stage; update requires review")
macro=controller/"MiniVofStokes.java"
bak=D/"BEFORE_NATIVE_VOF_PLAYBACK.java"
if bak.exists():
    raise RuntimeError("VOF playback was already installed")
shutil.copy2(macro,bak)
incoming=controller/"MiniVofStokes.java.playback_pending"
shutil.copy2(D/"vof_proposed/MiniVofStokes.java",incoming)
os.replace(incoming,macro)
receipt.update(installed=True,macro=str(macro),macro_sha256=sha(macro),isolated_cpu=cpu)
(controller/"NATIVE_PLAYBACK_ARMED.json").write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2),flush=True)


