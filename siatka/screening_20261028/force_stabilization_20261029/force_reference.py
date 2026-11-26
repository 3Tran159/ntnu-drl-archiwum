"""Audited nominal buoyancy correction. No STAR/CFD and no raw history edits.
Runtime adapters are stdlib-only. build_manifest uses installed scientific Python
only to read a verified CGNS. Imported/unknown meshes have no default correction.
"""
from pathlib import Path
import datetime,functools,hashlib,json,math,os,subprocess,sys,uuid
R=Path(__file__).resolve().parent
SCIENTIFIC_PYTHON=Path("E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/star/lib/python/python.exe")
REVIEW=R/"force_reference_review.json"
def _read(p):
 try:return json.loads(Path(p).read_text(encoding="utf-8-sig"))
 except (OSError,ValueError):return {}
def _write(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+"."+uuid.uuid4().hex+".tmp")
 t.write_text(json.dumps(v,indent=2,allow_nan=False));os.replace(t,p)
@functools.lru_cache(maxsize=256)
def _hash_cached(path,size,mtime):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(8*1024**2),b""):h.update(b)
 return h.hexdigest()
def _hash(p):
 p=Path(p);s=p.stat();return _hash_cached(str(p.resolve()),s.st_size,s.st_mtime_ns)
def _number(v):
 if isinstance(v,bool):return None
 try:v=float(v)
 except (TypeError,ValueError):return None
 return v if math.isfinite(v) else None
def _unavailable(reason,case=None):
 return dict(available=False,case=str(case) if case else None,mesh_sha256=None,cl_offset=None,buoyancy_N=None,
  reference_force_N=None,provenance_file=None,reason=reason,definition="CL=(Fz-rho_water*(-g_z)*displaced_volume)/reference_force")
def _physics(audit):
 if audit.get("force_physics"):p=audit["force_physics"]
 else:p=audit
 if p.get("native_getters_verified") is not True:raise ValueError("Native force physics getters are not verified")
 vals={}
 for k in ("rho_water_kg_m3","rho_air_kg_m3","reference_density_kg_m3","reference_speed_m_s","reference_area_m2","raw_reference_force_N","pressure_reference_density_kg_m3","region_density_min_kg_m3","region_density_max_kg_m3","foil_alpha_min"):
  vals[k]=_number(p.get(k))
  if vals[k] is None:raise ValueError("Missing/nonfinite native physics: "+k)
 g=p.get("gravity_m_s2");direction=p.get("lift_direction")
 if not isinstance(g,list) or len(g)!=3 or any(_number(x) is None for x in g):raise ValueError("Native gravity vector missing/nonfinite")
 if any(abs(float(x)-y)>1e-10 for x,y in zip(g[:2],[0,0])) or float(g[2])>=0:raise ValueError("Only downward Z gravity is currently supported")
 if direction!=[0,0,1]:raise ValueError("Only +Z lift direction is supported")
 if p.get("fully_submerged") is not True or vals["foil_alpha_min"]<1-1e-8:raise ValueError("Full foil immersion was not verified")
 if abs(vals["rho_water_kg_m3"]-1000)>1e-6 or abs(vals["reference_density_kg_m3"]-vals["rho_water_kg_m3"])>1e-6:raise ValueError("Water/reference density differs from supported raw-force profile")
 if abs(vals["pressure_reference_density_kg_m3"])>1e-8:raise ValueError("Nonzero pressure reference density requires a separate force-definition audit")
 if vals["rho_air_kg_m3"]<=0 or abs(vals["region_density_min_kg_m3"]-vals["rho_air_kg_m3"])>1e-5 or abs(vals["region_density_max_kg_m3"]-vals["rho_water_kg_m3"])>1e-5:raise ValueError("Native mixture density extrema do not confirm water/air values")
 if vals["reference_speed_m_s"]<=0 or vals["reference_area_m2"]<=0:raise ValueError("Positive force-reference speed and area required")
 q=.5*vals["reference_density_kg_m3"]*vals["reference_speed_m_s"]**2*vals["reference_area_m2"]
 if abs(q-3855.6)>1e-6 or abs(vals["raw_reference_force_N"]-q)>1e-6:raise ValueError("Actual reference quantities do not match raw history normalization3855.6N")
 return dict(vals,gravity_m_s2=list(map(float,g)),lift_direction=direction,reference_force_N=q,
  native_getters_verified=True,fully_submerged=True)
