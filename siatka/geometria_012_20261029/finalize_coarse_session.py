import json, datetime, pathlib, subprocess, sys
root=pathlib.Path(r"F:\ntnu\mesh_screening_20261028")
geo=pathlib.Path(r"F:\ntnu\geometry_012_20261029")
night=root/"night_20261028"
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(p): return json.loads(p.read_text(encoding="utf-8-sig"))
def write(p,d): p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
m=read(root/"coarse012_C003/measurement.json")["metrics"]
sim=root/"coarse012_C003/HF_012_C003_mesh.sim"
assert sim.is_file() and sim.stat().st_size>100000000
assert read(root/"coarse012_C003/mesh_exit.json")["returncode"]==0
event={"id":"coarse012-completed-20261029","time":now,"kind":"finding",
"work":"Geometria 012: gotowa siatka diagnostyczna 1,165 mln komórek",
"finding":"C001: 9 534 590; C002: 6 037 861; C003: 1 165 391 komórek. C003: 19,2 s samego siatkowania, zero komórek o ujemnej objętości, otwartych i zdegenerowanych. Zapis: "+str(sim)+". Solver nieuruchomiony.",
"challenge":"C003: dowolne pryzmy pokrywają 100% pola płata; pełne 15 warstw tylko 94,560%. 187 komórek z quality <0,01 i 283 ze skewness >80°. Przydatność produkcyjna NWAR pozostaje niepotwierdzona.",
"next_step":"Lokalna kontrola pryzm i krótki test hydrostatyczny (0 m/s), następnie 18 m/s: koszt kroku, CFL, y+ i historia sił. Dopiero potem decyzja o długim przebiegu."}
events=read(night/"work_log.json")
events=[e for e in events if e.get("id")!=event["id"]]+[event]
write(night/"work_log.json",events)
write(night/"current_activity.json",{"updated_at":now,"text":"Zakończono: geometria 012 poprawiona i zweryfikowana; C003 ma 1 165 391 komórek. Pliki zapisane, solver nieuruchomiony. Pełne 15 pryzm na 94,560% pola — wymaga lokalnej kontroli. Następny etap: krótki test 0 m/s, potem 18 m/s, y+, siły i koszt kroku."})
p=root/"block1_20261029/comparison_definition.json";d=read(p)
if "historical_geometry_010" not in d:
    d["historical_geometry_010"]=d["geometry"]
    d["historical_geometry_010"]["note"]="Original geometry for the old A/B/D cases; old force normalization remains unchanged."
v=read(geo/"geometry_verified.json")
st=next(x for x in v["star"]["stations"] if x["y_m"]==0)
d["geometry"]={**d["geometry"],
"S_ref_full_projected_m2":v["star"]["projected_planform_m2"],
"S_ref_half_projected_m2":v["star"]["projected_planform_m2"]/2,
"mean_geometric_chord_m":v["star"]["projected_planform_m2"]/11,
"measured_max_vertical_root_thickness_c":st["max_thickness_c"],
"measured_max_root_camber_c":st["max_camber_c"],
"profile_identity":"HF_012_v3; checked against the project's reconstructed 012 DAT, not independent published-profile validation",
"source":str(geo/"geometry_verified.json")}
d["C0"]["minimum_foil_clearance_m"]=d["C0"]["free_surface_z_m"]-v["star"]["bounds_m"][2][1]
d["C0"]["status"]="Definition for corrected geometry; no new solver run performed"
d["mesh_strategy"].update({"status":"C003_012 generated for solver diagnostics; production suitability unconfirmed",
"selected_case":"C003_012","actual_cells":m["cell_count"],"mesh_sim":str(sim),
"full_15_prism_area_fraction":m["foil_area_fraction_full_15_prism_layers"],
"solver_iterations":0})
d["status"]="Corrected 012 geometry verified; 1,165,391-cell diagnostic mesh saved; CFD convergence not established"
d["updated_at"]=now
d["source_integrity"]["scope"]="Historical 010 audit copy; corrected baseline hash recorded separately"
d["source_integrity"]["corrected_012_baseline_sha256"]=v["baseline_sha256"]
write(p,d)
p=geo/"README_GEOMETRY.txt";s=p.read_text(encoding="utf-8")
s=s.split("NEXT CASES")[0]+"""COMPLETED MESH-ONLY TRIALS
C001: 9,534,590 cells; C002: 6,037,861 cells; C003: 1,165,391 cells.
Current diagnostic candidate:
F:\\ntnu\\mesh_screening_20261028\\coarse012_C003\\HF_012_C003_mesh.sim
C003: zero negative-volume, unclosed or degenerated cells.
Any prism layers cover 100% of foil area; all 15 cover 94.559651%.
Minimum quality 5.0866e-5; minimum volume change 0.0110144; maximum skewness 84.9958 degrees.
Local review flags: 187 cells below quality 0.01; 283 above skewness 80 degrees.
Nominal prism settings retained: 15 layers, first height 0.1799 mm, total 15.46 mm.
C003 meshing time 19.2 s excludes startup, reports and file I/O.
All three cases have zero solver iterations. No new y+, forces, CL or CD are available.

NEXT CHECK
Review local prism collapse and quality flags; short hydrostatic startup at 0 m/s,
then an 18 m/s diagnostic run to measure runtime, CFL, wall y+ and force behavior.
Geometry verification is not hydrodynamic validation. The mesh is not approved
for production NWAR comparison; force/time/mesh sensitivity remain to be checked.
"""
p.write_text(s,encoding="utf-8")
# Correct an exported explanatory label; threshold mode and reported values were already correct.
for folder in sorted(root.glob("coarse012_C*")):
    p=folder/"measurement.json";a=read(p)
    a["notes"]=[s.replace("Diagnostic SkewnessAngle < ","Diagnostic SkewnessAngle > ") for s in a.get("notes",[])]
    write(p,a)
    p=folder/"Coarse012.java";s=p.read_text(encoding="utf-8")
    old='notes.add("Diagnostic "+name+" < "+cutoff+'
    new='notes.add("Diagnostic "+name+(above?" > ":" < ")+cutoff+'
    if old in s:
        backup=folder/"Coarse012.executed.java.txt"
        if not backup.exists(): backup.write_text(s,encoding="utf-8")
        p.write_text(s.replace(old,new),encoding="utf-8")
subprocess.run([sys.executable,str(night/"update_dashboard.py"),str(root)],check=True)
html=(root/"dashboard.html").read_text(encoding="utf-8")
assert html.count('id="geometry012"')==1
for expected in ["C003_012","1,165,391","94.560%","coarse012-completed-20261029"]:
    assert expected in html,expected
print(json.dumps({"status":"completed","mesh_path":str(sim),"mesh_bytes":sim.stat().st_size,
"mesh_returncode":0,"cell_count":m["cell_count"],"dashboard_verified":True,"updated_at":now},ensure_ascii=False))
