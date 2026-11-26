"""Read-only M09/M10 short-domain mesh comparison; writes this review only."""
import os,sys,json,csv,hashlib,datetime
from pathlib import Path
for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):os.environ[k]="1"
R=Path(r"F:/ntnu/mesh_screening_20261028/force_stabilization_20261029")
Q=R.parent/"quasi2d_012_20261029"
sys.path.insert(0,str(Q/"deps311"))
import numpy as np,h5py
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(2**20),b""):h.update(b)
 return h.hexdigest()
def stats(v):
 v=np.asarray(v,dtype=float)
 return {"min":float(v.min()),"median":float(np.median(v)),"p95":float(np.quantile(v,.95)),"max":float(v.max())} if len(v) else None
def mesh_audit(mesh):
 p=Q/mesh;src=p/"mesh.CGNS";polys=[];records=[];bounds=[]
 with h5py.File(src,"r") as f:
  z=f["Base/fluid"];xyz=np.column_stack([z["GridCoordinates/Coordinate"+a+"/ data"][...] for a in "XYZ"])
  g=z["Q2D_span_source"];off=g["ElementStartOffset/ data"][...];con=g["ElementConnectivity/ data"][...]-1
  for i in range(len(off)-1):
   poly=xyz[con[off[i]:off[i+1]]][:,[0,2]];lo=poly.min(axis=0);hi=poly.max(axis=0)
   if hi[1]<=1.7 or lo[1]>=2.3:continue
   area=abs(np.dot(poly[:,0],np.roll(poly[:,1],-1))-np.dot(poly[:,1],np.roll(poly[:,0],-1)))/2
   polys.append(poly);bounds.append([*lo,*hi])
   records.append([poly[:,0].mean(),poly[:,1].mean(),*lo,*hi,hi[0]-lo[0],hi[1]-lo[1],area])
  a=np.array(records);b=np.array(bounds)
  def summary(mask):
   v=a[mask]
   if not len(v):return {"cells":0}
   def weighted_stats(col):
    x=v[:,col];out=stats(x);idx=np.argsort(x);c=np.cumsum(v[idx,8]);out["area_weighted_p95"]=float(x[idx[np.searchsorted(c,.95*c[-1])]]);return out
   dx=weighted_stats(6);dz=weighted_stats(7)
   return {"cells":len(v),"bbox_dx_m":dx,"bbox_dz_m":dz,"area_fraction_bbox_dz_above_0p025":float(v[v[:,7]>.0250001,8].sum()/v[:,8].sum()),"area_fraction_bbox_dx_above_0p25":float(v[v[:,6]>.2500001,8].sum()/v[:,8].sum()),"lambda20_over_max_bbox_dx":20/dx["max"],"height0p5_over_max_bbox_dz":.5/dz["max"]}
  def intervals(axis,value):
   ids=np.where((b[:,axis]<=value)&(b[:,axis+2]>value))[0];out=[]
   for i in ids:
    poly=polys[i];hits=[]
    for u,v in zip(poly,np.roll(poly,-1,axis=0)):
     if min(u[axis],v[axis])<=value<max(u[axis],v[axis]):
      hits.append(u[1-axis]+(value-u[axis])/(v[axis]-u[axis])*(v[1-axis]-u[1-axis]))
    hits.sort()
    for lo,hi in zip(hits[::2],hits[1::2]):
     if hi-lo>1e-12:out.append((float(lo),float(hi)))
   return out
  def ray_stats(iv,lo,hi):
   v=[(a,b) for a,b in iv if b>lo+1e-10 and a<hi-1e-10]
   lengths=np.array([b-a for a,b in v])
   return {"crossed_cells_including_partial":len(v),"coverage_m":sum(min(b,hi)-max(a,lo) for a,b in v),"full_intersection_length_m":stats(lengths)}
  vertical=[]
  for x in [-11.8,-10,-5,-1,.01,.3,.6,.9,1.18,2,5,10,20,25,30.8]:
   iv=intervals(0,x);vertical.append({"x_m":x,"band_1p7_to_2p3":ray_stats(iv,1.7,2.3),"height_1p76_to_2p26":ray_stats(iv,1.76,2.26)})
  horizontal=[]
  for zz in [1.75,1.9,2.0,2.1,2.25]:
   iv=intervals(1,zz);horizontal.append({"z_m":zz,"short_domain":ray_stats(iv,-11.9,30.94),"foil_above":ray_stats(iv,0,1.19)})
  boundary={}
  for name in ["DOMAIN.inlet","DOMAIN.outlet"]:
   c=z[name+"/ElementConnectivity/ data"][...]-1;v=xyz[np.unique(c)];v=v[np.abs(v[:,1]-.01)<1e-9]
   zz=np.unique(v[:,2]);spans=[(float(lo),float(hi)) for lo,hi in zip(zz[:-1],zz[1:]) if hi>1.7+1e-10 and lo<2.3-1e-10]
   d=np.array([hi-lo for lo,hi in spans])
   boundary[name]={"intersected_rows":len(spans),"row_height_m":stats(d),"wave_height0p5_over_max_row_height":.5/float(d.max()),"wave_height0p5_over_median_row_height":.5/float(np.median(d)),"intersected_row_bounds_m":spans}
  wc=z["HF_012_wall/ElementConnectivity/ data"][...]-1;foil=xyz[np.unique(wc)];foil=foil[np.abs(foil[:,1]-.01)<1e-9][:,[0,2]]
  foil=foil[np.lexsort((np.round(foil[:,1],12),np.round(foil[:,0],12)))]
  totals={"cell_count":len(off)-1,"domain_bounds_m":{axis:[float(xyz[:,i].min()),float(xyz[:,i].max())] for i,axis in enumerate("xyz")},"foil_source_nodes":len(foil),"foil_bounds_xz_m":[foil.min(axis=0).tolist(),foil.max(axis=0).tolist()]}
  result={"source":str(src),"sha256":sha(src),"totals":totals,"free_surface":summary(np.ones(len(a),dtype=bool)),"foil_above":summary((a[:,0]>=0)&(a[:,0]<=1.19)),"incoming":summary((a[:,0]>=-11.9)&(a[:,0]<-1)),"downstream":summary((a[:,0]>1.19)&(a[:,0]<=30.94)),"vertical_rays":vertical,"horizontal_rays":horizontal,"extension_interface_rows":boundary}
 return result,foil
