from pathlib import Path
import json
import sys

from run_day import HERE, ROOT, sha
sys.path.insert(0,str(HERE/"WALL_FUNCTIONS_AUDIT"))
from audit_wall import load_mesh
from prepare_high_yplus_v2 import check

OUT=HERE/"WALL_FUNCTIONS_AUDIT"/"COARSE_FACETED_LARGE_CELLS"
if OUT.exists():
    raise FileExistsError(OUT)
poly=r'''
def simplified_foil():
 source,_=sealed(0)
 lower_hinge,upper_hinge=np.flatnonzero(abs(source[:,0]-.952)<1e-8)
 tip=int(np.argmax(source[:,0]))
 lo=np.where(source[lower_hinge:tip,0]<=1.16)[0][-1]+lower_hinge
 hi=np.where(source[tip:upper_hinge,0]<=1.16)[0][0]+tip
 def resample(points,step=.035):
  s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
  q=np.linspace(0,s[-1],max(1,int(np.ceil(s[-1]/step)))+1)
  return np.column_stack([np.interp(q,s,points[:,j]) for j in range(2)])
 # Keep the hinge split. Replace the needle tip with a 20 mm blunt edge.
 first=resample(source[:lower_hinge+1])
 second=resample(np.vstack([source[lower_hinge:lo+1],[1.19,-.010]]))
 third=resample(np.vstack([[1.19,.010],source[hi:upper_hinge+1]]))
 last=resample(np.vstack([source[upper_hinge:],source[0]]))
 a=np.vstack([first[:-1],second,third,last[1:-1]])
 labels=["flap" if .5*(a[i,0]+a[(i+1)%len(a),0])>.952+1e-10 else "main" for i in range(len(a))]
 return a,labels
'''
original=ROOT/"prepare_vof_foil.py"
src=original.read_text(encoding="utf8")
src=src.replace("ROOT=Path(__file__).resolve().parent",f"ROOT=Path({str(ROOT)!r})")
src=src.replace("out=ROOT/'mini_vof_20261103'/'SEALED0_A005';out.mkdir(exist_ok=True)",f"out=Path({str(OUT)!r});out.mkdir()")
src=src.replace("a,labels=sealed(0);",poly+"\na,labels=simplified_foil();")
src=src.replace("setTransfiniteCurve(h[i],321)","setTransfiniteCurve(h[i],65)")
src=src.replace("setTransfiniteCurve(side[1],65)","setTransfiniteCurve(side[1],33)")
src=src.replace("'SizeMin',.009","'SizeMin',.045").replace("'SizeMin',.125","'SizeMin',.625")
src="\n".join(line for line in src.splitlines() if "fld.setAsBoundaryLayer(bl)" not in line)+"\n"
src=src.replace("original modified NACA66-012 sealed demonstrator","faceted modified NACA66-012 derivative, sealed, blunt 20 mm TE")
exec(compile(src,str(original),"exec"),{"__file__":str(original)})
p=OUT/"geometry_and_mesh.msh"
xy,cells,walls=load_mesh(p)
kin=check(xy,cells)
if any(q["nonpositive_cells_or_corners"] for q in kin):
    raise RuntimeError("Coarse mesh failed full-range offline motion audit")
meta_path=OUT/"mesh_metadata.json"
meta=json.loads(meta_path.read_text())
meta.update(kinematic_grid_check=kin,blunt_TE_m=.020,wall_sampling_target_m=.035,first_layer_m=None)
meta_path.write_text(json.dumps(meta,indent=2))
original=ROOT/"extrude_foil_vof.py"
src=original.read_text(encoding="utf8").replace("R=Path(__file__).resolve().parent",f"R=Path({str(ROOT)!r})")
anchor="D=R/'mini_vof_20261103';src=D/'SEALED0_A005';o=D/'Q2D_SEALED0_CALM_PREPARED';"
if src.count(anchor)!=1:
    raise RuntimeError("Unexpected extrusion source")
src=src.replace(anchor,f"src=Path({str(OUT)!r});o=Path({str(OUT/'Q2D')!r});")
exec(compile(src,str(original),"exec"),{"__file__":str(original)})
mesh=OUT/"Q2D"/"mesh_3d.msh"
report=dict(mesh=str(mesh),mesh_sha256=sha(mesh),cells=meta["cells"],min_SICN=meta["min_SICN"],
    min_volume_m3=.02*meta["min_area_m2"],foil_area_m2=meta["foil_area_m2"],buoyancy_N=.02*meta["buoyancy_N_per_m"],
    minimum_volume_during_motion=min(v["min_volume_m3"] for v in kin),
    status="OFFLINE_MESH_MOTION_PASS",blunt_TE_m=.020,first_layer_m=None,interface_dx_m=.625,
    original_foil_unchanged=True)
(OUT/"COARSE_AUDIT.json").write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))



