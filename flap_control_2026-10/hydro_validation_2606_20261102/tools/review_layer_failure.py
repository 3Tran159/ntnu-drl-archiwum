from pathlib import Path
import sys,json,datetime
import pandas as pd,numpy as np
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h.parent/'flap_poc_2606_20261102/deps'))
import shapely
from shapely.geometry import Polygon
run=Path(sys.argv[1]).resolve();assert run.is_relative_to(h/'cases/SP_C_split0_overset')
native=h/'cases/SP_C_split0_overset/c0_layers36_recut_20261103_015428'
polys={n:Polygon(json.loads((native/(n+'_native_polygon.json')).read_text())) for n in ['main','flap']}
source=h/'cases/SP_C_split0_overset/c0_layers36_zero_storage_20261103_021548'
o=dict(at=datetime.datetime.now().astimezone().isoformat(),run=str(run),coordinate_note='Full-plane polygon centers used to locate mesh error; not true volume centers.',regions={},scientific_approved=False)
for reg in ['Background','FlapOverset']:
 d=pd.read_csv(run/(reg+'_failed_full_plane.csv'));b=pd.read_csv(source/(reg+'_before_full_plane.csv'))
 for col in ['Overset Cell Status','Overset Error Status']:
  assert np.isfinite(d[col]).all() and d[col].abs().max()<10000,'Unavailable native storage'
 pts=shapely.points(d['X (m)'].to_numpy(),d['Z (m)'].to_numpy());idx=shapely.STRtree(shapely.points(b['X (m)'].to_numpy(),b['Z (m)'].to_numpy())).nearest(pts)
 xyz=['X (m)','Y (m)','Z (m)'];match=b.iloc[idx].reset_index(drop=True)
 errors=d[d['Overset Error Status']!=0].copy();ep=shapely.points(errors['X (m)'].to_numpy(),errors['Z (m)'].to_numpy())
 errors['inside_main']=shapely.contains(polys['main'],ep);errors['inside_flap']=shapely.contains(polys['flap'],ep)
 errors['outside_outer_box']=(errors['X (m)']<.732)|(errors['X (m)']>1.55)|(errors['Z (m)']<.02128173276776986-.28)|(errors['Z (m)']>.02128173276776986+.28)
 r=dict(cells=len(d),status_counts={str(k):int(v) for k,v in d['Overset Cell Status'].value_counts().items()},error_counts={str(k):int(v) for k,v in d['Overset Error Status'].value_counts().items()},unique_mesh_matches=len(np.unique(idx)),max_coordinate_difference_m=float(np.abs(d[xyz].to_numpy()-match[xyz].to_numpy()).max()),status_changes=int((d['Overset Cell Status'].to_numpy()!=match['Overset Cell Status'].to_numpy()).sum()),error_cell_count=len(errors),errors_inside_main=int(errors.inside_main.sum()),errors_inside_flap=int(errors.inside_flap.sum()),errors_outside_outer_box=int(errors.outside_outer_box.sum()))
 if len(errors):
  r['error_bounds']={c:[float(errors[c].min()),float(errors[c].max())] for c in xyz}
  r['sample_errors']=errors.head(12).to_dict(orient='records')
 errors.to_csv(run/(reg+'_error_cells_review.csv'),index=False)
 o['regions'][reg]=r
(run/'work_error_localization.json').write_text(json.dumps(o,indent=2),encoding='utf8')
(h/'validation/C0_wall36_error_localization.json').write_text(json.dumps(o,indent=2),encoding='utf8')
print(json.dumps(o,indent=2))
