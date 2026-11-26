import json,hashlib,shutil,datetime
from pathlib import Path
r=Path(r"F:\ntnu\geometry_012_20261029")
d=json.loads((r/"geometry_acceptance.json").read_text())
nx=d["sources"]["native_012_fine_mm.stl"]
star=d["sources"]["star_012_verified_m.stl"]
for a in [nx,star]:
    assert a["closed_two_faces_per_edge"],"Open CAD tessellation"
    assert len(a["stations"])==7
    for p in a["stations"]:
        assert abs(p["max_thickness_c"]-.12)<.0001,(a["file"],p)
        assert abs(p["max_camber_c"]-.025)<.0001,(a["file"],p)
        assert p["source_point_max_deviation_mm"]<.05,(a["file"],p)
        assert p["source_points_matched"]>=159
assert abs(star["volume_m3"]/nx["volume_m3"]-1)<.001
assert abs(star["projected_planform_m2"]/nx["projected_planform_m2"]-1)<.0002
source=r/"HF_012_baseline_unmeshed.sim"
out=Path(r"F:\ntnu\mesh_screening_20261028\coarse012_C001")
target=out/"baseline_copy.sim"
assert not target.exists(),"Do not overwrite case baseline"
shutil.copy2(source,target)
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert h(source)==h(target)
gate={"status":"GEOMETRY_VERIFIED_FOR_MESHING","time":datetime.datetime.now(datetime.timezone.utc).isoformat(),"baseline_sha256":h(target),"native":nx,"star":star,"scope":"CAD section, closed tessellation, unchanged planform/pose, corrected Boolean inputs and wall mapping. No claim of hydrodynamic validation."}
(out/"GEOMETRY_VERIFIED.json").write_text(json.dumps(gate,indent=2))
(r/"geometry_verified.json").write_text(json.dumps(gate,indent=2))
print(json.dumps({"status":gate["status"],"star":star,"volume_relative_difference":star["volume_m3"]/nx["volume_m3"]-1},indent=2))