build=read(R/"wave_fs_refinement_result.json")
assert build.get("status")=="short_domain_mesh_audited_pending_extension",build.get("status")
assert build.get("flow_steps")==0
meshes={};foils={}
for mesh in ["M09","M10_FS020_r1"]:
 meshes[mesh],foils[mesh]=mesh_audit(mesh)
 p=Q/mesh
 for k,fn in [("quality","measurement.json"),("topology","topology_audit.json"),("extrusion","extrusion_validation.json"),("nominal","design.json")]:meshes[mesh][k]=read(p/fn)
 assert meshes[mesh]["topology"]["single_layer_topology"]
 assert not meshes[mesh]["topology"]["invalid_cells"]
 assert meshes[mesh]["quality"]["metrics"]["NegativeVolumeCells"]==0
 assert meshes[mesh]["quality"]["metrics"]["UnclosedCells"]==0
a=meshes["M09"];b=meshes["M10_FS020_r1"]
foil_match=foils["M09"].shape==foils["M10_FS020_r1"].shape
foil_delta=float(np.max(np.linalg.norm(foils["M09"]-foils["M10_FS020_r1"],axis=1))) if foil_match else None
def layer_data(m):
 with (Q/m/"foil_layer_topology.csv").open(newline="",encoding="utf-8-sig") as f:rows=list(csv.DictReader(f))
 rows=sorted(rows,key=lambda r:(round(float(r["x"]),12),round(float(r["z"]),12)))
 return {k:np.array([float(r[k]) if r[k] else np.nan for r in rows]) for k in rows[0]}
la=layer_data("M09");lb=layer_data("M10_FS020_r1")
layer_missing_patterns_match={k:bool(np.array_equal(np.isnan(la[k]),np.isnan(lb[k]))) for k in la}
assert all(layer_missing_patterns_match.values())
layer_diff={k:float(np.nanmax(np.abs(lb[k]-la[k]))) for k in la}
sharedkeys=["base_m","foil_target_m","foil_min_m","global_min_m","near_foil_m","first_layer_um","layers","total_prism_m","protected_middle_size_m","protected_middle_xz_m"]
same={k:a["nominal"].get(k) for k in sharedkeys if a["nominal"].get(k)==b["nominal"].get(k)}
nominal_changes=[{"parameter":"Free-surface nominal isotropic size","unit":"m","M09":a["nominal"]["free_surface_m"],"M10_FS020_r1":b["nominal"]["free_surface_m"],"change_pct":100*(b["nominal"]["free_surface_m"]/a["nominal"]["free_surface_m"]-1)}]
deltas={"cells_added":b["totals"]["cell_count"]-a["totals"]["cell_count"],"cell_count_change_pct":100*(b["totals"]["cell_count"]/a["totals"]["cell_count"]-1)}
for region in ["free_surface","foil_above","incoming","downstream"]:
 deltas[region]={}
 for quantity in ["bbox_dx_m","bbox_dz_m"]:
  deltas[region][quantity+"_median_change_pct"]=100*(b[region][quantity]["median"]/a[region][quantity]["median"]-1)
  deltas[region][quantity+"_p95_change_pct"]=100*(b[region][quantity]["p95"]/a[region][quantity]["p95"]-1)
 deltas[region]["cell_count_change_pct"]=100*(b[region]["cells"]/a[region]["cells"]-1)
