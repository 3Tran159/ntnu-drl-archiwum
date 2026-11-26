import csv,statistics,json
from pathlib import Path
p=Path('E:/ntnu/quasi2d_waves_20261029/W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4')
with (p/'history.csv').open() as f:h=[{k:float(v) for k,v in x.items()} for x in csv.DictReader(f)]
r=[]
for i in range(2,len(h)):
 a,b,c=h[i-2:i+1];dt=c['time_s']-b['time_s'];v=(3*c['mass_kg']-4*b['mass_kg']+a['mass_kg'])/(2*dt)+c['net_outward_mass_kg_s']
 r.append(dict(time=c['time_s'],pct=100*v/c['inward_mass_kg_s'],residual=v,speed=c['max_speed_m_s'],net=c['net_outward_mass_kg_s']))
out=dict(top=sorted(r,key=lambda x:abs(x['pct']),reverse=True)[:10],windows=[])
for lo,hi in [(0,.2),(.2,.5),(.5,.75),(.75,1),(1,1.2)]:
 v=[x for x in r if lo<x['time']<=hi+1e-9];out['windows'].append(dict(window=[lo,hi],max_abs_pct=max(abs(x['pct']) for x in v),mean_abs_pct=statistics.mean(abs(x['pct']) for x in v),samples_above_0p01=sum(abs(x['pct'])>.01 for x in v)))
print(json.dumps(out,indent=2))
