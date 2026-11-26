import subprocess,json,time,sys,shutil
from pathlib import Path
r=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029")
assert json.loads((r/"cpu24.exit.json").read_text())["returncode"]==0
(r/"M03_GPU").mkdir(exist_ok=True);shutil.copy2(r/"M03/topology_audit.json",r/"M03_GPU/topology_audit.json")
p=subprocess.Popen([sys.executable,str(r/"run_gpu_job.py"),str(r/"gpu_m03_job.json")])
samples=[]
while p.poll() is None:
 (r/"status.json").write_text(json.dumps({"activity":"Quasi-2D: końcowe porównanie M03 na GPU do t=0,2 s","live":True},ensure_ascii=False),encoding="utf-8")
 g=subprocess.run(["nvidia-smi","--query-gpu=utilization.gpu,memory.used,power.draw","--format=csv,noheader,nounits"],capture_output=True,text=True)
 samples.append({"unix":time.time(),"gpu":g.stdout.strip()});(r/"gpu_m03_resources.json").write_text(json.dumps(samples))
 subprocess.run([sys.executable,r"F:\ntnu\phase2_012_20261029\build_dashboard.py"],capture_output=True)
 time.sleep(10)
(r/"status.json").write_text(json.dumps({"activity":"Quasi-2D: wszystkie próby zakończone, podsumowanie wyników","live":False},ensure_ascii=False),encoding="utf-8")
subprocess.run([sys.executable,r"F:\ntnu\phase2_012_20261029\build_dashboard.py"],capture_output=True)
print("M03 GPU benchmark finished",p.returncode)
