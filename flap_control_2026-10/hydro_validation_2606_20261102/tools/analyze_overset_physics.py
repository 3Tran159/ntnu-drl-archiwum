from pathlib import Path
import sys,json,re,datetime
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h/'tools/deps'))
import numpy as np,pandas as pd
sys.path.insert(0,str(h.parent/'flap_poc_2606_20261102/deps'))
from shapely.geometry import Polygon
from shapely import contains_xy
folder=Path(sys.argv[1]).resolve();assert folder.is_relative_to(h/'audit')
assert json.loads((folder/'status.json').read_text())['status']=='inspection_complete'
g=json.loads((h/'geometry/gap_002500um/geometry.json').read_text())
polygons={k:np.array(g[k+'_polygon']) for k in ['main','flap']}
out=dict(at=datetime.datetime.now().astimezone().isoformat(),inspection=str(folder),source_simulation_unchanged=True,physical_solid_intrusion_check=[],interpolation={},wall_area={})
for region in ['Background','FlapOverset']:
 p=folder/(region+'_Volume_Mesh.csv');df=pd.read_csv(p);status=next(c for c in df if c=='Overset Cell Status');ratio=next(c for c in df if 'Interpolation Cell Size Ratio' in c)
 assert df[status].between(-2,1).all(),'Invalid Overset field data cannot pass inspection'
 coords=df[['X (m)','Z (m)']].to_numpy()
 for name,polygon in polygons.items():
  inside=contains_xy(Polygon(polygon).buffer(-1e-6),coords[:,0],coords[:,1])
  active=inside & (df[status].to_numpy()==0)
  types=df.loc[inside,status].value_counts().to_dict()
  out['physical_solid_intrusion_check'].append(dict(region=region,solid=name,all_centroids_inside=int(inside.sum()),active_centroids_inside=int(active.sum()),status_counts={str(k):int(v) for k,v in types.items()}))
  if active.any():df.loc[active].to_csv(folder/(region+'_inside_'+name+'_active.csv'),index=False)
 acc=df[df[status].isin([-1,-2])];rvals=acc[ratio].replace([np.inf,-np.inf],np.nan).dropna()
 out['interpolation'][region]=dict(total_cells=len(df),cell_status_counts={str(k):int(v) for k,v in df[status].value_counts().items()},acceptors=len(acc),size_ratio_quantiles={str(k):float(v) for k,v in rvals.quantile([0,.01,.5,.99,1]).items()})
audit=(folder/'audit.txt').read_text(encoding='utf8')
for region,name in [('Background','main'),('FlapOverset','flap')]:
 poly=polygons[name];expected=float(np.linalg.norm(np.roll(poly,-1,axis=0)-poly,axis=1).sum()*.02)
 area={}
 for rep in ['Volume Mesh','Overset Mesh']:
  vals=[float(line.split('area=')[1]) for line in audit.splitlines() if line.startswith(region+' | '+rep+' | ')]
  area[rep]=dict(sum_m2=sum(vals),native_polygon_expected_m2=expected,relative_difference=sum(vals)/expected-1)
 out['wall_area'][region]=area
out['no_active_cell_centroids_in_solid']=all(row['active_centroids_inside']==0 for row in out['physical_solid_intrusion_check'])
out['representation_used']='Volume Mesh (active and visualization acceptor cells)'
out['full_overset_representation_verified']=False
out['invalid_overset_mesh_export_excluded']=True
out['training_approved']=False
(folder/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf8')
(h/'validation/SP_C_overset_physics_audit.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps(out,indent=2))