def _validate_values(v):
 if v.get("available") is not True:return False
 values=[_number(v.get(k)) for k in ("cl_offset","buoyancy_N","reference_force_N")]
 if any(x is None for x in values):return False
 c,b,q=values
 return q>0 and b>0 and c>0 and math.isclose(c,b/q,rel_tol=1e-10,abs_tol=1e-12)
def _validate_manifest(path,expected_hash=None):
 p=Path(path);v=_read(p)
 try:
  if expected_hash and _hash(p)!=expected_hash:raise ValueError("Force reference manifest hash changed")
  if v.get("schema_version")!=1 or not _validate_values(v):raise ValueError("Force reference manifest is incomplete")
  mesh=Path(v["mesh_cgns"]);audit=Path(v["physical_audit"])
  if _hash(mesh)!=v["mesh_sha256"]:raise ValueError("Bound CGNS changed")
  if _hash(audit)!=v["physical_audit_sha256"]:raise ValueError("Bound native physical audit changed")
  physics=_physics(_read(audit))
  volume=_number(v.get("displaced_volume_m3"))
  if volume is None or volume<=0:raise ValueError("Displaced volume is missing")
  b=physics["rho_water_kg_m3"]*(-physics["gravity_m_s2"][2])*volume
  if not math.isclose(b,v["buoyancy_N"],rel_tol=1e-11,abs_tol=1e-10):raise ValueError("Manifest buoyancy and native physics disagree")
  return dict(v,provenance_file=str(p),force_reference_file=str(p),force_reference_sha256=_hash(p),reason="Audited nominal buoyancy correction available")
 except (OSError,ValueError,KeyError,TypeError) as ex:return _unavailable(str(ex),v.get("case"))
def reference_for_source(source,profile=None):
 """Validate a source's already-built manifest; never calculate or launch a solver."""
 if not isinstance(source,dict):return _unavailable("Source manifest must be a dictionary")
 path=source.get("force_reference_file");sha=source.get("force_reference_sha256")
 if not path or not sha:return _unavailable("Source has no bound force reference file/hash")
 v=_validate_manifest(path,sha)
 if not v["available"]:return v
 if source.get("mesh"):
  try:
   if _hash(source["mesh"])!=v["mesh_sha256"]:return _unavailable("Source mesh file and force reference CGNS hash disagree")
  except (OSError,TypeError,ValueError):return _unavailable("Bound source mesh file is missing or unreadable")
 expected=source.get("force_reference_mesh_sha256") or source.get("mesh_cgns_sha256")
 if expected and expected!=v["mesh_sha256"]:return _unavailable("Source and force reference CGNS hashes disagree")
 # selected mesh can be extended/cropped; its original CGNS hash need not equal final-domain CGNS.
 if profile and isinstance(profile,dict) and profile.get("force_reference_mesh_sha256") and profile["force_reference_mesh_sha256"]!=v["mesh_sha256"]:return _unavailable("Profile force-reference mesh binding disagrees")
 return v
def correction_for_case(folder):
 """Read case-bound manifest (including copied provenance) or a verified legacy entry."""
 folder=Path(folder).resolve();p=folder/"force_reference.json";identity=_read(folder/"source_identity.json")
 if p.is_file():
  sha=identity.get("force_reference_sha256")
  v=_read(p)
  if str(Path(v.get("case","missing")).resolve())!=str(folder) and not sha:return _unavailable("Copied force reference lacks source_identity hash binding",folder)
  return _validate_manifest(p,sha)
 if identity.get("force_reference_file"):
  return reference_for_source(identity)
 # Legacy entries are individually reviewed, bound to exact files, never inferred from a mesh label.
 review=_read(REVIEW)
 for v in review.get("legacy_case_references",[]):
  if str(Path(v.get("case","missing")).resolve())!=str(folder):continue
  try:
   for item in v.get("bindings",[]):
    if _hash(item["path"])!=item["sha256"]:raise ValueError("Legacy case evidence changed: "+item["path"])
   if not v.get("bindings") or not _validate_values(v):raise ValueError("Legacy case binding is incomplete")
   return dict(v,provenance_file=str(REVIEW),reason="Legacy source-specific geometry and physics review")
  except (OSError,ValueError,KeyError) as ex:return _unavailable(str(ex),folder)
 return _unavailable("No source-bound buoyancy evidence for this case; retain rawCL_total and do not guess a correction",folder)
