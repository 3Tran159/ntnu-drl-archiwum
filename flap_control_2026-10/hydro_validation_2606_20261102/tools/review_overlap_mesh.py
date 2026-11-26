from pathlib import Path
import sys,json,datetime
import numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h.parent/'flap_poc_2606_20261102/deps'))
import shapely
from shapely import STRtree
run=Path(sys.argv[1]).resolve();assert run.is_relative_to(h/'cases/SP_C_split0_overset')
control=h/'cases/SP_C_split0_overset/c0_distance_20261102_232050'
bg0=pd.read_csv(control/'Background_final_full_plane.csv');bg1=pd.read_csv(run/'Background_mesh_full_plane.csv')
xyz=['X (m)','Y (m)','Z (m)'];vcol=next(c for c in bg0 if c.startswith('Volume'));qcol=next(c for c in bg0 if c.startswith('Cell Quality'))
tree=STRtree(shapely.points(bg0['X (m)'].to_numpy(),bg0['Z (m)'].to_numpy()))
idx=tree.nearest(shapely.points(bg1['X (m)'].to_numpy(),bg1['Z (m)'].to_numpy()))
matched=bg0.iloc[idx].reset_index(drop=True)
err=np.linalg.norm(bg1[xyz].to_numpy()-matched[xyz].to_numpy(),axis=1)
vr=np.abs(bg1[vcol].to_numpy()/matched[vcol].to_numpy()-1)
qr=np.abs(bg1[qcol].to_numpy()-matched[qcol].to_numpy())
o=dict(at=datetime.datetime.now().astimezone().isoformat(),candidate=str(run),background_control=str(control),comparison='same full-plane representation; not volume-cell centers',background=dict(control_cells=len(bg0),candidate_cells=len(bg1),unique_matches=len(np.unique(idx)),max_center_error_m=float(err.max()),max_relative_volume_error=float(vr.max()),max_quality_error=float(qr.max()),identity_pass=bool(len(bg0)==len(bg1)==len(np.unique(idx)) and err.max()<1e-10 and vr.max()<1e-6 and qr.max()<1e-6)),regions={},scientific_approved=False)
for name in ['Background','FlapOverset']:
 d=pd.read_csv(run/(name+'_mesh_full_plane.csv'));acc=d[d['Overset Cell Status']<0]
 ratio=next(c for c in d if c.startswith('Overset Interpolation Cell Size Ratio'))
 o['regions'][name]=dict(cells=len(d),active=int((d['Overset Cell Status']==0).sum()),inactive=int((d['Overset Cell Status']==1).sum()),acceptors=len(acc),error_cells=int((d['Overset Error Status']!=0).sum()),difficult_cells=int(d['Overset Interpolation Type'].between(4,6).sum()),min_volume=float(d[vcol].min()),min_quality=float(d[qcol].min()),quality_quantiles={str(k):float(d[qcol].quantile(k)) for k in [.001,.01,.5]},acceptor_size_ratio_quantiles={str(k):float(acc[ratio].quantile(k)) for k in [.0,.5,.95,.99,1.]},ratio_above2=int((acc[ratio]>2).sum()),ratio_below_half=int((acc[ratio]<.5).sum()))
o['mesh_review_pass']=bool(o['background']['identity_pass'] and all(r['error_cells']==0 and r['difficult_cells']==0 and r['min_volume']>0 and r['min_quality']>0 for r in o['regions'].values()))
(run/'work_mesh_review.json').write_text(json.dumps(o,indent=2),encoding='utf8')
(h/'validation'/('mesh_review_'+run.name+'.json')).write_text(json.dumps(o,indent=2),encoding='utf8')
print(json.dumps(o,indent=2))
