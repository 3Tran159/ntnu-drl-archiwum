from pathlib import Path
import json
p=Path(r"F:\ntnu\phase2_012_20261029")
f=p/"observations.json";d=json.loads(f.read_text(encoding="utf-8"))
d["F18_18ms"]=[x for x in d["F18_18ms"] if not x.startswith("Lokalizacja w końcowym polu")]
d["F18_18ms"].append("Lokalizacja w końcowym polu: 8 komórek z prędkością >36 m/s skupia się przy krawędzi natarcia około x=0,095–0,096 m, y=4,06 m, z=−0,003 m, w pryzmach 1–6. CFL >2 występuje w 6 komórkach tego obszaru i 2 przy końcówce płata (y≈5,50 m). To lokalny obszar do kontroli; nie ustala miejsca wcześniejszego piku ani nie dowodzi jeszcze przyczyny.")
f.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
f=p/"build_dashboard.py";s=f.read_text(encoding="utf-8")
s=s.replace("8 komórek z prędkością >36 m/s i 8 z CFL >2 przy krawędzi natarcia części zwężającej się, y około 4,06 m. Bez kolejnych kroków solvera.","8 komórek z prędkością >36 m/s przy y≈4,06 m; CFL >2: 6 komórek tam i 2 przy y≈5,50 m. Bez kolejnych kroków solvera.")
s=s.replace("lokalna kontrola pryzm przy krawędzi natarcia (y około 4,06 m)","lokalna kontrola pryzm przy krawędzi natarcia (y około 4,06 m) i końcówce płata")
f.write_text(s,encoding="utf-8")
f=p/"project_manifest.json";d=json.loads(f.read_text(encoding="utf-8"))
for x in d["stages"]:
 if x["id"] in ["2.1","2.2"]:x["status"]="short diagnostic completed; not production acceptance"
d["next_action"]="Review leading-edge prism cells at y≈4.06 m and tip cells at y≈5.50 m; then bounded startup/time-step test before long foil-in-waves runs"
d["long_wave_run_ready"]=False
f.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
print("Final phase-2 findings reconciled")
