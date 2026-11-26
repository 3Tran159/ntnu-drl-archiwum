from pathlib import Path
import json, os, shutil, subprocess, sys
d=Path(__file__).resolve().parent
sys.path.insert(0,str(d.parent/"ARCHIVE_ACTIVE_FLAPS_20261105"))
from run import setup_cpu, CLI, day_chain, sha
source=Path("T:/FLAPS_ARCHIVE/SEALED_GAP_2D_U18_20261104/SHARP_SEALED_FIXED_START.sim")
copy=d/"Sharp_Sealed_Original_Mesh_REFERENCE.sim"
if not copy.exists(): shutil.copy2(source,copy)
assert sha(source)==sha(copy)
cpu=setup_cpu()
base=sys.argv[1] if len(sys.argv)>1 else "0.27"
macro=sys.argv[2] if len(sys.argv)>2 else "NativeSharpSealed.java"
case=sys.argv[3] if len(sys.argv)>3 else copy.name
tag=sys.argv[4] if len(sys.argv)>4 else "build"
env={**os.environ,**day_chain.LIC,"SHARP_NATIVE_DIR":str(d),"SHARP_BASE_M":base}
args=[CLI,"-power","-np","1","-cpubind","off","-printpids","-nbuserdir",str(d/"profile"),"-batch",str(d/macro),str(d/case)]
with (d/(tag+".log")).open("w",encoding="utf-8") as log:
    print("Native mesh job pinned to logical CPU",cpu,file=log,flush=True)
    process=subprocess.run(args,cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
(d/(tag+"_exit.json")).write_text(json.dumps({"returncode":process.returncode,"logical_cpu":cpu,"base_size_m":base}))
sys.exit(process.returncode)