def correct_row(row,ref):
 """Copy a row; CL is corrected, CL_total/rawCL_total remain raw; CD is untouched."""
 out=dict(row);raw=_number(row.get("rawCL_total",row.get("CL_total")))
 out["rawCL_total"]=raw;out["CL"]=None;out["CL_definition"]="buoyancy_subtracted"
 out["cl_correction_available"]=False;out["force_reference_source"]=ref.get("provenance_file") if isinstance(ref,dict) else None
 if not isinstance(ref,dict) or not _validate_values(ref):
  out["cl_correction_reason"]="Unavailable or nonfinite audited force reference";return out
 if ("rawCL_total" in row or "CL_total" in row) and raw is None:
  out["cl_correction_reason"]="Raw coefficient is nonfinite";return out
 q=float(ref["reference_force_N"]);b=float(ref["buoyancy_N"])
 fz=next((_number(row.get(k)) for k in ("Fz_slice_N","Fz_N","Fz_total_N","lift_N") if _number(row.get(k)) is not None),None)
 if fz is None and raw is not None:fz=raw*q
 if fz is None:out["cl_correction_reason"]="Raw total lift force/coefficient is missing or nonfinite";return out
 if raw is None:out["rawCL_total"]=fz/q
 elif not math.isclose(raw*q,fz,rel_tol=1e-7,abs_tol=1e-7):
  out["cl_correction_reason"]="Raw Fz and CL_total normalization disagree";return out
 out["CL"]=(fz-b)/q;out["Fz_without_buoyancy_N"]=fz-b;out["cl_correction_available"]=True
 out["cl_correction_reason"]="Nominal fully submerged buoyancy subtracted; raw total retained"
 return out
def build_manifest(folder,mesh_cgns,physical_audit,expected_mesh_sha256):
 """Explicit preparation: file-only geometry audit, then save immutable correction manifest."""
 folder=Path(folder);mesh=Path(mesh_cgns).resolve();audit=Path(physical_audit).resolve();target=folder/"force_reference.json"
 try:
  if not expected_mesh_sha256 or _hash(mesh)!=expected_mesh_sha256:raise ValueError("CGNS identity does not match explicit preparation")
  physics=_physics(_read(audit));auditsha=_hash(audit)
  if target.exists():
   old=_validate_manifest(target)
   if old.get("available") and old.get("mesh_sha256")==expected_mesh_sha256 and old.get("physical_audit_sha256")==auditsha:return old
   raise ValueError("A different force manifest already exists; preserve it and use a new preparation")
  cmd=[str(SCIENTIFIC_PYTHON),str(Path(__file__).resolve()),"--geometry",str(mesh),expected_mesh_sha256]
  p=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace",env=dict(os.environ,OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1"),creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)|getattr(subprocess,"BELOW_NORMAL_PRIORITY_CLASS",0),timeout=180)
  if p.returncode:raise ValueError("CGNS displaced-volume audit failed: "+p.stderr.strip()[-600:])
  geo=json.loads(p.stdout);volume=geo["displaced_volume_m3"]
  if not geo.get("verified") or geo["mesh_sha256"]!=expected_mesh_sha256:raise ValueError("CGNS geometry receipt mismatch")
  if _hash(mesh)!=expected_mesh_sha256 or _hash(audit)!=auditsha:raise ValueError("Preparation evidence changed during audit")
  b=physics["rho_water_kg_m3"]*(-physics["gravity_m_s2"][2])*volume;q=physics["reference_force_N"]
  v=dict(schema_version=1,available=True,case=str(folder.resolve()),mesh_cgns=str(mesh),mesh_sha256=expected_mesh_sha256,
   physical_audit=str(audit),physical_audit_sha256=auditsha,physics=physics,geometry=geo,displaced_volume_m3=volume,
   buoyancy_N=b,reference_force_N=q,cl_offset=b/q,definition="CL=(Fz-rho_water*(-g_z)*displaced_volume)/reference_force",
   scope="Nominal hydrostatic buoyancy correction for fully submerged foil; not an accuracy or convergence claim.",
   created_at=datetime.datetime.now().astimezone().isoformat(),reason="Audited nominal buoyancy correction available")
  _write(target,v);return _validate_manifest(target)
 except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as ex:return _unavailable(str(ex),folder)
