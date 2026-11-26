"""Independent CGNS topology/volume/preservation audit. No STAR or solver control."""
import os
for _key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):
 os.environ[_key]="1"
import sys,json,csv,math,hashlib,collections
from pathlib import Path
sys.path.insert(0,"F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029/deps311")
import numpy as np,h5py

def digest(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
 return h.hexdigest()
def read_mesh(path):
 with h5py.File(path,"r") as f:
  z=f["Base/fluid"];xyz=np.column_stack([z["GridCoordinates/Coordinate"+a+"/ data"][...] for a in "XYZ"])
  sections={}
  for name,g in z.items():
   if isinstance(g,h5py.Group) and "ElementConnectivity" in g:
    sections[name]={"type":int(g[" data"][0]),"start":int(g["ElementRange/ data"][0]),
                    "end":int(g["ElementRange/ data"][1]),"offset":g["ElementStartOffset/ data"][...],
                    "connect":g["ElementConnectivity/ data"][...]}
  bcs={k:z["ZoneBC/"+k+"/PointRange/ data"][...].ravel().tolist() for k in z["ZoneBC"]
       if isinstance(z["ZoneBC"][k],h5py.Group) and "PointRange" in z["ZoneBC"][k]}
  size=z[" data"][...].ravel().tolist()
 return xyz,sections,bcs,size
def polys(sec):
 c=sec["connect"]-1;o=sec["offset"]
 return [c[o[i]:o[i+1]] for i in range(len(o)-1)]
def area2(xyz,p):
 q=xyz[p][:,[0,2]];q=q-q[0]
 return float(.5*np.sum(q[:,0]*np.roll(q[:,1],-1)-np.roll(q[:,0],-1)*q[:,1]))
def signature_poly(xyz,p):
 # An exact coordinate signature independent of index relabelling/cyclic start.
 q=[tuple(float(v) for v in row) for row in xyz[p]]
 k=min(range(len(q)),key=q.__getitem__);a=q[k:]+q[:k]
 q=list(reversed(q));k=min(range(len(q)),key=q.__getitem__);b=q[k:]+q[:k]
 return tuple(min(a,b))
def edges(polygons):
 d=collections.defaultdict(list)
 for i,p in enumerate(polygons):
  for a,b in zip(p,np.roll(p,-1)):
   d[tuple(sorted((int(a),int(b))))].append((i,int(a),int(b)))
 return d
def wall_edges(xyz,sec):
 out=[]
 for p in polys(sec):
  lo=[int(i) for i in p if abs(xyz[i,1]-.01)<1e-12]
  if len(lo)!=2:raise AssertionError("Foil face is not an exact extruded edge")
  out.append(tuple(sorted(lo)))
 return out

def audit(folder):
 folder=Path(folder);build=json.loads((folder/"build_result.json").read_text())
 source=Path(build["source"]);target=folder/"mesh.CGNS"
 assert digest(source)==build["source_sha256"],"Source changed"
 assert digest(target)==build["output_sha256"],"Output changed after build"
 x,s,bcs,size=read_mesh(target);sx,ss,sbcs,ssize=read_mesh(source)
 face_secs={k:v for k,v in s.items() if v["type"]==22}
 assert s["fluid"]["type"]==23
 nfaces=max(v["end"] for v in face_secs.values())
 avec=np.zeros((nfaces+1,3));cent=np.zeros((nfaces+1,3));present=np.zeros(nfaces+1,dtype=np.int8)
 for name,v in face_secs.items():
  off=v["offset"];lens=np.diff(off);c=v["connect"]-1
  assert len(lens)==v["end"]-v["start"]+1 and lens.min()>=3
  p=x[c];cc=np.add.reduceat(p,off[:-1],axis=0)/lens[:,None]
  rel=p-np.repeat(cc,lens,axis=0)
  nxt=np.arange(len(c))+1;nxt[off[1:]-1]=off[:-1]
  av=.5*np.add.reduceat(np.cross(rel,rel[nxt]),off[:-1],axis=0)
  ids=np.arange(v["start"],v["end"]+1);present[ids]+=1;avec[ids]=av;cent[ids]=cc
  assert np.all(np.linalg.norm(av,axis=1)>0),"Zero area face"
  if name in bcs:assert bcs[name]==[v["start"],v["end"]],"BC range mismatch"
 assert np.all(present[1:]==1),"Face numbering gaps/overlap"
 cv=s["fluid"];off=cv["offset"];conn=cv["connect"];ids=np.abs(conn)
 assert ids.min()>=1 and ids.max()<=nfaces
 signs=np.sign(conn);lengths=np.diff(off);C=len(lengths)
 assert C==size[1] and len(x)==size[0]
 assert np.all(lengths>=5)
 counts=np.bincount(ids,minlength=nfaces+1)
 orientation=np.bincount(ids,weights=signs,minlength=nfaces+1)
 internal=face_secs["Polyfaces_fluid"];ii=np.arange(internal["start"],internal["end"]+1)
 boundary=np.setdiff1d(np.arange(1,nfaces+1),ii)
 assert np.all(counts[ii]==2) and np.all(orientation[ii]==0),"Interior face ownership/sign failure"
 assert np.all(counts[boundary]==1) and np.all(orientation[boundary]==1),"Boundary ownership/sign failure"
 src=face_secs["Q2D_span_source"];tgt=face_secs["Q2D_span_target"]
 ns=np.add.reduceat(((ids>=src["start"])&(ids<=src["end"])).astype(int),off[:-1])
 nt=np.add.reduceat(((ids>=tgt["start"])&(ids<=tgt["end"])).astype(int),off[:-1])
 assert np.all(ns==1) and np.all(nt==1),"Not one cell through span"
 cp=polys(src);tp=polys(tgt);sp=polys(ss["Q2D_span_source"])
 assert len(cp)==C and len(tp)==C
 source_nodes=np.unique(src["connect"]-1);target_nodes=np.unique(tgt["connect"]-1)
 assert np.max(abs(x[source_nodes,1]-.01))<1e-12 and np.max(abs(x[target_nodes,1]-.03))<1e-12
 assert len(source_nodes)+len(target_nodes)==len(x)
 pair_error=0.
 for a,b in zip(cp,tp):
  assert len(a)==len(b)
  qa=x[a][:,[0,2]];qb=x[b[::-1]][:,[0,2]]
  pair_error=max(pair_error,float(np.max(np.abs(qa-qb))))
 assert pair_error==0.,"Target projection mismatch"
 ci=np.repeat(np.arange(C),lengths)
 cc=cent[np.arange(src["start"],src["end"]+1)]
 face_terms=signs*np.einsum("ij,ij->i",avec[ids],cent[ids]-cc[ci])/3.
 volumes=np.add.reduceat(face_terms,off[:-1])
 closure=np.add.reduceat(avec[ids]*signs[:,None],off[:-1],axis=0)
 all_area=np.add.reduceat(np.linalg.norm(avec[ids],axis=1),off[:-1])
 relclosure=np.linalg.norm(closure,axis=1)/all_area
 assert np.all(volumes>0),"Nonpositive signed volume"
 assert relclosure.max()<1e-10,"Unclosed cell"
 areas=np.array([area2(x,p) for p in cp])
 assert np.all(areas>0),"Wrong source face winding"
 assert np.all(abs(volumes-areas*.02)<=1e-13+1e-8*areas*.02),"Independent 3D volume/extrusion mismatch"
 es=edges(cp)
 assert all(len(v) in (1,2) for v in es.values()),"Nonmanifold 2D edge"
 assert all(len(v)==1 or v[0][1:]==v[1][1:][::-1] for v in es.values()),"Inconsistent edge winding"
 # Boundary planes and area normals are independent of builder labels.
 xmin,xmax,zmin,zmax=build["target_bounds_m"]
 planes={"inlet":(0,xmin,-1),"outlet":(0,xmax,1),"bottom":(2,zmin,-1),"top":(2,zmax,1)}
 plane_result={}
 for suffix,(axis,pos,sgn) in planes.items():
  names=[k for k in face_secs if k.endswith("."+suffix)];assert len(names)==1
  v=face_secs[names[0]];nodes=v["connect"]-1;fi=np.arange(v["start"],v["end"]+1)
  err=float(abs(x[nodes,axis]-pos).max());assert err<1e-10
  assert np.all(avec[fi,axis]*sgn>0),"Boundary face points inward"
  expected=(zmax-zmin)*.02 if axis==0 else (xmax-xmin)*.02
  measured=float(np.linalg.norm(avec[fi],axis=1).sum())
  assert abs(measured-expected)<1e-9
  plane_result[suffix]={"plane_error_m":err,"face_count":len(fi),"area_m2":measured,"expected_area_m2":expected}
 # Exact foil edge coordinates and all kept-cell coordinates.
 swall=wall_edges(sx,ss["HF_012_wall"]);wall=wall_edges(x,s["HF_012_wall"])
 def edge_sig(xx,e):return tuple(sorted(tuple(float(v) for v in xx[i]) for i in e))
 assert len(swall)==856 and len(wall)==856
 assert sorted(edge_sig(sx,e) for e in swall)==sorted(edge_sig(x,e) for e in wall),"Foil changed"
 with (folder/"source_cell_map.csv").open() as f: maps=list(csv.DictReader(f))
 assert len(maps)==len(sp)
 status={};kept=0;cropped=0;removed=0;protected=0
 lost=0.
 for i,m in enumerate(maps):
  assert int(m["source_cell_index0"])==i
  j=int(m["output_cell_index0"]);st=m["status"];status[i]=st
  sa=abs(area2(sx,sp[i]))
  if st=="keep":
   assert j>=0 and signature_poly(sx,sp[i])==signature_poly(x,cp[j]),"Kept source polygon modified"
   kept+=1;oa=areas[j]
  elif st=="crop":
   assert j>=0;cropped+=1;oa=areas[j];assert 0<oa<sa
   assert np.min(sx[sp[i],0])<xmax<np.max(sx[sp[i],0]),"Crop is not at remote plane"
  elif st=="remove":
   removed+=1;oa=0.;assert j==-1 and sx[sp[i],0].min()>=xmax
  else:raise AssertionError("Unknown mapping status")
  lost+=sa-oa
  xx=sx[sp[i],0]
  if xx.max()>=-5 and xx.min()<=5:assert st=="keep";protected+=1
 # Identify consecutive quadrilateral prism chains from each original foil edge.
 se=edges(sp);prism=set();layer_counts=[]
 for wall_e in swall:
  edge=wall_e;visited=set();n=0
  for _ in range(80):
   choices=[c for c,*_ in se[edge] if c not in visited]
   if len(choices)!=1:break
   c=choices[0];p=sp[c]
   if len(p)!=4:break
   opposite=[tuple(sorted((int(a),int(b)))) for a,b in zip(p,np.roll(p,-1))
             if a not in edge and b not in edge]
   if len(opposite)!=1:break
   visited.add(c);prism.add(c);n+=1;edge=opposite[0]
  layer_counts.append(n)
 assert all(status[i]=="keep" for i in prism),"Prism chain cell changed"
 # Rectangle-minus-foil analytical area, using unchanged wall edge coordinates.
 wall_direct=[]
 for edge in swall:
  own=se[edge];assert len(own)==1
  _,a,b=own[0];wall_direct.append((a,b))
 foil_signed=.5*math.fsum(sx[a,0]*sx[b,2]-sx[b,0]*sx[a,2] for a,b in wall_direct)
 foil_area=abs(foil_signed)
 expected=(xmax-xmin)*(zmax-zmin)-foil_area
 totalA=float(math.fsum(areas));totalV=float(math.fsum(volumes))
 assert abs(totalA-expected)<1e-7 and abs(totalV-expected*.02)<2e-9
 oldmax=float(sx[:,0].max());expected_lost=(oldmax-xmax)*(zmax-zmin)
 assert abs(lost-expected_lost)<1e-7,"Removed area differs from cropped remote rectangle"
 assert digest(source)==build["source_sha256"],"Source changed during audit"
 result={"status":"independent_file_geometry_gates_passed_pending_STAR_import",
  "source":str(source),"source_unchanged":True,"source_sha256":build["source_sha256"],"output_sha256":digest(target),
  "cells":C,"span_m":.02,"x_bounds_m":[xmin,xmax],"z_bounds_m":[zmin,zmax],"wave_depth_m":24,
  "single_span_cells":C,"max_target_source_xz_error_m":pair_error,"negative_or_zero_volumes":int(np.sum(volumes<=0)),
  "minimum_signed_volume_m3":float(volumes.min()),"maximum_relative_cell_closure_error":float(relclosure.max()),
  "nonmanifold_edges":0,"inconsistent_internal_face_signs":0,"boundary_planes":plane_result,
  "foil_edges":len(wall),"foil_coordinates_unchanged":True,"foil_area_m2":foil_area,
  "source_cell_counts":{"kept":kept,"cropped":cropped,"removed":removed},
  "protected_interval_cells_unchanged":protected,"identified_prism_chain_cells_unchanged":len(prism),
  "prism_chain_layer_histogram":dict(collections.Counter(layer_counts)),
  "cropped_area_m2":lost,"expected_cropped_remote_rectangle_area_m2":expected_lost,
  "total_area_m2":totalA,"expected_rectangle_minus_foil_area_m2":expected,
  "total_signed_volume_m3":totalV,"expected_volume_m3":expected*.02,
  "flow_steps":0,"STAR_launched":False,
  "pending":["STAR import and native cell-quality/face-validity checks","Matched calm for this domain/settings",
             "FifthOrder L10 wave configuration and wave-specific numerical/propagation/FS accuracy checks"],
  "interpretation":"File-level conservative geometry/topology support only; not a STAR quality or flow acceptance result."}
 (folder/"independent_geometry_audit.json").write_text(json.dumps(result,indent=2))
 print(json.dumps(result),flush=True)
 return result
if __name__=="__main__":audit(sys.argv[1])
