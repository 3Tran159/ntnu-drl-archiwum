from pathlib import Path
import sys,json,datetime
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h/'tools/deps'));sys.path.insert(0,str(h.parent/'flap_poc_2606_20261102/deps'))
import pandas as pd,numpy as np
from shapely.geometry import Polygon,Point
c=h/'cases/SP_C_split0_overset';run=c/'motion_20261102_194119/steady_init_20261102_200834/steady_init_20261102_202530/steady_init_20261102_203046/urans_from_steady_20261102_203650/stabilize_20261102_203650'
df=pd.read_csv(run/'history.csv');result={}
for key in ['CL_hydro','CD','Mh_Nm']:
 ws=[]
 for end in [100,125,150]:
  new=df.iloc[end-25:end][key];old=df.iloc[end-50:end-25][key]
  ws.append(dict(end_step=end,mean=float(new.mean()),relative_mean_change=float(abs(new.mean()-old.mean())/max(.01 if key!='CD' else .001,abs(new.mean()))),relative_range=float((new.max()-new.min())/max(.01 if key!='CD' else .001,abs(new.mean())))))
 result[key]=ws
g=json.loads((h/'geometry/gap_002500um/geometry.json').read_text())
audit=h/'audit/overset_physics_20261102_203904';deviation=[]
for region,solid in [('Background','main'),('FlapOverset','flap')]:
 p=audit/(region+'_inside_'+solid+'_active.csv')
 if not p.exists():continue
 pts=pd.read_csv(p);poly=Polygon(g[solid+'_polygon']);dist=np.array([poly.exterior.distance(Point(x,z)) for x,z in pts[['X (m)','Z (m)']].to_numpy()])
 imax=int(dist.argmax());deviation.append(dict(region=region,samples=len(pts),max_penetration_native_polygon_m=float(dist.max()),median_m=float(np.median(dist)),worst_xyz=pts.iloc[imax][['X (m)','Y (m)','Z (m)']].to_dict(),interpretation='Own-wall discretization versus original polygon, not cross-body Overset intrusion; mesh boundary must be considered.'))
out=dict(at=datetime.datetime.now().astimezone().isoformat(),source_result=str(run),checkpoint=str(run/'checkpoint.sim'),time_s=float(df.time_s.iloc[-1]),dt_s=.002,windows=result,mass_max_last_75=float(df.tail(75).mass_imbalance_relative.max()),pabs_min_all_Pa=float(df.p_absolute_min_Pa.min()),CL_mean=float(df.tail(25).CL_hydro.mean()),CD_mean=float(df.tail(25).CD.mean()),Mh_mean_Nm=float(df.tail(25).Mh_Nm.mean()),own_boundary_deviation=deviation,full_overset_audit_pending=True,training_approved=False)
(h/'validation/NIGHT_C0_readonly_review.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps(out,indent=2))
