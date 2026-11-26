import json,datetime
from pathlib import Path
r=Path(r"F:\ntnu\mesh_screening_20261028")
p=r/"night_20261028"
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
f=p/"work_log.json"
log=json.loads(f.read_text(encoding="utf-8-sig"))
e={"id":"geometry-012-corrected-20261029","time":now,"kind":"finding","work":"Naprawa geometrii w NX i weryfikacja importu STAR","finding":"HF_v2.prt oraz HF_v2.x_t zawieraly profil 010. Zapisano HF_012_v3.prt i .x_t; nowy profil ma 11.9979% grubosci i 2.5003% wygiecia. 7 przekrojow sprawdzonych, zamknieta bryla, odchylki sprawdzonych punktow DAT <0.01 mm. STAR: S_full=10.900869 m2, S_half=5.450434 m2. Oryginaly zachowane.","challenge":"Aktualizacja starego obiektu 3D-CAD w STAR zakonczyla probe bledem; niezalezny import nowego Parasolidu i ponowne przypisanie Boolean/wall/mesh controls zostaly wykonane i zweryfikowane. Nocne wyniki nadal dotycza 010.","next_step":"C001_012: uruchomiono zgrubne siatkowanie nowej geometrii. Cel ok. 1 mln komorek do diagnostyki; solver nieuruchomiony. Pozniej ocena jakosci, pryzm i kosztu."}
log=[x for x in log if x.get("id")!=e["id"]]+[e]
f.write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding="utf-8")
(p/"current_activity.json").write_text(json.dumps({"updated_at":now,"text":"Geometria 012 poprawiona i sprawdzona w NX/STAR. Trwa C001_012: zgrubna siatka diagnostyczna, docelowo ok. 1 mln komorek. Solver nie jest uruchomiony."},ensure_ascii=False),encoding="utf-8")
d=r/"block1_20261029"/"comparison_definition.json"
v=json.loads(d.read_text(encoding="utf-8-sig"))
v["geometry_acceptance"]={"status":"GEOMETRY_VERIFIED_FOR_MESHING","updated_at":now,"new_cad":r"F:\ntnu\geometry_012_20261029\HF_012_v3.x_t","new_baseline":r"F:\ntnu\geometry_012_20261029\HF_012_baseline_unmeshed.sim","reference_area_full_m2":10.900868608830482,"reference_area_half_m2":5.450434304415241,"note":"Old night cases remain 010; keep their original force normalization. CFD and mesh suitability not yet validated."}
d.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding="utf-8")
print("Geometry correction logged; C001 pending.")
