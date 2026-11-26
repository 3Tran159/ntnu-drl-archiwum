import time,json,subprocess,sys,datetime
from pathlib import Path
r=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029")
deadline=time.time()+1800
while not (r/"session.exit.json").exists():
 if time.time()>deadline:raise RuntimeError("CPU session did not finish")
 time.sleep(2)
assert json.loads((r/"session.exit.json").read_text())["returncode"]==0
assert (r/"M03/sequence_completed.json").exists()
assert (r/"M02/F18_dt500us/prepared.sim").exists()
p=subprocess.Popen([sys.executable,str(r/"run_gpu_job.py"),str(r/"gpu_job.json")],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
samples=[];lastbuild=0
while p.poll() is None:
 (r/"status.json").write_text(json.dumps({"activity":"Quasi-2D: test GPU na M02 (uruchamianie lub obliczenia)","live":True},ensure_ascii=False),encoding="utf-8")
 result=subprocess.run(["nvidia-smi","--query-gpu=name,utilization.gpu,memory.used,power.draw","--format=csv,noheader,nounits"],capture_output=True,text=True)
 samples.append({"time":time.time(),"gpu":result.stdout.strip()})
 (r/"gpu_resources.json").write_text(json.dumps(samples,indent=2))
 subprocess.run([sys.executable,str(Path(r"F:\ntnu\phase2_012_20261029\build_dashboard.py"))],capture_output=True)
 time.sleep(10)
output=p.stdout.read();print(output)
(r/"status.json").write_text(json.dumps({"activity":"Quasi-2D: testy CPU i próba GPU zakończone; analiza wyników","live":False},ensure_ascii=False),encoding="utf-8")
subprocess.run([sys.executable,str(Path(r"F:\ntnu\phase2_012_20261029\build_dashboard.py"))],capture_output=True)
print("GPU controller finished")
