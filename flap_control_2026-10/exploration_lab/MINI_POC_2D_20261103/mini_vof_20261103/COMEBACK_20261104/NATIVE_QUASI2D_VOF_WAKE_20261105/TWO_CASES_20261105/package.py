from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys

D=Path(__file__).resolve().parent
P=D.parent.parent
S=Path(sys.argv[1])
sys.path.insert(0,str(P/"ARCHIVE_ACTIVE_FLAPS_20261105"))
from run import setup_cpu,CLI,day_chain,sha
meta=json.loads((S/"AF_PLAYBACK_FINAL.json").read_text())
cpu=setup_cpu()
checks={}
for tag,checkpoint in (("01_REMESH_START","START.sim"),("02_RUN","FINAL.sim")):
    out=D/tag
    out.mkdir()
    source=out/"SOURCE_COPY.sim"
    shutil.copy2(S/checkpoint,source)
    if sha(source)!=sha(S/checkpoint): raise RuntimeError("Checkpoint copy mismatch")
    if tag=="02_RUN":
        shutil.copy2(S/meta["history_file"],out/meta["history_file"])
    env={**os.environ,**day_chain.LIC,"NATIVE_PACKAGE_DIR":str(out)}
    args=[CLI,"-power","-np","1","-cpubind","off","-printpids","-nbuserdir",str(out/"profile"),
        "-batch",str(D/"PackageNativeVof.java"),str(source)]
    with (out/"star.log").open("w",encoding="utf-8") as log:
        cp=subprocess.run(args,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,
           creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
    receipt=out/"PACKAGE_RECEIPT.txt"
    if cp.returncode or not receipt.is_file(): raise RuntimeError(f"{tag} STAR packaging failed, see {out/'star.log'}")
    checks[tag]={"source":str(S/checkpoint),"source_sha256":sha(source),"receipt":receipt.read_text()}
    (D/"PACKAGE_STATUS.json").write_text(json.dumps(checks,indent=2))

