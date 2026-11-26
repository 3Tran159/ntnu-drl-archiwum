"""Explicit .sim mesh inspection/import and selection; no flow solver operations.
Importing this module has no side effects. inspect_request starts only a requested
CPU1 zero-flow inspection. A selected mesh is NOT convergence or calm approval.
"""
from pathlib import Path
import contextlib,datetime,hashlib,json,math,os,re,shutil,subprocess,sys,threading,time,uuid
R=Path(__file__).resolve().parent
W=Path("E:/ntnu/quasi2d_waves_20261029")
D=R/"local_control"/"mesh_inputs"
PYTHON=Path("C:/Python315/python.exe")
SCIPY=Path("E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/star/lib/python/python.exe")
REFERENCE_CGNS=W/"C01_W20L4_M10_FS020_mesh_r2"/"mesh.CGNS"
READY="mesh_inspection_passed"
ACTIVE={"queued","waiting_for_resources","inspecting","auditing_geometry"}
def _stamp():return datetime.datetime.now().astimezone().isoformat()
def _read(p):
 try:return json.loads(Path(p).read_text(encoding="utf-8-sig"))
 except (OSError,ValueError):return {}
def _write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 tmp=p.with_name(p.name+"."+uuid.uuid4().hex+".tmp");tmp.write_text(json.dumps(x,indent=2,allow_nan=False),encoding="utf-8")
 for i in range(20):
  try:os.replace(tmp,p);return
  except PermissionError:
   if i==19:raise
   time.sleep(.05)