qa={"foil_source_coordinates_same_to_1e_minus12_m":bool(foil_match and foil_delta<=1e-12),"max_foil_source_coordinate_displacement_m":foil_delta,"foil_edge_count_equal":a["topology"]["foil_edges"]==b["topology"]["foil_edges"],"layer_histogram_equal":a["topology"]["layer_histogram"]==b["topology"]["layer_histogram"],"per_edge_prism_comparison_max_abs_delta":layer_diff,"per_edge_layer_count_equal":layer_diff["continuous_quad_layers"]==0,"all_shared_nominal_controls_match":len(same)==len(sharedkeys),"domain_bounds_equal_to_1e_minus10_m":bool(np.max(np.abs(np.array(list(a["totals"]["domain_bounds_m"].values()))-np.array(list(b["totals"]["domain_bounds_m"].values()))))<1e-10),"source_build_audit_pass":True}
source_paths=[R/"wave_fs_refinement_result.json",R/"wave_fs_refinement_state.json",R/"MeshRawM10_FS020_r1.java",R/"professor_c01_fs_review.py",R/"professor_c01_fs_ray_review.py",R/"professor_c01_wavegrid_recommendation.json"]
for mesh in ["M09","M10_FS020_r1"]:
 source_paths += [Q/mesh/x for x in ["design.json","topology_audit.json","extrusion_validation.json","measurement.json","foil_layer_topology.csv"]]
result={"status":"short_domain_geometry_audited_pending_long_domain_and_flow_validation","generated_at":datetime.datetime.now().astimezone().isoformat(),"scope":"Actual M09 versus M10_FS020_r1 short-domain CGNS geometry. Read-only; no solver steps, no admission of a wave result.","build_status":build["status"],"flow_steps":0,"method":{"free_surface_band_z_m":[1.7,2.3],"wave_height_m":.5,"wavelength_m":20,"bbox":"Source-span polygons intersecting the band; unweighted cell percentiles plus full-polygon-area-weighted p95. Boxes are geometric extents, not directional face-normal spacings.","rays":"Exact half-open line/polygon intersections. Crossed cells include partially intersected end cells. Grazing chords are not meaningful CFL length limits.","foil":"Source-plane wall vertices sorted by rounded x,z; independent per-edge layer CSVs sorted by rounded centroid x,z and compared numerically."},"nominal_changes":nominal_changes,"shared_controls":same,"meshes":meshes,"difference":deltas,"preservation_checks":qa,"cost_interpretation":{"measured_cell_count_ratio":b["totals"]["cell_count"]/a["totals"]["cell_count"],"measured_solver_cost_available":False,"statement":"Cell count rises by "+format(deltas["cell_count_change_pct"],".2f")+"% on the unchanged short domain. This is not a measured runtime penalty. Smaller free-surface streamwise cells can also increase temporal-resolution cost; measure actual cost with matched solver settings and physical time."},"extension_plan":{"status":"pending separate long-domain construction/import/quality audit","original_short_x_m":[-11.9,30.94],"target_W01_L4_x_m":[-35,45],"target_length_m":80,"remote_extension_nominal_dx_m":.2,"vertical_rows":"Carry the actual refined inlet/outlet z rows coherently into extension strips; do not restore old M09 vertical spacing.","distinction":"The changed0.020m control is isotropic in the short-domain core, so it refines both x and z. Planned remote strips use approximately0.2m in x with inherited refined vertical rows. This is coupled free-surface refinement, not a vertical-only experiment."},"limits":["No accepted flow, calm or wave result exists for this new grid in this review.","Short-domain mesh audit does not validate the extended80m domain, wave propagation, boundary treatment, CFL or timestep.","An approximately H/20 guideline is not a universal acceptance criterion; compare measured wave amplitude,phase,mean level and force-cycle responses on matched grids.","Every regenerated wave grid needs its own matched calm reference; preserve M09 data separately.","A forthcoming extended mesh must be audited independently; do not assume the reported short-domain cell count or statistics apply to the complete wave domain."],"provenance":[{"path":str(p),"sha256":sha(p)} for p in source_paths]}
assert qa["foil_source_coordinates_same_to_1e_minus12_m"] and qa["per_edge_layer_count_equal"] and qa["all_shared_nominal_controls_match"]
out=R/"professor_m10_wavegrid_review.json"
out.write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps({"report":str(out),"status":result["status"],"cells":{k:v["totals"]["cell_count"] for k,v in meshes.items()},"difference":deltas,"preservation":qa,"boundary_rows":{k:{n:v["row_height_m"] for n,v in m["extension_interface_rows"].items()} for k,m in meshes.items()}},indent=2))
