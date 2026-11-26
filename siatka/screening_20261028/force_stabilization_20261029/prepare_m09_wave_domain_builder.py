from pathlib import Path
R=Path(__file__).resolve().parent
out=R/'extend_m09_wave_domain.py'
if out.exists():raise RuntimeError('Existing domain-extension builder preserved')
s=(R/'extrude_source_mesh.py').read_text()
s=s.replace('source=Path(sys.argv[1]);target=Path(sys.argv[2])','source=Path(sys.argv[1]);target=Path(sys.argv[2]);xmin=float(sys.argv[3]);xmax=float(sys.argv[4]);dxmax=.2\nsource_sha=hashlib.sha256(source.read_bytes()).hexdigest()')
anchor=' face_groups={name:[] for name in groups};face_edges={}'
insert=''' # Append orthogonal remote strips. Every original polygon and coordinate remains unchanged.
 original_cells=C;original_nodes=N;original_volume=sum(areas)*.02
 old_xmin=float(xyz[:N,0].min());old_xmax=float(xyz[:N,0].max())
 zmin=float(xyz[:N,2].min());zmax=float(xyz[:N,2].max())
 if not (xmin<old_xmin and xmax>old_xmax and abs(zmin+22)<1e-8 and abs(zmax-8)<1e-8):raise RuntimeError('Unexpected extension bounds')
 points=xyz[:N].tolist();extensions=[]
 def bname(suffix):
  found=[k for k in groups if k.endswith('.'+suffix)]
  if len(found)!=1:raise RuntimeError('Ambiguous boundary '+suffix)
  return found[0]
 for side,old,new in [('inlet',old_xmin,xmin),('outlet',old_xmax,xmax)]:
  name=bname(side);wall_edges=[edge for edge,label in boundary_map.items() if label==name]
  ids=sorted({v for edge in wall_edges for v in edge},key=lambda v:points[v][2])
  if len(ids)!=len(wall_edges)+1 or {tuple(sorted(x)) for x in zip(ids[:-1],ids[1:])}!=set(wall_edges):raise RuntimeError('Remote boundary is not a simple vertical chain')
  if max(abs(points[v][0]-old) for v in ids)>1e-8:raise RuntimeError('Remote plane mismatch')
  cols=int(np.ceil(abs(new-old)/dxmax));prev=ids
  for xx in np.linspace(old,new,cols+1)[1:]:
   current=[]
   for v in ids:
    current.append(len(points));points.append([float(xx),.01,float(points[v][2])])
   for lo in range(len(ids)-1):
    a,b=prev[lo:lo+2];c,d=current[lo:lo+2]
    poly=np.array([c,a,b,d] if new<old else [a,c,d,b],dtype=np.int64)
    area=abs(float(xx)-points[a][0])*(points[b][2]-points[a][2])
    if area<=0:raise RuntimeError('Nonpositive extension cell')
    ci=len(surface);surface.append(poly);areas.append(area)
    for aa,bb in zip(poly,np.roll(poly,-1)):edges[tuple(sorted((int(aa),int(bb))))].append((ci,int(aa),int(bb)))
   boundary_map[tuple(sorted((prev[0],current[0])))]=bname('bottom')
   boundary_map[tuple(sorted((prev[-1],current[-1])))]=bname('top')
   prev=current
  for aa,bb in zip(prev[:-1],prev[1:]):boundary_map[tuple(sorted((aa,bb)))]=name
  extensions.append({'side':side,'old_x_m':old,'new_x_m':new,'columns':cols,'max_dx_m':abs(new-old)/cols,'boundary_vertical_segments':len(ids)-1})
 N=len(points);C=len(surface);xyz=np.vstack([np.array(points),np.array(points)]);xyz[:N,1]=.01;xyz[N:,1]=.03
 expected_volume=original_volume+((xmax-xmin)-(old_xmax-old_xmin))*(zmax-zmin)*.02
 if abs(sum(areas)*.02-expected_volume)>1e-8:raise RuntimeError('Extension volume mismatch')
 if not np.array_equal(xyz[:original_nodes][:,[0,2]],xyz0[used][:,[0,2]]):raise RuntimeError('Protected coordinates changed')
'''
assert s.count(anchor)==1;s=s.replace(anchor,insert+anchor)
s=s.replace("result['output_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()","""result.update({'purpose':'M09-derived 4-lambda wave-domain mesh preparation; not a new accepted flow result','source_mesh':'M09','source_sha256':source_sha,'original_cells':original_cells,'added_cells':C-original_cells,'original_cell_polygons_preserved':True,'original_coordinates_preserved':True,'extensions':extensions,'expected_volume_m3':expected_volume,'x_bounds_m':[xmin,xmax],'z_bounds_m':[zmin,zmax],'wave_depth_m':24,'pending':['Independent STAR mesh import/quality/boundary checks','Matched calm run on this domain','Wave propagation/time/domain validation'],'method':'Preserve all M09 source polygons; append conforming orthogonal strips at the original inlet and outlet, then rebuild exact one-cell-span connectivity'})
if hashlib.sha256(source.read_bytes()).hexdigest()!=source_sha:raise RuntimeError('Source mesh changed')
result['output_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()""")
out.write_text(s)
compile(s,str(out),'exec')
print('M09 domain-extension builder prepared; no flow launched.')
