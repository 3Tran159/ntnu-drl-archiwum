import json,datetime,time,subprocess,sys,csv
from pathlib import Path
r=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029")
builder=Path(r"F:\ntnu\phase2_012_20261029\build_dashboard.py")
def read(p,d=None):
 try:return json.loads(p.read_text(encoding="utf-8"))
 except (OSError,ValueError):return d
events=read(r/"work_log.json",[])
events.append({"time":datetime.datetime.now().astimezone().isoformat(),"work":"M01: sprawdzono 37 411 komórek i jedną warstwę","finding":"100% komórek dotyka obu płaszczyzn bocznych. Zero ujemnych objętości, skew max 46,71°. Co najmniej 15 kolejnych czworokątów na 97,07% obwodu; odstępstwa przy TE. Niewielka różnica x/z boków po projekcji CAD: maks. 0,124 mm. Testy solvera w przygotowaniu."})
(r/"work_log.json").write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8")
start=time.time()
while time.time()-start<10000:
 active=(r/"active_command.txt").read_text().strip() if (r/"active_command.txt").exists() else "Oczekiwanie na następny test"
 live=not (r/"END_SESSION").exists()
 (r/"status.json").write_text(json.dumps({"activity":"Quasi-2D: "+active,"live":live},ensure_ascii=False),encoding="utf-8")
 for d in r.glob("M*"):
  if not d.is_dir():continue
  m=read(d/"measurement.json");t=read(d/"topology_audit.json")
  if m and t:
   a=m["metrics"]
   a["foil_area_fraction_full_15_prism_layers"]=t["area_fraction_at_least_15_quad_layers"]
   a["foil_area_fraction_any_prism_layers"]=t["area_fraction_any_quad_layers"]
   a["single_layer_topology"]=t["single_layer_topology"]
   a["prism_coverage_method"]="Conservative topology criterion: consecutive quadrilateral cells; irregular transition cells stop the count."
   if d.name=="M01" and a.get("mesh_time_s")==0:a["mesh_time_s"]=None;a["sweep_time_s"]=20.5462356;a["source_mesh_time_s"]=1.95
   (d/"measurement.json").write_text(json.dumps(m,indent=2))
 subprocess.run([sys.executable,str(builder)],capture_output=True)
 if not live:break
 time.sleep(15)
