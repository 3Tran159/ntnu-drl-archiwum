import time,json,subprocess,sys,shutil
from pathlib import Path
r=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029")
(r/"M03_CPU24").mkdir(exist_ok=True)
shutil.copy2(r/"M03/topology_audit.json",r/"M03_CPU24/topology_audit.json")
deadline=time.time()+2200
while not (r/"gpu.exit.json").exists():
 if time.time()>deadline:raise RuntimeError("GPU did not finish")
 time.sleep(2)
# The GPU controller only polls resources and writes HTML after the solver has exited.
p=subprocess.Popen([sys.executable,str(r/"run_job.py"),str(r/"cpu24_job.json")])
while p.poll() is None:
 (r/"status.json").write_text(json.dumps({"activity":"Quasi-2D: porównanie 24 i 8 procesów CPU na M03","live":True},ensure_ascii=False),encoding="utf-8")
 subprocess.run([sys.executable,r"F:\ntnu\phase2_012_20261029\build_dashboard.py"],capture_output=True)
 time.sleep(10)
(r/"status.json").write_text(json.dumps({"activity":"Quasi-2D: testy zakończone; podsumowanie i wybór dalszych prób","live":False},ensure_ascii=False),encoding="utf-8")
subprocess.run([sys.executable,r"F:\ntnu\phase2_012_20261029\build_dashboard.py"],capture_output=True)
print("CPU24 benchmark finished",p.returncode)
