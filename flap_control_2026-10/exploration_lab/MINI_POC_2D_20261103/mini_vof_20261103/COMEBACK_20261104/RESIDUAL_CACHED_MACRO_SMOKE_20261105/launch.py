import os,subprocess,sys,time
from pathlib import Path

D=Path(__file__).resolve().parent
P=D.parent
sys.path[:0]=[str(P),str(P.parents[1])]
from run_day import CLI,FLAG
from day_chain import LIC

if subprocess.check_output(["nvidia-smi","--query-compute-apps=pid","--format=csv,noheader"],
                           text=True,creationflags=FLAG).strip():
    raise RuntimeError("GPU already occupied")
props=dict(authorization="COMEBACK_DAY_20261104",stage="RESIDUAL_CACHED_MACRO_SMOKE",
    expected_cells=25617,dt=.0002,inner=20,foil="true",stokes="true",expected_time=1.0788,
    calm_only="true",clean_calm="true",matched_calm="true",amplitude=0,old_amplitude=0,
    af_native="false",gpu_requested="true",pressure_diagnostic_only="true",
    steps=25,wall_budget_s=420,deadline_ms=int((time.time()+660)*1000),
    stop_path=(D/"STOP_REQUESTED").as_posix())
(D/"job.properties").write_text("".join(f"{k}={v}\n" for k,v in props.items()),encoding="ascii")
macro=P/"RESUME_0422200_GPU_CHECK_20261105/residual_cache_macro/MiniVofStokes.java"
with (D/"star.log").open("x",encoding="utf8") as log:
    env={**os.environ,**LIC,"MINI_CASE_DIR":str(D)}
    rc=subprocess.call([CLI,"-np","1","-gpgpu","auto:1","-require-gpgpu-compatibility","-batch",
                        str(macro),str(D/"COPY.sim")],
                       cwd=D,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=FLAG)
(D/"EXIT.txt").write_text(str(rc))
