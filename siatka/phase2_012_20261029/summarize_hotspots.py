import csv,json,math
from pathlib import Path
p=Path(r"F:\ntnu\phase2_012_20261029")
r=Path(r"F:\ntnu\mesh_screening_20261028\flow012_short_20261029\postprocess")
summary={}
for name in ["velocity_above_36","cfl_above_2"]:
 with (r/(name+".csv")).open() as f:rows=[{k:float(v) for k,v in x.items()} for x in csv.DictReader(f)]
 bounds={k:[min(x[k] for x in rows),max(x[k] for x in rows)] for k in rows[0]}
 normalized=[]
 for x in rows:
  y=x["Y (m)"];c=1.19*(1-.67*max(0,(abs(y)-2.75)/2.75));le=(1.19-c)/4
  normalized.append((x["X (m)"]-le)/c)
 summary[name]={"count":len(rows),"bounds":bounds,"nominal_chordwise_fraction_bounds":[min(normalized),max(normalized)]}
(r/"hotspot_summary.json").write_text(json.dumps(summary,indent=2))
obs=json.loads((p/"observations.json").read_text(encoding="utf-8"))
note="Lokalizacja w końcowym polu: 8 komórek ma prędkość >36 m/s, a 8 ma CFL >2. Leżą przy krawędzi natarcia zwężającej się części płata, około x=0,095–0,096 m, y=4,06 m, z=−0,003 m, w warstwach pryzmatycznych. To wskazuje konkretny obszar do lokalnej kontroli siatki; nie ustala miejsca wcześniejszego piku prędkości."
if not any("Lokalizacja w końcowym polu" in x for x in obs["F18_18ms"]):obs["F18_18ms"].append(note)
(p/"observations.json").write_text(json.dumps(obs,ensure_ascii=False,indent=2),encoding="utf-8")
f=p/"build_dashboard.py";s=f.read_text(encoding="utf-8")
s=s.replace('event(F/"process.json","Uruchomienie sekwencji', 'event(F/"postprocess/hotspot_summary.json","Lokalna kontrola końcowego pola","8 komórek z prędkością >36 m/s i 8 z CFL >2 przy krawędzi natarcia części zwężającej się, y około 4,06 m. Bez kolejnych kroków solvera.")\nevent(F/"process.json","Uruchomienie sekwencji')
s=s.replace("Najpierw ocena testów 0 i 18 m/s, kosztu kroku oraz lokalnych problemów.","Najpierw lokalna kontrola pryzm przy krawędzi natarcia (y około 4,06 m), ocena rozruchu i dobór kroku czasowego względem kosztu.")
f.write_text(s,encoding="utf-8")
print(json.dumps(summary))
