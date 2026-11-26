import os,subprocess,sys
from pathlib import Path

D=Path(__file__).resolve().parent
P=D.parent
sys.path[:0]=[str(P),str(P.parents[1])]
from run_day import CLI,FLAG
from day_chain import LIC

if subprocess.check_output(["nvidia-smi","--query-compute-apps=pid","--format=csv,noheader"],
                           text=True,creationflags=FLAG).strip():
    raise RuntimeError("GPU already occupied")
with (D/"star.log").open("x",encoding="utf8") as log:
    env={**os.environ,**LIC,"FLAP_BENCH_DIR":str(D)}
    rc=subprocess.call([CLI,"-np","1","-gpgpu","auto:1","-require-gpgpu-compatibility","-batch",
                        str(D/"MonitorReuseProbe.java"),str(D/"COPY.sim")],
                       cwd=D,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=FLAG)
(D/"EXIT.txt").write_text(str(rc))