def _geometry(path,expected):
 sys.path.insert(0,"F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029/deps311")
 import h5py,numpy as np
 path=Path(path)
 if _hash(path)!=expected:raise ValueError("CGNS hash mismatch")
 with h5py.File(path,"r") as f:
  zones=[]
  f.visititems(lambda n,o:zones.append(o) if isinstance(o,h5py.Group) and "GridCoordinates" in o else None)
  if len(zones)!=1:raise ValueError("Exactly one CGNS zone required")
  z=zones[0];xyz=np.column_stack([np.asarray(z["GridCoordinates/Coordinate"+a+"/ data"]) for a in "XYZ"])
  if not np.isfinite(xyz).all():raise ValueError("Nonfinite coordinates")
  g=z["HF_012_wall"];off=np.asarray(g["ElementStartOffset/ data"],dtype=np.int64);con=np.asarray(g["ElementConnectivity/ data"],dtype=np.int64)-1
  if np.any(np.diff(off)!=4):raise ValueError("Foil sides must be extruded quadrilaterals")
  nodes=con.reshape(-1,4);yy=xyz[nodes,1];ymin=float(yy.min());ymax=float(yy.max());span=ymax-ymin
  if span<=0:raise ValueError("Invalid span")
  low=np.abs(yy-ymin)<1e-9;high=np.abs(yy-ymax)<1e-9
  if np.any(low.sum(1)!=2) or np.any(high.sum(1)!=2):raise ValueError("Foil must be a single extrusion layer")
  a=xyz[nodes][low].reshape(-1,2,3)[:,:,[0,2]];b=xyz[nodes][high].reshape(-1,2,3)[:,:,[0,2]]
  dev=np.minimum(np.linalg.norm(a-b,axis=2).max(1),np.linalg.norm(a-b[:,::-1],axis=2).max(1)).max()
  if dev>1e-10:raise ValueError("Foil is not constant across span")
  pairs=nodes[low].reshape(-1,2);adj={}
  for i,j in pairs.tolist():adj.setdefault(i,[]).append(j);adj.setdefault(j,[]).append(i)
  if any(len(v)!=2 for v in adj.values()):raise ValueError("Foil section is not a closed manifold")
  first=min(adj);order=[first];seen={first};previous=None;cur=first
  while True:
   nxt=next(k for k in adj[cur] if k!=previous)
   if nxt==first:break
   if nxt in seen:raise ValueError("Crossed foil connectivity")
   order.append(nxt);seen.add(nxt);previous,cur=cur,nxt
  if len(seen)!=len(adj):raise ValueError("Multiple foil loops")
  poly=xyz[order][:,[0,2]];area=abs(float(np.sum(poly[:,0]*np.roll(poly[:,1],-1)-np.roll(poly[:,0],-1)*poly[:,1])))*.5
  if area<=0:raise ValueError("Nonpositive foil area")
  v=dict(verified=True,mesh_sha256=expected,foil_section_area_m2=area,span_m=span,displaced_volume_m3=area*span,foil_edges=len(pairs),foil_z_m=[float(poly[:,1].min()),float(poly[:,1].max())],method="Closed CGNS HF_012_wall polygon shoelace area times verified constant extrusion span")
 if _hash(path)!=expected:raise ValueError("CGNS changed during file audit")
 return v
if __name__=="__main__":
 if len(sys.argv)==4 and sys.argv[1]=="--geometry":
  try:print(json.dumps(_geometry(sys.argv[2],sys.argv[3]),allow_nan=False))
  except Exception as ex:print(str(ex),file=sys.stderr);raise SystemExit(2)
 else:raise SystemExit("This module is used by the local preparation/worker/UI.")
