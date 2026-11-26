import json,datetime
from pathlib import Path
root=Path(r"F:\ntnu\mesh_screening_20261028")
folder=root/"night_20261028"
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
path=folder/"work_log.json"
data=json.loads(path.read_text(encoding="utf-8-sig"))
event={"id":"profile-identity-20261029","time":now,"kind":"problem","work":"Weryfikacja profilu CAD wzgledem obu plikow DAT","finding":"Aktualny CAD odpowiada starszemu profilowi 010: RMS roznicy powierzchni 0.194 mm wobec 9.090 mm dla 012 (x/c 0.02-0.98). Maks. grubosc root z teselacji 118.50 mm; referencja 012: 142.77 mm. Config i metadane v02 wskazuja 012.","challenge":"Brak weryfikacji geometrii przed nocnymi testami. Dokladny etap wyboru/importu starszego profilu nieustalony. Wyniki nocne nie waliduja docelowego plata 12%.","next_step":"WSTRZYMANE nowe siatki/CFD do odtworzenia CAD z referencji 012 i pomiaru przekrojow. Zachowac camber 2.5%; nie skalowac calego Z razy 1.2. Potem dopiero siatka diagnostyczna ok. 1 mln."}
data=[e for e in data if e.get("id")!=event["id"]]+[event]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
(folder/"current_activity.json").write_text(json.dumps({"updated_at":now,"text":"WSTRZYMANE nowe siatki/CFD: CAD odpowiada profilowi 010 zamiast 012. Porownanie DAT zakonczone; wymagane odtworzenie i weryfikacja geometrii 12%."},ensure_ascii=False),encoding="utf-8")
definition=root/"block1_20261029"/"comparison_definition.json"
d=json.loads(definition.read_text(encoding="utf-8-sig"))
d["geometry_acceptance"]={"status":"HOLD_PROFILE_MISMATCH","updated_at":now,"current_profile_match":"older project 010 reconstructed DAT","intended_profile":"project 012 reconstructed DAT","next_action":"Rebuild CAD using verified 012 source; recheck section thickness, camber and planform before meshing.","source_comparison":"profile_identity_comparison.json"}
definition.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"event_id":event["id"],"status":d["geometry_acceptance"]["status"],"timestamp":now}))
