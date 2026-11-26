"""Read-only native field visualization ingestor for NTNU hydrofoil.
Never opens solver/checkpoint, writes only project_dashboard/flow_cache.
All scalar grids contain means of measured active-cell-center data; no time interpolation.
"""
from __future__ import annotations
import csv, datetime as dt, hashlib, json, logging, math, re, statistics, threading
from collections import Counter
from pathlib import Path
import ramp_live

HERE=Path(__file__).resolve().parent
CACHE=HERE/"flow_cache"
CAMP=ramp_live.CAMP
GEOM=CAMP/"geometry"/"current_geometry.json"
LIMIT=12339.0  # user specified Flow Field diagnostic threshold [Pa]
REGIONS={
 "foil": (-0.16, 1.66, -0.36, 0.36),
 "nose": (-0.08, 0.32, -0.14, 0.14),
 "hinge": (0.83, 1.11, -0.13, 0.14),
 "wake": (1.12, 1.85, -0.28, 0.28),
}
NX=400
NY=220
SLOTS=("u","w","speed","pabs","gauge","k","omega","mu","quality","volume")
COLS={
 "u":"Velocity[i] (m/s)","v":"Velocity[j] (m/s)","w":"Velocity[k] (m/s)",
 "pabs":"Absolute Pressure (Pa)","gauge":"Pressure (Pa)",
 "k":"Turbulent Kinetic Energy (J/kg)","omega":"Specific Dissipation Rate (/s)",
 "mu":"Turbulent Viscosity Ratio","quality":"Cell Quality",
 "volume":"Volume (m^3)", "x":"X (m)","z":"Z (m)",
 "status":"Overset Cell Status","error":"Overset Error Status",
}
_LOCK=threading.Lock()
_MEM={}
def stamp(path):
 try:
  s=path.stat()
  return (s.st_size,s.st_mtime_ns)
 except OSError:return None
def read_small(path,cap=900000):
 try:
  s=path.stat()
  if s.st_size>cap:return ""
  return path.read_text(encoding="utf-8-sig",errors="replace")
 except OSError:return ""
def time_from_audit(folder,suffix):
 txt=read_small(folder/("full_audit_"+suffix+".txt"),2000)
 m=re.search(r"\btime\s*=\s*([0-9.]+)",txt)
 return float(m.group(1)) if m else None
def frames():
 queue=ramp_live.read_json(ramp_live.QUEUE)
 selected=ramp_live.select_experiment(queue)
 candidates=[]
 for job in selected["jobs"]:
  base=ramp_live.safe_output(job.get("output"))
  if not base:continue
  stages=[
   ("readback","readback","volume"),
   ("final","final","volume"),
   ("latest","latest","full_plane"),
  ]
  for code,audit,typ in stages:
   # Exclude unproven 'latest' time when a final field exists with its own audit.
   fn0=base/("Background_"+code+"_"+typ+".csv")
   fn1=base/("FlapOverset_"+code+"_"+typ+".csv")
   t=time_from_audit(base,audit if code!="latest" else "latest")
   if t is None or not fn0.is_file() or not fn1.is_file():continue
   try:
    with fn0.open(encoding="utf-8-sig") as f:head=next(csv.reader(f))
    with fn1.open(encoding="utf-8-sig") as f:head1=next(csv.reader(f))
   except (OSError,StopIteration,csv.Error):continue
   have_velocity=all(COLS[k] in head and COLS[k] in head1 for k in ("u","v","w"))
   have_pressure=all(COLS[k] in head and COLS[k] in head1 for k in ("pabs","gauge"))
   if code=="latest" and (base/("Background_final_volume.csv")).exists():
    continue
   uid=str(job.get("run_id") or base.name)+"-"+code
   candidates.append({
    "id":uid,"kind":"flow" if have_velocity and have_pressure else "mesh",
    "time_s":t,"job_id":job.get("id"),"stage":code,"run_id":job.get("run_id"),
    "folder":str(base),"source_type":typ,
    "background":str(fn0),"flap":str(fn1),
    "has_velocity":have_velocity,"has_pressure":have_pressure,
    "has_turbulence":all(COLS[k] in head for k in ("k","omega","mu")),
    "mtime":max(fn0.stat().st_mtime,fn1.stat().st_mtime),
    "sources":[str(fn0),str(fn1)],
    "wall_main":str(base/("main_"+code+"_wall.csv")) if (base/("main_"+code+"_wall.csv")).exists() else None,
    "wall_flap":str(base/("flap_"+code+"_wall.csv")) if (base/("flap_"+code+"_wall.csv")).exists() else None,
    "mesh_foil":str(base/"mesh_foil.png") if (base/"mesh_foil.png").exists() else None,
    "mesh_hinge":str(base/"mesh_hinge.png") if (base/"mesh_hinge.png").exists() else None,
   })
 # Remove duplicate time+same experiment geometry data from latest export aliases.
 candidates.sort(key=lambda x:(x["time_s"],x["mtime"]))
 return candidates
