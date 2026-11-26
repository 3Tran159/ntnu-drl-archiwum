"""First offline NWAR mesh candidate retaining the exact project foil contour."""
import json
from pathlib import Path
from run_day import ROOT,sha

out=ROOT/"MINI_NWAR_50K_20261104"/"MESH_CANDIDATE_02"
if out.exists():
    raise FileExistsError(out)
source=ROOT/"prepare_vof_foil.py"
s=source.read_text(encoding="utf8")
s=s.replace("ROOT=Path(__file__).resolve().parent",f"ROOT=Path({str(ROOT)!r})")
s=s.replace("out=ROOT/'mini_vof_20261103'/'SEALED0_A005';out.mkdir(exist_ok=True)",f"out=Path({str(out)!r});out.mkdir()")
s=s.replace("sy=2.02128173276777","sy=2.0").replace("ys=[-10,yb,yt,4]","ys=[-22,yb,yt,8]")
s=s.replace("geo.addPoint(-12,y,0)","geo.addPoint(-35,y,0)").replace("geo.addPoint(28,y,0)","geo.addPoint(45,y,0)")
s=s.replace("setTransfiniteCurve(h[i],321)","setTransfiniteCurve(h[i],501)")
s=s.replace("setTransfiniteCurve(side[1],65)","setTransfiniteCurve(side[1],49)")
s=s.replace("setTransfiniteCurve(side[2],25","setTransfiniteCurve(side[2],27")
s=s.replace("'SizeMin',.009","'SizeMin',.013").replace("'SizeMax',.65","'SizeMax',.85")
s=s.replace("'SizeMin',.125","'SizeMin',.20").replace("'Sampling',321","'Sampling',501")
s=s.replace("'Size',.00002","'Size',.00010").replace("'Thickness',.0009","'Thickness',.002")
exec(compile(s,str(source),"exec"),{"__file__":str(source)})
source=ROOT/"extrude_foil_vof.py"
s=source.read_text(encoding="utf8").replace("R=Path(__file__).resolve().parent",f"R=Path({str(ROOT)!r})")
anchor="D=R/'mini_vof_20261103';src=D/'SEALED0_A005';o=D/'Q2D_SEALED0_CALM_PREPARED';"
assert s.count(anchor)==1
s=s.replace(anchor,f"src=Path({str(out)!r});o=Path({str(out/'Q2D')!r});")
s=s.replace("faces={}","nodes=np.column_stack((nodes[:,0],.03-nodes[:,2],nodes[:,1]));faces={}")
s=s.replace("for zid,(name,fs) in enumerate(zones.items(),2):",
    "boundary_names={'main':'HF_012_main','flap':'HF_012_flap','inlet':'DOMAIN.inlet','outlet':'DOMAIN.outlet','top':'DOMAIN.top','bottom':'DOMAIN.bottom','span_front':'Q2D_span_target','span_back':'Q2D_span_source'}\n for zid,(name,fs) in enumerate(zones.items(),2):")
s=s.replace("f' {name})())","f' {boundary_names.get(name,name)})())").replace("45 (1 fluid MINI_water_air)","45 (1 fluid fluid)")
exec(compile(s,str(source),"exec"),{"__file__":str(source)})
mesh=out/"Q2D"/"mesh_3d.msh"
meta=json.loads((out/"mesh_metadata.json").read_text())
audit=dict(status="OFFLINE_CANDIDATE",cells=meta["cells"],within_target=50000<=meta["cells"]<=65000,
           min_volume_m3=.02*meta["min_area_m2"],min_SICN=meta["min_SICN"],nonpositive=meta["nonpositive_cells"],
           native_mesh=str(mesh),mesh_sha256=sha(mesh),x_bounds_m=[-35,45],z_bounds_m=[-22,8],
           span_y_bounds_m=[.01,.03],waterline_z_m=2,hinge_xyz_m=[.952,.02,.02128173276777],
           unchanged_foil_definition=meta["source_sha256"],one_span_layer=True,
           C01_physics_not_yet_mapped=True,native_mesh_import_verified=False,motion_verified=False)
(out/"NWAR_MESH_AUDIT.json").write_text(json.dumps(audit,indent=2))
print(json.dumps(audit,indent=2))


