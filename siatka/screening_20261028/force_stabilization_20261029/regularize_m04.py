import sys,json,shutil,collections
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029';out=Q/'M04/repair_regular_layers';out.mkdir(exist_ok=True)
sys.path.insert(0,str(Q/'deps311'))
import h5py,numpy as np
target=out/'mesh_regular_layers.CGNS'
if target.exists():raise RuntimeError('Preserve earlier repair attempt')
shutil.copy2(Q/'M04/mesh.CGNS',target)
with h5py.File(target,'r+') as f:
 z=f['Base/fluid'];xyz=np.column_stack([z['GridCoordinates/Coordinate'+a+'/ data'][...] for a in 'XYZ']);original=xyz.copy()
 faces={};groups={}
 for name,g in z.items():
  if isinstance(g,h5py.Group) and 'ElementConnectivity' in g and int(g[' data'][0])==22:
   off=g['ElementStartOffset/ data'][...];con=g['ElementConnectivity/ data'][...]-1;start=int(g['ElementRange/ data'][0])
   groups[name]=list(range(start,start+len(off)-1))
   for i in range(len(off)-1):faces[start+i]=con[off[i]:off[i+1]]
 polys=[faces[k] for k in groups['Q2D_span_source']]
 edgecells=collections.defaultdict(list);pairs={}
 for i,v in enumerate(polys):
  for a,b in zip(v,np.roll(v,-1)):edgecells[tuple(sorted((int(a),int(b))))].append(i)
 for v in faces.values():
  for a,b in zip(v,np.roll(v,-1)):
   if abs(xyz[a,1]-xyz[b,1])>.01:
    if xyz[a,1]>xyz[b,1]:a,b=b,a
    assert a not in pairs or pairs[a]==b
    pairs[int(a)]=int(b)
 columns={}
 for fi in groups['HF_012_wall']:
  v=[int(i) for i in faces[fi] if abs(xyz[i,1]-.01)<1e-8];assert len(v)==2
  edge=v;chains=[[v[0]],[v[1]]];visited=set()
  for layer in range(40):
   candidates=[c for c in edgecells[tuple(sorted(edge))] if c not in visited]
   if len(candidates)!=1:break
   ci=candidates[0];poly=list(map(int,polys[ci]))
   if len(poly)!=4:break
   nxt=[]
   for old in edge:
    ix=poly.index(old);neighbors=[poly[(ix-1)%4],poly[(ix+1)%4]]
    other=[x for x in neighbors if x not in edge]
    if len(other)!=1:raise RuntimeError('Ambiguous layer edge')
    nxt.append(other[0])
   for k in range(2):chains[k].append(nxt[k])
   edge=nxt;visited.add(ci)
  if len(chains[0])==41:
   for chain in chains:
    key=chain[0]
    if key in columns:assert columns[key]==chain
    else:columns[key]=chain
 ratio=1.1875157536
 fraction=np.cumsum(ratio**np.arange(40));fraction/=fraction[-1]
 proposals={}
 for chain in columns.values():
  wall=original[chain[0]];outer=original[chain[-1]]
  for k,node in enumerate(chain[1:-1]):
   pt=wall+(outer-wall)*fraction[k]
   if node in proposals:assert np.linalg.norm(proposals[node]-pt)<1e-10
   proposals[node]=pt
 for node,pt in proposals.items():xyz[node]=pt
 src=np.array(sorted(pairs));dst=np.array([pairs[k] for k in src])
 xyz[dst,0]=xyz[src,0];xyz[dst,2]=xyz[src,2];xyz[src,1]=.01;xyz[dst,1]=.03
 areas=[]
 for v in polys:
  pp=xyz[v][:,[0,2]];areas.append(.5*np.sum(pp[:,0]*np.roll(pp[:,1],-1)-np.roll(pp[:,0],-1)*pp[:,1]))
 areas=np.array(areas);bad=int((areas*np.sign(np.median(areas))<=0).sum())
 wallnodes=np.unique(np.concatenate([faces[k] for k in groups['HF_012_wall']]))
 wallsource=wallnodes[np.abs(original[wallnodes,1]-.01)<1e-8]
 result={'regularized_full_layer_columns':len(columns),'modified_source_interior_nodes':len(proposals),'max_source_node_change_m':float(np.linalg.norm(xyz[src]-original[src],axis=1).max()),'source_wall_change_m':float(np.linalg.norm(xyz[wallsource]-original[wallsource],axis=1).max()),'inverted_or_zero_source_cells':bad,'min_source_area_m2':float(abs(areas).min()),'layer_growth_ratio':ratio,'description':'Regularize full 40-layer columns between unchanged wall and outermost-layer nodes using geometric spacing; exact translation across span. Original geometry, connectivity and core nodes retained on source plane.'}
 (out/'repair_geometry.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
 if bad:raise RuntimeError('Repair still has reversed source cells; not accepted')
 for i,a in enumerate('XYZ'):z['GridCoordinates/Coordinate'+a+'/ data'][...]=xyz[:,i]
# Prepare isolated import into original invalid model; no original writes.
shutil.copy2(Q/'M04/mesh.sim',out/'input_invalid_copy.sim')
macro=(R/'ImportExactM04.java').read_text().replace('ImportExactM04','ImportRegularM04').replace('M04/repair_exact_extrusion','M04/repair_regular_layers').replace('mesh_exact_extrusion.CGNS','mesh_regular_layers.CGNS')
(R/'ImportRegularM04.java').write_text(macro)
job={'source':str(out/'input_invalid_copy.sim'),'macro':str(R/'ImportRegularM04.java'),'log':str(out/'import.log'),'np':2,'timeout_s':1800}
(R/'m04_regular_job.json').write_text(json.dumps(job))