def zones():
 queue=ramp_live.read_json(ramp_live.QUEUE)
 sel=ramp_live.select_experiment(queue)
 newest=(sel["active"] or (sel["jobs"][-1] if sel["jobs"] else None))
 base=ramp_live.safe_output(newest.get("output")) if newest else None
 path=base/"pressure_zones.csv" if base else None
 out=[]
 if path and path.is_file() and path.stat().st_size<1000000:
  try:
   with path.open(newline="",encoding="utf-8-sig") as stream:
    for rec in csv.DictReader(stream):
     try:
      out.append({"t":round(float(rec["time_s"]),7),"step":int(rec["step"]),
       "zone":rec["zone"],"pabs":float(rec["pabs_Pa"]),
       "x":float(rec["x_m"]),"z":float(rec["z_m"])})
     except (KeyError,ValueError):pass
  except (OSError,csv.Error):pass
 return {"points":out,"source":str(path) if path else None,"mtime":stamp(path) if path else None}
def manifest():
 data=ramp_live.snapshot()
 ff=frames()
 return {"experiment":data.get("experiment_id"),"ramp": {
   "t":(data.get("current") or {}).get("t"),"angle":(data.get("current") or {}).get("actual_angle"),
   "state":data.get("state"),"history_rows":data.get("rows"),
   "source_age_s":data.get("source_age_s")},
   "frames":[{k:v for k,v in frame.items() if k not in ("folder","background","flap","wall_main","wall_flap","mesh_foil","mesh_hinge")} for frame in ff],
   "latest_vector_field_time_s":max((x["time_s"] for x in ff if x["has_velocity"]),default=None),
   "last_mesh_time_s":max((x["time_s"] for x in ff),default=None),
   "regions":{k:{"x0":v[0],"x1":v[1],"z0":v[2],"z1":v[3]} for k,v in REGIONS.items()},
   "threshold_pa":LIMIT,"rho_kg_m3":1000,
   "color_info":"Cell-bin means of observed active fluid cell centers; unsupported bins transparent; no temporal interpolation.",
   "limitations":["Only exported volume snapshots contain velocity and full pressure fields.",
      "Latest ramp mesh export contains cell quality/status, not pressure or velocity.",
      "Star absolute/gauge pressure are separate native columns.",
      "Cp requires validated local reference pressure p∞(z); disabled until supplied.",
      "Exact mesh edges require native mesh images or cell connectivity, not cell centroids."],
   "pressure_zones":zones(),"read_only":True}
def allowed_frame(identifier):
 return next((f for f in frames() if f["id"]==identifier),None)
def file_signature(frame,region):
 names=[Path(frame["background"]),Path(frame["flap"])]
 for key in ("wall_main","wall_flap"):
  if frame.get(key):names.append(Path(frame[key]))
 return [frame["id"],region,*[(str(f),stamp(f)) for f in names]]
def fv(row,key):
 try:
  n=float(row[COLS[key]])
  return n if math.isfinite(n) else None
 except (ValueError,KeyError,TypeError):return None
def wall_samples(path,bounds):
 if not path:return []
 p=Path(path)
 if not p.is_file() or p.stat().st_size>700000:return []
 result=[]
 try:
  with p.open(newline="",encoding="utf-8-sig") as f:
   for rec in csv.DictReader(f):
    try:
     x,z=float(rec["X (m)"]),float(rec["Z (m)"])
     if bounds[0]-.03<=x<=bounds[1]+.03 and bounds[2]-.04<=z<=bounds[3]+.04:
      result.append([round(x,7),round(z,7)])
    except (ValueError,KeyError):pass
 except (OSError,csv.Error):return []
 return result[:3500]