def _digest(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
 return h.hexdigest()
def _identity(p):
 p=Path(p);s=p.stat();return dict(bytes=s.st_size,mtime_ns=s.st_mtime_ns,sha256=_digest(p))
def _id(value):
 if not isinstance(value,str) or re.fullmatch(r"[0-9a-f]{32}",value) is None:raise ValueError("Invalid imported mesh identifier")
 return value
def _entry_path(value):return D/"entries"/(_id(value)+".json")
def _update(value,**changes):
 p=_entry_path(value);v=_read(p);v.update(changes,updated_at=_stamp());_write(p,v);return v
def _alive(pid):
 if not isinstance(pid,int) or pid<=0:return False
 try:
  import ctypes
  k=ctypes.windll.kernel32;k.OpenProcess.restype=ctypes.c_void_p
  h=k.OpenProcess(0x1000,False,pid)
  if not h:return False
  try:
   n=ctypes.c_ulong()
   return bool(k.GetExitCodeProcess(ctypes.c_void_p(h),ctypes.byref(n))) and n.value==259
  finally:k.CloseHandle(ctypes.c_void_p(h))
 except (AttributeError,OSError):return False
def list_entries():
 result=[]
 for p in sorted((D/"entries").glob("*.json")) if (D/"entries").exists() else []:
  v=_read(p)
  if not v:continue
  if v.get("status") in ACTIVE and v.get("controller_pid") and not _alive(v["controller_pid"]):
   v=dict(v,status="interrupted",ready=False,reason="Inspection process has ended without a terminal receipt. Preserve this attempt; request a new inspection.")
  result.append(v)
 return sorted(result,key=lambda x:(x.get("created_at",""),x.get("id","")),reverse=True)
def selected():
 choice=_read(D/"selected.json");value=choice.get("id")
 return next((v for v in list_entries() if v.get("id")==value),None)
def set_selected(value):
 value=_id(value);v=_read(_entry_path(value))
 if v.get("status")!=READY or v.get("ready") is not True:raise ValueError(v.get("reason") or "Choose a mechanically compatible inspected mesh")
 for name,key in [("mesh_sim","file_sha256"),("mesh_cgns","mesh_cgns_sha256")]:
  p=Path(v.get(name,"missing"))
  owned=(W/("LOCAL_MESH_IMPORT_"+value)).resolve()
  if p.resolve().parent!=owned:raise ValueError("Imported artifact is outside its owned inspection folder")
  if not p.is_file() or _digest(p)!=v.get(key):raise ValueError("Imported artifact changed or is missing; inspect it again")
 _write(D/"selected.json",dict(id=value,selected_at=_stamp(),file_sha256=v["file_sha256"],mesh_fingerprint=v["mesh_fingerprint"]))
 return dict(v,selected=True,selection_launches_calculation=False)
def public_status():
 entries=list_entries();choice=selected()
 return dict(entries=entries,selected=choice,selected_id=choice.get("id") if choice else None,
  imports=[v for v in entries if v.get("status") in ACTIVE],inspection_available=True,
  scientific_approval="Selection confirms mechanical compatibility only; scientific convergence and matched C01 remain separate.",
  flow_on_hold=(R/"local_control"/"PAUSE").exists(),zero_flow_inspection_allowed_during_flow_hold=True)
def _validate_source(value):
 if not isinstance(value,str) or not value.strip():raise ValueError("Paste the absolute path to an existing .sim with a generated volume mesh")
 text=value.strip()
 if len(text)>=2 and text[0]==text[-1] and text[0] in ("'",'"'):text=text[1:-1]
 p=Path(text)
 if not p.is_absolute():raise ValueError("Use an absolute .sim path, for example E:/folder/M11.sim")
 if p.suffix.lower()!=".sim":raise ValueError("Select a saved .sim file, not a folder or CGNS file")
 if not p.is_file():raise ValueError("The .sim file does not exist or is not accessible")
 if p.stat().st_size<=0:raise ValueError("The .sim file is empty")
 return p.resolve()
def _spawn_inspection(value,folder):
 flags=getattr(subprocess,"CREATE_NO_WINDOW",0)|getattr(subprocess,"BELOW_NORMAL_PRIORITY_CLASS",0)
 with (folder/"controller.stdout.log").open("x") as out,(folder/"controller.stderr.log").open("x") as err:
  return subprocess.Popen([str(PYTHON),str(Path(__file__).resolve()),"--inspect",value],cwd=str(R),stdout=out,stderr=err,creationflags=flags)
def inspect_request(path):
 source=_validate_source(path)
 # A deliberate button click is the authorization; importing/listing never launches.
 for old in list_entries():
  if old.get("source_path")==str(source) and old.get("status") in ACTIVE:
   return dict(id=old["id"],pid=old.get("controller_pid"),status=old["status"],reason="This path is already being inspected",entry=old)
 value=uuid.uuid4().hex;folder=W/("LOCAL_MESH_IMPORT_"+value)
 folder.mkdir(parents=True,exist_ok=False)
 entry=dict(id=value,label=source.stem,source_path=str(source),file_sha256=None,mesh_cgns=None,
  mesh_sim=None,cells=None,dt_s=None,inner=None,domain_x_m=None,domain_z_m=None,span_m=None,
  status="queued",ready=False,reason="Waiting for the explicitly requested CPU1 zero-flow inspection",
  created_at=_stamp(),updated_at=_stamp(),directory=str(folder),scientific_approval="not_assessed",
  calm_accepted=False,retained_fields_are_accepted_calm=False,flow_steps=0,request_kind="explicit_zero_flow_mesh_inspection")
 _write(_entry_path(value),entry);_write(folder/"request.json",entry)
 try:p=_spawn_inspection(value,folder)
 except BaseException as ex:
  _update(value,status="inspection_failed",reason="Could not start inspection: "+str(ex),ready=False);raise
 # Avoid replacing any status already written by a fast child process.
 latest=_read(_entry_path(value));latest["controller_pid"]=p.pid;_write(_entry_path(value),latest)
 return dict(id=value,pid=p.pid,status=latest["status"],entry=latest)
def _check_receipt():
 p=R/"InspectLocalMesh.java";v=_read(R/"local_mesh_import_compile_receipt.json")
 if v.get("status")!="javac_passed" or v.get("macro_sha256")!=_digest(p):raise RuntimeError("Inspection macro needs an offline compile before use")
 return v
def _own_solver_pids():
 # Return only identifiers, never raw process commands or licensing data.
 command="Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'star' -and $_.CommandLine -and ($_.CommandLine.Replace([char]92,[char]47) -match 'E:/ntnu/quasi2d_waves_20261029/|F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/') -and ($_.CommandLine -match '-batch|-server')} | Select-Object -ExpandProperty ProcessId"
 p=subprocess.run(["powershell.exe","-NoProfile","-Command",command],capture_output=True,text=True,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),timeout=30)
 if p.returncode:raise RuntimeError("Could not verify existing campaign solver processes")
 return [int(x.strip()) for x in p.stdout.splitlines() if x.strip().isdigit()]
