from pathlib import Path
import json,os,shutil,subprocess,sys,time
D=Path(__file__).resolve().parent
P=D.parents[2]
sys.path.insert(0,str(P/"ARCHIVE_ACTIVE_FLAPS_20261105"))
from run import setup_cpu,CLI,day_chain,sha
src=P/"runs/CALM_VOF_NATIVE_FULL_BAND_FIXED_STABILIZE_20261105_142054"
checkpoint=src/"CP_000025_t0.026000.sim"
source=json.loads((src/"AF_RESUME_HISTORY.json").read_text())
for path in (checkpoint,Path(source["path"]),Path(source["archive_path"])):
    for _ in range(4):
        first=sha(path)
        shutil.copy2(path,D/path.name)
        if sha(path)==first==sha(D/path.name):break
        time.sleep(2)
    else: raise RuntimeError("Could not capture stable copy of "+path.name)
cpu=setup_cpu()
env={**os.environ,**day_chain.LIC,"AF_REPAIR_DIR":str(D)}
args=[CLI,"-power","-np","1","-cpubind","off","-printpids","-nbuserdir",str(D/"profile"),
      "-batch",str(D/"RepairPlayback.java"),str(D/checkpoint.name)]
with (D/"star.log").open("w",encoding="utf-8") as f:
    ret=subprocess.run(args,cwd=D,env=env,stdout=f,stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
sys.exit(ret.returncode)

