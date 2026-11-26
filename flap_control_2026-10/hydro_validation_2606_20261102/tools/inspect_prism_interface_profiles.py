from pathlib import Path
import sys,json,datetime
import pandas as pd,numpy as np
h=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(h.parent/'flap_poc_2606_20261102/deps'))
import shapely
from shapely.geometry import LineString,Point
g=json.loads((h/'geometry/gap_002500um/geometry.json').read_text());line=LineString(g['main_polygon']+[g['main_polygon'][0]])
folder=h/'cases/SP_C_split0_overset/c0_flux_recovery_20261103_012140'
d=pd.read_csv(folder/'Background_continuation_initial_full_plane.csv')
d=d[d['X (m)'].between(.73,.94)&d['Z (m)'].between(.04,.15)].copy()
pts=shapely.points(d['X (m)'].to_numpy(),d['Z (m)'].to_numpy());d['s']=shapely.line_locate_point(line,pts);d['distance_mm']=1000*shapely.distance(line,pts)
out=dict(at=datetime.datetime.now().astimezone().isoformat(),coordinate_caution='Full-plane polygon centers, not exact volume-cell centers. Column selection uses nearest physical surface arclength; inferred layer ordinal is geometric only, not native prism metadata.',profiles={})
for xpos in [.7556,.82,.89,.93]:
 nearwall=d[(d.distance_mm<.03)&(d['X (m)'].between(xpos-.003,xpos+.003))].copy()
 assert len(nearwall)
 row=nearwall.loc[(nearwall['X (m)']-xpos).abs().idxmin()]
 selected=d[(d.s-row.s).abs()<.00015].sort_values('distance_mm')
 selected=selected[selected.distance_mm<20].copy();selected['inferred_ordinal']=np.arange(1,len(selected)+1)
 selected['normal_height_approx_mm']=selected['Volume (m^3)']/(.02*.002857142857)*1000
 cols=['inferred_ordinal','distance_mm','normal_height_approx_mm','Overset Cell Status','Overset Interpolation Cell Size Ratio','Cell Quality','X (m)','Z (m)']
 out['profiles'][str(xpos)]=selected[cols].to_dict(orient='records')
fail=h/'cases/SP_C_split0_overset/c0_momentum_second_20261103_013313'
out['failure_extremes']={}
for region in ['Background','FlapOverset']:
 f=pd.read_csv(fail/(region+'_failure_volume.csv'));f=f[f['Overset Cell Status']==0].copy()
 f['speed']=np.sqrt(sum(f['Velocity['+a+'] (m/s)']**2 for a in 'ijk'));f['p0_meanflow']=f['Pressure (Pa)']+500*f.speed**2
 cols=['X (m)','Z (m)','Absolute Pressure (Pa)','Pressure (Pa)','speed','p0_meanflow','Wall Distance (m)','Turbulent Kinetic Energy (J/kg)','Specific Dissipation Rate (/s)','Cell Quality']
 out['failure_extremes'][region]=dict(min_pressure=f.nsmallest(3,'Absolute Pressure (Pa)')[cols].to_dict(orient='records'),max_head=f.nlargest(3,'p0_meanflow')[cols].to_dict(orient='records'))
p=h/'validation/C0_prism_interface_profiles_and_failure.json';p.write_text(json.dumps(out,indent=2),encoding='utf8')
brief=dict(at=out['at'],failure_extremes=out['failure_extremes'],profiles={k:[r for r in v if r['inferred_ordinal']>=20] for k,v in out['profiles'].items()})
print(json.dumps(brief,indent=2))
