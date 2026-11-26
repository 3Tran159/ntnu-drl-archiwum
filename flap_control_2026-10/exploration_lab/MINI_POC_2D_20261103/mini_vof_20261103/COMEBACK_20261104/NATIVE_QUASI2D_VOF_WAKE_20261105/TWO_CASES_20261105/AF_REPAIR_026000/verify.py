from pathlib import Path
import os,subprocess,sys
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D.parents[2]/"ARCHIVE_ACTIVE_FLAPS_20261105"))
from run import setup_cpu,CLI,day_chain
setup_cpu()
env={**os.environ,**day_chain.LIC,"AF_REPAIR_DIR":str(D)}
args=[CLI,"-power","-np","1","-cpubind","off","-printpids","-nbuserdir",str(D/"verify_profile"),
      "-batch",str(D/"VerifyRepairedPlayback.java"),str(D/"Sharp_Sealed_VOF_AF_REPAIRED_REVIEW.sim")]
with (D/"verify_star.log").open("w",encoding="utf8") as f:
    rc=subprocess.run(args,cwd=D,env=env,stdout=f,stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS).returncode
sys.exit(rc)

