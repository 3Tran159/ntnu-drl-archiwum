from pathlib import Path
import os,shutil,subprocess,sys,json
d=Path(__file__).resolve().parent
p=d.parent
sys.path.insert(0,str(p/"ARCHIVE_ACTIVE_FLAPS_20261105"))
from run import setup_cpu,CLI,day_chain,sha
run=p/"runs/CALM_VOF_SHARP_SEALED_0_STABILIZE_FIRST_20261105_130636"
source=run/"FINAL.sim"
expect="e9467516b387e7e5f58a1020ef46ffb0159f4e38db0d8acd6803b2c13c4c5a34"
status=json.loads((p/"DAY_STATUS.json").read_text())
assert status["solver_state"]=="STOPPED" and not (p/"CONTROLLER.lock").exists()
assert sha(source).lower()==expect
copy=d/"PAUSED_VOF_SOURCE_COPY.sim"
if not copy.exists(): shutil.copy2(source,copy)
assert sha(copy).lower()==expect
cpu=setup_cpu()
env={**os.environ,**day_chain.LIC,"NATIVE_VOF_DIR":str(d)}
args=[CLI,"-power","-np","1","-cpubind","off","-printpids","-nbuserdir",str(d/"profile"),
      "-batch",str(d/"BuildNativeVof.java"),str(copy)]
tag=sys.argv[1] if len(sys.argv)>1 else "build"
if tag=="verify":
    args[-2:]=[str(d/"VerifyNativeVof.java"),str(d/"PAUSED_VOF_SOURCE_COPY@meshed.sim")]
with (d/(tag+".log")).open("w",encoding="utf-8") as f:
    print("Native meshing only; logical CPU",cpu,file=f,flush=True)
    ret=subprocess.run(args,cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
(d/(tag+"_exit.json")).write_text(json.dumps({"returncode":ret.returncode,"logical_cpu":cpu}))
sys.exit(ret.returncode)

