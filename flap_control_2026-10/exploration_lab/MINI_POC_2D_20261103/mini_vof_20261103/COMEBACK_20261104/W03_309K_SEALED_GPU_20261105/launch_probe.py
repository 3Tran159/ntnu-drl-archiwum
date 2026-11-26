import json
import os
from pathlib import Path
import subprocess
import sys

D = Path(__file__).resolve().parent
P = D.parent
sys.path[:0] = [str(P), str(P.parents[1])]
from run_day import CLI, FLAG
from day_chain import LIC

def main():
    case = sys.argv[1]
    if case not in ("W03", "MINI"):
        raise ValueError("Expected W03 or MINI")
    steps = int(sys.argv[2])
    source = D / ("W03_309K_ORIGINAL_COPY.sim" if case == "W03" else "MINI_INPUT_COPY.sim")
    folder = D / f"{case}_GPU_{steps}"
    folder.mkdir()
    env = {**os.environ, **LIC, "FLAP_BENCH_DIR": str(folder),
           "FLAP_BENCH_W03": str(case=="W03").lower(), "FLAP_BENCH_STEPS": str(steps)}
    gpu = subprocess.check_output(["nvidia-smi","--query-compute-apps=pid","--format=csv,noheader"],
                                  text=True, creationflags=FLAG).strip()
    if gpu:
        raise RuntimeError("GPU already has a compute process")
    with (folder/"star.log").open("w", encoding="utf8") as log:
        proc = subprocess.Popen([CLI,"-np","1","-gpgpu","auto:1","-require-gpgpu-compatibility",
                                 "-batch",str(D/"SealedGpuMotionProbe.java"),str(source)],
                                cwd=folder, env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=FLAG)
        (folder/"LAUNCH.json").write_text(json.dumps({"pid":proc.pid,"source":str(source),"steps":steps},indent=2))
        code = proc.wait()
    (folder/"EXIT.json").write_text(json.dumps({"returncode":code}))
    return code

if __name__ == "__main__":
    sys.exit(main())