def process(frame,region):
 if region not in REGIONS:raise ValueError("unknown region")
 xmin,xmax,zmin,zmax=REGIONS[region]
 dx=(xmax-xmin)/NX; dz=(zmax-zmin)/NY
 layers=[]
 for layer,source in (("Background",frame["background"]),("FlapOverset",frame["flap"])):
  p=Path(source)
  before=stamp(p)
  if before is None or before[0]>140000000:raise ValueError("missing or oversized source")
  bins={}
  counts=Counter()
  checked=Counter()
  try:
   with p.open(newline="",encoding="utf-8-sig") as f:
    reader=csv.DictReader(f)
    for raw in reader:
     try:
      code=int(float(raw.get(COLS["status"],"999")))
      x=float(raw[COLS["x"]]);z=float(raw[COLS["z"]])
     except (ValueError,KeyError):continue
     counts[code]+=1
     if x<xmin or x>=xmax or z<zmin or z>=zmax:continue
     checked[code]+=1
     if code!=0:continue # exclude inactive and acceptor interpolation from physical field.
     xi=int((x-xmin)/dx);zi=int((z-zmin)/dz)
     key=zi*NX+xi
     item=bins.get(key)
     if item is None:
      item=[0]+[0.0]*len(SLOTS)+[0.0]*len(SLOTS)
      bins[key]=item
     item[0]+=1
     for index,k in enumerate(SLOTS):
      if k=="speed":
       vec=[fv(raw,axis) for axis in ("u","v","w")]
       val=math.hypot(*vec) if all(v is not None for v in vec) else None
      else:val=fv(raw,k)
      if val is not None:
       item[1+index]+=val
       item[1+len(SLOTS)+index]+=1
  except (OSError,UnicodeError,csv.Error) as exc:raise ValueError(str(exc))
  if stamp(p)!=before:raise ValueError("CFD source changed while being read; try again")
  entries=[]
  for index,val in bins.items():
   means=[round(val[1+i]/val[1+len(SLOTS)+i],5) if val[1+len(SLOTS)+i] else None
           for i in range(len(SLOTS))]
   entries.append([index%NX,index//NX,val[0]]+means)
  layers.append({"name":layer,"cells":entries,"all_status_counts":dict(counts),
    "roi_status_counts":dict(checked),"source":str(p),"mtime_ns":before[1],
    "active_code":0,"acceptor_code":-2,"inactive_code":1})
 return {"frame_id":frame["id"],"time_s":frame["time_s"],"stage":frame["stage"],
  "job_id":frame.get("job_id"),"source_files":frame["sources"],
  "kind":frame["kind"],"has_velocity":frame["has_velocity"],
  "has_pressure":frame["has_pressure"],"has_turbulence":frame["has_turbulence"],
  "region":region,"bounds":{"x0":xmin,"x1":xmax,"z0":zmin,"z1":zmax},
  "nx":NX,"ny":NY,"columns":["i","j","cell_count",*SLOTS],
  "layers":layers,"walls":[{"part":"Main","points":wall_samples(frame.get("wall_main"),(xmin,xmax,zmin,zmax))},
       {"part":"Flap","points":wall_samples(frame.get("wall_flap"),(xmin,xmax,zmin,zmax))}],
  "processing":"Bin-averaged active cell-center values; no donor/acceptor blending; no temporal interpolation.",
  "threshold_pa":LIMIT,"read_only":True}
def frame_data(identifier,region):
 frame=allowed_frame(identifier)
 if not frame:raise ValueError("unrecognized frame")
 if region not in REGIONS:raise ValueError("unrecognized region")
 signature=file_signature(frame,region)
 key=hashlib.sha256(json.dumps(signature,ensure_ascii=False).encode()).hexdigest()[:28]
 path=CACHE/(key+".json")
 token=(identifier,region,key)
 with _LOCK:
  hit=_MEM.get(token)
  if hit:return hit
 try:
  if path.is_file() and path.stat().st_size<24000000:
   data=json.loads(path.read_text("utf-8"))
   if data.get("frame_id")==identifier and data.get("region")==region:
    with _LOCK:_MEM[token]=data
    return data
 except (OSError,ValueError):pass
 out=process(frame,region)
 # Disk cache is entirely inside the independent dashboard; never source campaign.
 CACHE.mkdir(exist_ok=True)
 temp=CACHE/(key+".partial")
 try:
  temp.write_text(json.dumps(out,separators=(",",":"),ensure_ascii=False,allow_nan=False),encoding="utf-8")
  temp.replace(path)
 except OSError:logging.warning("Flow cache could not be saved",exc_info=True)
 with _LOCK:
  if len(_MEM)>14:_MEM.clear()
  _MEM[token]=out
 return out
def native_image(identifier,which):
 f=allowed_frame(identifier)
 if not f or which not in ("mesh_foil","mesh_hinge"):return None
 name=f.get(which)
 p=Path(name) if name else None
 if p and p.is_file() and p.suffix.lower()==".png" and p.stat().st_size<7000000:
  return p
 return None
