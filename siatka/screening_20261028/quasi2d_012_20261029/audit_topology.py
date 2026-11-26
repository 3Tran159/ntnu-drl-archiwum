import sys,json,collections,csv
from pathlib import Path
root=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029")
sys.path.insert(0,str(root/"deps311"))
import h5py,numpy as np
folder=root/(sys.argv[1] if len(sys.argv)>1 else "M01")
f=h5py.File(folder/"mesh.CGNS");z=f["Base/fluid"]
xyz=np.column_stack([z["GridCoordinates/Coordinate"+a+"/ data"][...] for a in "XYZ"])
faces={};groups={}
for name,g in z.items():
 if isinstance(g,h5py.Group) and "ElementConnectivity" in g and int(g[" data"][0])==22:
  off=g["ElementStartOffset/ data"][...];con=g["ElementConnectivity/ data"][...]-1;start=int(g["ElementRange/ data"][0])
  ids=[]
  for i in range(len(off)-1):
   ix=start+i;faces[ix]=con[off[i]:off[i+1]];ids.append(ix)
  groups[name]=ids
srcset=set(groups["Q2D_span_source"]);tgtset=set(groups["Q2D_span_target"])
cg=z["fluid"];co=cg["ElementConnectivity/ data"][...];off=cg["ElementStartOffset/ data"][...]
one=0;bad=[]
for i in range(len(off)-1):
 ids=set(np.abs(co[off[i]:off[i+1]]))
 ns=len(ids&srcset);nt=len(ids&tgtset)
 if ns==1 and nt==1:one+=1
 else:bad.append([i,ns,nt])
y=xyz[:,1];pairs={}
for name,ids in groups.items():
 if name.startswith("Q2D_span"):continue
 for fi in ids:
  v=faces[fi]
  for a,b in zip(v,np.roll(v,-1)):
   if abs(y[a]-y[b])>.01:
    if y[a]>y[b]:a,b=b,a
    if a in pairs:assert pairs[a]==b
    pairs[a]=b
disp=np.array([xyz[b,[0,2]]-xyz[a,[0,2]] for a,b in pairs.items()])
srcnodes=np.array(sorted(pairs))
tgt_nodes=np.array([pairs[a] for a in srcnodes])
polys=[faces[i] for i in groups["Q2D_span_source"]]
edge_cells=collections.defaultdict(list)
for i,v in enumerate(polys):
 for a,b in zip(v,np.roll(v,-1)):edge_cells[tuple(sorted((int(a),int(b))))].append(i)
records=[]
for fi in groups["HF_012_wall"]:
 v=faces[fi];v=[int(i) for i in v if abs(y[i]-.01)<1e-8];assert len(v)==2
 wall=tuple(sorted(v));edge=wall;visited=set();count=0;h1=None;total=0.
 mid0=xyz[v][:,[0,2]].mean(axis=0);tang=xyz[v[1],[0,2]]-xyz[v[0],[0,2]];length=np.linalg.norm(tang);normal=np.array([-tang[1],tang[0]])/length
 for _ in range(40):
  cs=[c for c in edge_cells[edge] if c not in visited]
  if len(cs)!=1:break
  c=cs[0];poly=polys[c]
  if len(poly)!=4:break
  opp=[tuple(sorted((int(a),int(b)))) for a,b in zip(poly,np.roll(poly,-1)) if a not in edge and b not in edge]
  if len(opp)!=1:break
  visited.add(c);oldmid=xyz[list(edge)][:,[0,2]].mean(axis=0);newmid=xyz[list(opp[0])][:,[0,2]].mean(axis=0)
  thickness=abs(np.dot(newmid-oldmid,normal))
  if count==0:h1=float(thickness)
  count+=1;total+=thickness;edge=opp[0]
 records.append({"x":float(mid0[0]),"z":float(mid0[1]),"edge_length_m":float(length),"continuous_quad_layers":count,"first_thickness_m":h1,"total_thickness_m":float(total)})
perim=sum(r["edge_length_m"] for r in records)
result={"cells":len(off)-1,"cells_with_one_source_and_target_face":one,"invalid_cells":bad[:20],"single_layer_topology":one==len(off)-1,"node_y_min_m":float(y.min()),"node_y_max_m":float(y.max()),"source_nodes":len(srcnodes),"paired_nodes":len(pairs),"max_target_source_xz_displacement_m":float(np.linalg.norm(disp,axis=1).max()),"y_plane_error_m":float(np.minimum(abs(y-.01),abs(y-.03)).max()),"foil_edges":len(records),"foil_perimeter_m":perim,"area_fraction_any_quad_layers":sum(r["edge_length_m"] for r in records if r["continuous_quad_layers"]>=1)/perim,"area_fraction_at_least_15_quad_layers":sum(r["edge_length_m"] for r in records if r["continuous_quad_layers"]>=15)/perim,"layer_histogram":dict(collections.Counter(r["continuous_quad_layers"] for r in records)),"first_thickness_min_m":min(r["first_thickness_m"] for r in records if r["first_thickness_m"] is not None),"first_thickness_max_m":max(r["first_thickness_m"] for r in records if r["first_thickness_m"] is not None),"method":"CGNS connectivity: every volume cell must touch both span planes; prism coverage inferred by following consecutive quadrilateral cells normal to each foil edge, area weighted."}
(folder/"topology_audit.json").write_text(json.dumps(result,indent=2))
with (folder/"foil_layer_topology.csv").open("w",newline="") as out:
 w=csv.DictWriter(out,fieldnames=records[0].keys());w.writeheader();w.writerows(records)
print(json.dumps(result,indent=2))
