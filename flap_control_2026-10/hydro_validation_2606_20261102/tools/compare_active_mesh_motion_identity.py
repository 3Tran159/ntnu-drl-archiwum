from pathlib import Path
import sys,json,numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h.parent/'flap_poc_2606_20261102/deps'))
from shapely import points,STRtree
old=pd.read_csv(h/'cases/SP_C_split0_overset/mesh_cells.csv');root=h/'cases/SP_C_split0_overset/c0_distance_20261102_232050'
a=old[['X (m)','Z (m)']].to_numpy();tree=STRtree(points(a));out={}
for region in ['Background','FlapOverset']:
 d=pd.read_csv(root/(region+'_control_source_volume.csv'));d=d[d['Overset Cell Status']==0];b=d[['X (m)','Z (m)']].to_numpy();idx=tree.nearest(points(b));dist=np.linalg.norm(a[idx]-b,axis=1);rel=np.abs(d['Volume (m^3)'].to_numpy()-old['Volume (m^3)'].to_numpy()[idx])/old['Volume (m^3)'].to_numpy()[idx]
 worst=int(dist.argmax())
 out[region]=dict(representation='Volume Mesh for both source and current, active subset only',active_cells=len(d),nearest_unique=len(np.unique(idx)),matched_within_1nm=int((dist<1e-9).sum()),distance_quantiles_m={str(q):float(np.quantile(dist,q)) for q in [0,.5,.99,1]},relative_volume_difference_quantiles={str(q):float(np.quantile(rel,q)) for q in [0,.5,.99,1]},worst_distance_source_xz=a[idx[worst]].tolist(),worst_distance_current_xz=b[worst].tolist())
(h/'validation/C0_active_mesh_motion_identity.json').write_text(json.dumps(out,indent=2),encoding='utf8')
p=h/'validation/C0_mesh_before_after_motion.json';j=json.loads(p.read_text());j['interpretation_warning']='This compares computational volume-cell centers with extracted plane polygon centers, which are different representations. It does NOT establish mesh deformation. Use C0_active_mesh_motion_identity.json for same-representation active-cell comparison.';p.write_text(json.dumps(j,indent=2),encoding='utf8')
print(json.dumps(out,indent=2))