def _block_reason(source_bytes):
 import run_until_settled as e
 if (R/"STOP_ALL").exists():return "Global STOP_ALL is active; no new STAR inspection started"
 if (R/"queue.lock").exists() or (W/"preparation.lock").exists():return "Waiting for campaign/preparation lock release"
 if e.free_memory()<24*1024**3:return "Waiting for at least24GiB available memory"
 if shutil.disk_usage(W).free<max(8*1024**3,4*source_bytes):return "Insufficient free space on E for preserved input and exports"
 if _own_solver_pids():return "Waiting for existing campaign STAR processes; no duplicate solver will be started"
 return None
@contextlib.contextmanager
def _locks(value):
 paths=[R/"queue.lock",W/"preparation.lock"];owned=[];token=uuid.uuid4().hex
 try:
  for p in paths:
   with p.open("x") as f:json.dump(dict(pid=os.getpid(),owner_token=token,mesh_import_id=value,purpose="Explicit CPU1 zero-flow mesh inspection",created_at=_stamp()),f)
   owned.append(p)
  yield
 finally:
  for p in reversed(owned):
   if _read(p).get("owner_token")==token:p.unlink()
def _safe(line):
 import run_until_settled as e
 if any(k in line.lower() for k in ("podkey","licpath","password","license key","authorization","token=")):
  return "[service connection details redacted]\n"
 return e.redact(line)
