from pathlib import Path
import sys,json,datetime
import numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(h.parent/'flap_poc_2606_20261102/deps'))
import shapely
from shapely.geometry import LineString
g=json.loads((h/'geometry/gap_002500um/geometry.json').read_text())
main=LineString(g['main_polygon']+[g['main_polygon'][0]])
flap=LineString(g['flap_polygon']+[g['flap_polygon'][0]])
sets=[
 ('B',h/'audit/comparison_SP_B_20261102_222923',''),
 ('C40',h/'cases/SP_C_split0_overset/c0_distance_20261102_232050','control_source_'),
 ('C_distance',h/'cases/SP_C_split0_overset/c0_distance_20261102_232050','final_'),
 ('C_refined_failure',h/'cases/SP_C_split0_overset/c0_refined_init_20261103_004626','failure_')]
out=dict(at=datetime.datetime.now().astimezone().isoformat(),method='True active volume-cell coordinates vs closest 2D physical foil segments; identical extruded span. Close-wall meshing chordal errors can affect smallest distances. Not full native wall-distance validation.',cases={})
for name,folder,tag in sets:
 rows=[]
 for region in ['Background','FlapOverset']:
  p=folder/(region+'_'+tag+'volume.csv')
  if not p.exists():continue
  df=pd.read_csv(p);df=df[df['X (m)'].between(.7,1.3)&df['Z (m)'].between(-.13,.2)]
  if 'Overset Cell Status' in df:df=df[df['Overset Cell Status']==0]
  df=df.copy();pts=shapely.points(df['X (m)'].to_numpy(),df['Z (m)'].to_numpy())
  df['geom_main_m']=shapely.distance(pts,main);df['geom_flap_m']=shapely.distance(pts,flap)
  df['geom_nearest_m']=df[['geom_main_m','geom_flap_m']].min(axis=1)
  df['native_to_geometric_ratio']=df['Wall Distance (m)']/df['geom_nearest_m']
  df['region']=region;rows.append(df)
 data=pd.concat(rows,ignore_index=True);case={}
 for region in data.region.unique():
  a=data[data.region==region];selected=a[a.geom_nearest_m.between(.0001,.03)]
  case[region]=dict(active_near=len(a),screen_count=len(selected),ratio_quantiles=selected.native_to_geometric_ratio.quantile([0,.01,.5,.99,1]).to_dict(),ratio_gt2=int((selected.native_to_geometric_ratio>2).sum()),ratio_lt_half=int((selected.native_to_geometric_ratio<.5).sum()),max_absolute_error_mm=float((selected['Wall Distance (m)']-selected.geom_nearest_m).abs().max()*1000))
  other=selected[selected['geom_main_m'] < .1*selected['geom_flap_m']] if region=='FlapOverset' else selected[selected['geom_flap_m'] < .1*selected['geom_main_m']]
  case[region]['closer_other_foil_component']=dict(count=len(other),ratio_quantiles=other.native_to_geometric_ratio.quantile([0,.01,.5,.99,1]).to_dict() if len(other) else {})
  cols=['X (m)','Z (m)','Wall Distance (m)','geom_main_m','geom_flap_m','native_to_geometric_ratio','Specific Dissipation Rate (/s)']
  case[region]['worst_high_ratio']=selected.nlargest(5,'native_to_geometric_ratio')[cols].to_dict(orient='records')
  floor=a[a['Specific Dissipation Rate (/s)']<=1.0001e-10]
  case[region]['omega_floor_count']=len(floor)
  case[region]['floor_distance_ratio_quantiles']=floor.native_to_geometric_ratio.quantile([0,.5,1]).to_dict() if len(floor) else {}
 out['cases'][name]=case
(h/'validation/BC_native_wall_distance_screen.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps({k:{r:{q:v for q,v in a.items() if q not in ['worst_high_ratio']} for r,a in c.items()} for k,c in out['cases'].items()},indent=2))