def _run_star(folder):
 import run_until_settled as e
 options=e.saved_options(1)
 if any("gpu" in str(v).lower() for v in options):raise RuntimeError("CPU-only inspection options unexpectedly contain GPU selection")
 if "-np" not in options or str(options[options.index("-np")+1])!="1":raise RuntimeError("Inspection requires exactly one CPU worker")
 env=dict(os.environ,NTNU_MESH_IMPORT_OUT=str(folder),OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1")
 flags=getattr(subprocess,"CREATE_NO_WINDOW",0)|getattr(subprocess,"BELOW_NORMAL_PRIORITY_CLASS",0)
 with (folder/"star.log").open("x",encoding="utf-8") as log:
  p=subprocess.Popen([str(e.STAR),*options,"-batch",str(folder/"InspectLocalMesh.java"),str(folder/"input.sim")],cwd=str(folder),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",creationflags=flags)
  _write(folder/"process.json",dict(launcher_pid=p.pid,workers=1,gpu=False,flow_steps=0,started_at=_stamp()))
  def drain():
   for line in p.stdout:log.write(_safe(line));log.flush()
  thread=threading.Thread(target=drain,daemon=True);thread.start()
  try:rc=p.wait(timeout=1800)
  except subprocess.TimeoutExpired:
   subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],capture_output=True,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
   raise RuntimeError("Owned zero-flow inspection timed out; attempt preserved")
  thread.join(15)
 if rc:raise RuntimeError("STAR zero-flow inspection failed; inspect the preserved redacted log")
 return rc
def _configuration_issues(native):
 p=native.get("profile",{});issues=list(native.get("configuration_notes",[]))
 def number(v):
  try:
   x=float(v);return x if math.isfinite(x) else None
  except (TypeError,ValueError):return None
 dt=number(p.get("dt_s"))
 if dt is None or not .0001-1e-12<=dt<=.001+1e-12:issues.append("Configure dt between0.0001 and0.001s; the importer does not change it")
 if p.get("inner")!=10:issues.append("The current local recipe requires10inner iterations")
 if p.get("order")!="SECOND_ORDER":issues.append("The current local recipe requires SECOND_ORDER")
 if p.get("continuum")!="water+air":issues.append("Use the water+air continuum")
 for key in ("vof_wave_model_available","calm_flat_reference_available","segregated_flow_vof_available"):
  if p.get(key) is not True:issues.append("Required physics/API availability not confirmed: "+key)
 return list(dict.fromkeys(issues))
def _settings_to_replace(native):
 p=native.get("profile",{})
 wanted=dict(wave_active=False,current_m_s=[18,0,0],wind_m_s=[18,0,0],waterline_m=[0,0,2],vertical=[0,0,1],
  outlet_reversed_pressure="ENVIRONMENTAL",bottom_shear="SLIP",foil_shear="NO_SLIP",top_reversed_pressure="STATIC",
  pressure_AMG_tolerance=.1,VOF_AMG_tolerance=.1)
 return dict(applies_only_to_new_C01_copy=True,source_is_never_modified=True,retained_fields_not_accepted=True,
  planned_recipe_values=wanted,differences={k:dict(imported=p.get(k),new_C01=v) for k,v in wanted.items() if p.get(k)!=v},
  inspection_notes=native.get("settings_to_replace_notes",[]))
def _qualify(native,geometry):
 errors=[]
 if native.get("status")!="zero_flow_inspection_completed" or native.get("flow_steps")!=0 or native.get("initialized_or_cleared") is not False:errors.append("Zero-flow inspection receipt is incomplete")
 if native.get("physical_time_s")!=native.get("physical_time_after_s"):errors.append("Physical time changed during inspection")
 q=native.get("quality",{})
 for k in ("NegativeVolumeCells","UnclosedCells","DegeneratedFeCells"):
  try:ok=float(q[k])==0
  except (KeyError,TypeError,ValueError):ok=False
  if not ok:errors.append("Mesh quality failed or unavailable: "+k)
 for k,limit in [("min_cell_quality",.01),("min_face_validity",.5)]:
  try:ok=math.isfinite(float(q[k])) and float(q[k])>=limit
  except (KeyError,TypeError,ValueError):ok=False
  if not ok:errors.append("Mesh quality below local inspection threshold: "+k)
 if geometry.get("passed") is not True:errors.extend(geometry.get("errors") or ["Independent CGNS topology audit did not pass"])
 if native.get("cells")!=geometry.get("cells"):errors.append("Native and CGNS cell counts disagree")
 if errors:return "unsupported_geometry",False,"; ".join(errors)
 issues=_configuration_issues(native)
 if issues:return "needs_configuration",False,"; ".join(issues)
 return READY,True,"Mechanical inspection passed. Mesh convergence, numerical accuracy and a matched settled C01 are not approved by this inspection."
def _inspect(value):
 value=_id(value);entry=_read(_entry_path(value))
 if entry.get("status") not in ("queued","waiting_for_resources"):raise RuntimeError("This unique inspection is already used; preserve it")
 folder=Path(entry["directory"]);expected=W/("LOCAL_MESH_IMPORT_"+value)
 if folder.resolve()!=expected.resolve():raise RuntimeError("Inspection directory is outside the owned attempt")
 with (folder/"controller.claim").open("x") as f:f.write(str(os.getpid()))
 _update(value,controller_pid=os.getpid())
 try:
  _check_receipt();source=_validate_source(entry["source_path"]);started=time.monotonic()
  while True:
   reason=_block_reason(source.stat().st_size)
   if reason is None:break
   _update(value,status="waiting_for_resources",reason=reason)
   if (R/"STOP_ALL").exists() or time.monotonic()-started>1800:raise RuntimeError(reason+"; request a new inspection after resolving this condition")
   time.sleep(10)
  with _locks(value):
   # Recheck processes/memory inside the exclusive locks without treating our own locks as blockers.
   import run_until_settled as e
   if _own_solver_pids() or e.free_memory()<24*1024**3:raise RuntimeError("Resources/process state changed before inspection")
   before=_identity(source);shutil.copy2(source,folder/"input.sim")
   if _digest(folder/"input.sim")!=before["sha256"] or _identity(source)!=before:raise RuntimeError("Source changed while copying; wait for its writer to finish and inspect a new attempt")
   shutil.copy2(R/"InspectLocalMesh.java",folder/"InspectLocalMesh.java")
   _write(folder/"source_identity.json",dict(source=str(source),**before,copy_sha256=before["sha256"],source_is_accepted_calm=False))
   _update(value,status="inspecting",reason="CPU1 zero-flow inspection and mesh export",file_sha256=before["sha256"],mesh_sim=str(folder/"input.sim"))
   _run_star(folder)
   if _digest(source)!=before["sha256"] or _digest(folder/"input.sim")!=before["sha256"]:raise RuntimeError("Original/copy hash changed during inspection; candidate rejected")
   _update(value,status="auditing_geometry",reason="Checking exported boundary planes, foil geometry and one-span topology")
   command=[str(SCIPY),str(Path(__file__).resolve()),"--audit-cgns",str(folder)]
   result=subprocess.run(command,capture_output=True,text=True,encoding="utf-8",errors="replace",env=dict(os.environ,OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1"),creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)|getattr(subprocess,"BELOW_NORMAL_PRIORITY_CLASS",0),timeout=1200)
   (folder/"geometry_audit.log").write_text(_safe(result.stdout+"\n"+result.stderr))
   if result.returncode:raise RuntimeError("Independent CGNS audit failed; see geometry_audit.json/log in the preserved attempt")
   native=_read(folder/"inspection.json");geo=_read(folder/"geometry_audit.json")
   status,ready,reason=_qualify(native,geo);profile=native.get("profile",{})
   profile_hash=hashlib.sha256(json.dumps(dict(profile=profile,boundaries=native.get("boundaries")),sort_keys=True).encode()).hexdigest()
   final=_update(value,status=status,ready=ready,reason=reason,file_sha256=before["sha256"],source_unchanged=True,
    mesh_cgns=str(folder/"mesh.CGNS"),mesh_cgns_sha256=_digest(folder/"mesh.CGNS"),mesh_sim=str(folder/"input.sim"),mesh_sim_sha256=before["sha256"],
    inspection_sim=str(folder/"inspected.sim"),cells=native.get("cells"),dt_s=profile.get("dt_s"),inner=profile.get("inner"),order=profile.get("order"),
    physical_time_s=native.get("physical_time_s"),domain_x_m=geo.get("domain_x_m"),domain_y_m=geo.get("domain_y_m"),domain_z_m=geo.get("domain_z_m"),span_m=geo.get("span_m"),
    mesh_fingerprint=geo.get("mesh_fingerprint"),foil_geometry_fingerprint=geo.get("foil_geometry_fingerprint"),profile_hash=profile_hash,profile=profile,settings_to_replace=_settings_to_replace(native),
    geometry_audit=str(folder/"geometry_audit.json"),native_inspection=str(folder/"inspection.json"),quality=native.get("quality"),geometry=geo,
    inspected_at=_stamp(),scientific_approval="not_assessed",calm_accepted=False,retained_fields_are_accepted_calm=False,
    note="Owned input.sim retains original physical fields/time. Never treat it as settled C01. New calm preparation or a separately verified matching calm manifest is required.")
   _write(folder/"import_result.json",final)
   return final
 except BaseException as ex:
  message=_safe(str(ex)).strip();v=_update(value,status="inspection_failed",ready=False,reason=message)
  _write(folder/"import_error.json",dict(error=message,at=_stamp(),flow_steps=0,attempt_preserved=True))
  return v

def _audit_cgns(folder):
 """File-only full connectivity audit. Run using installed scientific Python."""
 sys.path.insert(0,"F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029/deps311")
 import numpy as np,h5py
 folder=Path(folder);path=folder/"mesh.CGNS";result=dict(passed=False,errors=[])
 def zone(f):
  found=[]
  def visitor(name,obj):
   if isinstance(obj,h5py.Group) and "GridCoordinates" in obj:found.append(obj)
  f.visititems(visitor)
  if len(found)!=1:raise ValueError("Expected exactly one CGNS volume zone")
  return found[0]
 def wall_segments(z,xyz):
  if "HF_012_wall" not in z:raise ValueError("Foil boundary HF_012_wall missing from CGNS")
  g=z["HF_012_wall"];off=np.asarray(g["ElementStartOffset/ data"],dtype=np.int64);con=np.asarray(g["ElementConnectivity/ data"],dtype=np.int64)-1
  if np.any(np.diff(off)!=4):raise ValueError("Foil side faces must be extruded quadrilaterals")
  nodes=con.reshape(-1,4);lower=np.abs(xyz[nodes,1]-.01)<1e-8
  if np.any(lower.sum(axis=1)!=2):raise ValueError("Foil faces do not span the two expected y planes")
  pairs=nodes[lower].reshape(-1,2);segments=xyz[pairs][:,:,[0,2]]
  adjacency={}
  for a,b in pairs.tolist():
   adjacency.setdefault(a,[]).append(b);adjacency.setdefault(b,[]).append(a)
  if not adjacency or any(len(v)!=2 for v in adjacency.values()):raise ValueError("Foil outline is not one closed manifold curve")
  first=min(adjacency);order=[first];previous=None;current=first
  while True:
   nxt=next(v for v in adjacency[current] if v!=previous)
   if nxt==first:break
   if nxt in order:raise ValueError("Foil outline has multiple/crossed loops")
   order.append(nxt);previous,current=current,nxt
   if len(order)>len(adjacency):raise ValueError("Foil outline traversal failed")
  if len(order)!=len(adjacency):raise ValueError("Multiple foil bodies are not supported")
  poly=xyz[order][:,[0,2]];area=abs(float(np.sum(poly[:,0]*np.roll(poly[:,1],-1)-np.roll(poly[:,0],-1)*poly[:,1])))*.5
  if area<=0:raise ValueError("Foil section has zero area")
  return segments,poly,area
 def distance(points,segments):
  a=segments[:,0,:];v=segments[:,1,:]-a;vv=np.sum(v*v,axis=1)
  if np.any(vv<=0):raise ValueError("Zero-length foil edge")
  maximum=0.
  for i in range(0,len(points),128):
   p=points[i:i+128];delta=p[:,None,:]-a[None,:,:]
   f=np.clip(np.sum(delta*v[None,:,:],axis=2)/vv[None,:],0,1)
   dist=np.sqrt(np.sum((delta-f[:,:,None]*v[None,:,:])**2,axis=2))
   maximum=max(maximum,float(np.min(dist,axis=1).max()))
  return maximum
 try:
  with h5py.File(path,"r") as f:
   z=zone(f);xyz=np.column_stack([np.asarray(z["GridCoordinates/Coordinate"+a+"/ data"]) for a in "XYZ"])
   if not np.isfinite(xyz).all():raise ValueError("CGNS coordinates are non-finite")
   bounds=[[float(xyz[:,i].min()),float(xyz[:,i].max())] for i in range(3)]
   if max(abs(bounds[1][0]-.01),abs(bounds[1][1]-.03),abs(bounds[2][0]+22),abs(bounds[2][1]-8))>1e-8:raise ValueError("Required geometry is y0.01..0.03 and z−22..8m; depth24m/air6m must be retained")
   if bounds[0][0]>-2 or bounds[0][1]<5:raise ValueError("Horizontal domain must include the foil and a clear upstream/downstream core")
   planeerr=float(np.minimum(abs(xyz[:,1]-.01),abs(xyz[:,1]-.03)).max())
   if planeerr>1e-8:raise ValueError("More than two spanwise node planes; one20mm span is required")
   sections=[];volumes=[]
   fingerprint=hashlib.sha256(xyz.astype("<f8").tobytes())
   for name,g in sorted(z.items()):
    if not isinstance(g,h5py.Group) or "ElementConnectivity" not in g:continue
    kind=int(g[" data"][0]);off=np.asarray(g["ElementStartOffset/ data"],dtype=np.int64);con=np.asarray(g["ElementConnectivity/ data"],dtype=np.int64);er=np.asarray(g["ElementRange/ data"],dtype=np.int64)
    if off[0]!=0:off=off-off[0]
    fingerprint.update(name.encode());fingerprint.update(np.array([kind,*er],dtype="<i8").tobytes());fingerprint.update(off.astype("<i8").tobytes());fingerprint.update(con.astype("<i8").tobytes())
    if kind==22:sections.append((name,int(er[0]),off,con))
    elif kind==23:volumes.append((off,con))
    else:raise ValueError("CGNS export must use NGON/NFACE polyhedral connectivity")
   if len(volumes)!=1 or not sections:raise ValueError("Expected one NFACE volume section")
   off,co=volumes[0];cells=len(off)-1
   if cells<=0 or np.any(np.diff(off)<5):raise ValueError("Missing or invalid volume-cell connectivity")
   maximum=max(start+len(o)-2 for _,start,o,_ in sections);group=np.zeros(maximum+1,dtype=np.int8);present=np.zeros(maximum+1,dtype=bool)
   names={"Q2D_span_source":1,"Q2D_span_target":2,"HF_012_wall":3,"DOMAIN.inlet":4,"DOMAIN.outlet":5,"DOMAIN.top":6,"DOMAIN.bottom":7}
   seen=set();maxdisp=0.;source_area=0.;nonpositive=0;boundary_faces={}
   for name,start,o,c in sections:
    counts=np.diff(o);end=start+len(counts)
    if present[start:end].any():raise ValueError("Overlapping CGNS face IDs")
    present[start:end]=True;kind=names.get(name,0);group[start:end]=kind
    nodes=c-1
    if np.any(nodes<0) or np.any(nodes>=len(xyz)):raise ValueError("Face references a missing node")
    if kind:
     seen.add(name);boundary_faces[name]=len(counts)
     axis,target={1:(1,.01),2:(1,.03),4:(0,bounds[0][0]),5:(0,bounds[0][1]),6:(2,8),7:(2,-22)}.get(kind,(None,None))
     if axis is not None and np.max(np.abs(xyz[nodes,axis]-target))>1e-8:raise ValueError("Boundary is not on its expected plane: "+name)
    if kind in (1,2):
     if np.any(counts<3):raise ValueError("Degenerate span polygon")
     if kind==1:
      nxt=np.arange(len(nodes))+1;nxt[o[1:]-1]=o[:-1]
      cross=xyz[nodes,0]*xyz[nodes[nxt],2]-xyz[nodes[nxt],0]*xyz[nodes,2]
      areas=np.abs(np.add.reduceat(cross,o[:-1]))*.5
      nonpositive=int(np.count_nonzero(areas<=0));source_area=float(areas.sum())
    else:
     if np.any(counts!=4):raise ValueError("Every non-span face must be an extruded quadrilateral")
     quad=nodes.reshape(-1,4)
     for begin in range(0,len(quad),50000):
      q=xyz[quad[begin:begin+50000]];low=np.abs(q[:,:,1]-.01)<1e-8
      if np.any(low.sum(axis=1)!=2):raise ValueError("Side face does not connect exactly two nodes on each span plane")
      lower=q[low].reshape(-1,2,3)[:,:,[0,2]];upper=q[~low].reshape(-1,2,3)[:,:,[0,2]]
      direct=np.linalg.norm(lower-upper,axis=2).max(axis=1);reverse=np.linalg.norm(lower-upper[:,::-1],axis=2).max(axis=1)
      maxdisp=max(maxdisp,float(np.minimum(direct,reverse).max(initial=0)))
   if seen!=set(names):raise ValueError("CGNS boundary set differs from the seven required boundaries")
   if maxdisp>1e-10 or nonpositive:raise ValueError("One-span extrusion or positive section-area audit failed")
   ids=np.abs(co)
   if np.any(ids<=0) or np.any(ids>maximum) or not present[ids].all():raise ValueError("Volume references missing faces")
   g=group[ids]
   ns=np.add.reduceat((g==1).astype(np.int32),off[:-1]);nt=np.add.reduceat((g==2).astype(np.int32),off[:-1])
   if np.any(ns!=1) or np.any(nt!=1):raise ValueError("Every volume cell must touch exactly one source and one target span face")
   uses=np.bincount(ids,minlength=maximum+1);signs=np.bincount(ids,weights=np.sign(co),minlength=maximum+1)
   interior=present&(group==0);boundary=present&(group!=0)
   if np.any(uses[interior]!=2) or np.any(signs[interior]!=0) or np.any(uses[boundary]!=1):raise ValueError("Nonmanifold/unclosed or inconsistently oriented face connectivity")
   seg,poly,foil_area=wall_segments(z,xyz)
  expected_area=(bounds[0][1]-bounds[0][0])*30-foil_area
  if abs(source_area-expected_area)>max(1e-7,expected_area*1e-8):raise ValueError("Fluid cross-section area does not match rectangle minus single foil")
  if not REFERENCE_CGNS.is_file():raise ValueError("Fixed foil reference is missing; restore the verified reference before import")
  with h5py.File(REFERENCE_CGNS,"r") as f:
   z=zone(f);rxyz=np.column_stack([np.asarray(z["GridCoordinates/Coordinate"+a+"/ data"]) for a in "XYZ"]);rseg,rpoly,rarea=wall_segments(z,rxyz)
  deviation=max(distance(poly,rseg),distance(rpoly,seg));tolerance=5e-5
  if deviation>tolerance:raise ValueError("Foil position/shape differs from the fixed reference by%.6gm (limit%.6gm); review geometry rather than changing it automatically"%(deviation,tolerance))
  sortedpoly=poly[np.lexsort((poly[:,1],poly[:,0]))]
  result.update(passed=True,cells=cells,domain_x_m=bounds[0],domain_y_m=bounds[1],domain_z_m=bounds[2],span_m=bounds[1][1]-bounds[1][0],depth_m=24,air_height_m=6,
   single_layer_topology=True,cells_with_one_source_and_target_face=cells,span_plane_error_m=planeerr,max_span_xz_displacement_m=maxdisp,
   boundary_faces=boundary_faces,foil_edges=len(seg),foil_section_area_m2=foil_area,foil_reference=str(REFERENCE_CGNS),foil_reference_sha256=_digest(REFERENCE_CGNS),
   foil_max_polyline_deviation_m=deviation,foil_geometry_tolerance_m=tolerance,fluid_section_area_m2=source_area,volume_m3=source_area*.02,
   mesh_fingerprint=fingerprint.hexdigest(),foil_geometry_fingerprint=hashlib.sha256(np.round(sortedpoly,12).astype("<f8").tobytes()).hexdigest(),
   scientific_approval="not_assessed",method="All NGON/NFACE cells and faces checked; no856edge assumption. Dynamic face incidence and exact single-span connectivity; fixedfoil comparison permits only documented surface discretization tolerance.")
 except BaseException as ex:result["errors"].append(str(ex))
 _write(folder/"geometry_audit.json",result)
 print(json.dumps({k:result.get(k) for k in ("passed","cells","domain_x_m","foil_edges","errors")}))
 return 0 if result["passed"] else 2
def main():
 if len(sys.argv)==3 and sys.argv[1]=="--inspect":
  result=_inspect(sys.argv[2]);print(json.dumps(dict(id=result.get("id"),status=result.get("status"),reason=result.get("reason"))));return 0 if result.get("ready") else 2
 if len(sys.argv)==3 and sys.argv[1]=="--audit-cgns":return _audit_cgns(sys.argv[2])
 raise SystemExit("Use the local dashboard to request an inspection, or --inspect <requestid>.")
if __name__=="__main__":raise SystemExit(main())
