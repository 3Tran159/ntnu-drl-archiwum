from pathlib import Path
import csv,json
R=Path(__file__).resolve().parent; W=Path('E:/ntnu/quasi2d_waves_20261029')
cases={'r4':'W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4','r6':'W20_H24_X4_GPUprop_environmentalOutlet_inner20probe_r6','r8':'W20_H24_X4_GPUprop_environmentalOutlet_halfdt10inner_r8'}
out={}
for key,case in cases.items():
 h=list(csv.DictReader((W/case/'history.csv').open()))
 data=[{k:float(v) for k,v in row.items()} for row in h]
 peaks=[]
 for i in range(2,len(data)):
  a,b,c=data[i-2:i+1];dt=c['time_s']-b['time_s']
  if c['time_s']<.502-1e-9 or c['time_s']>.75+1e-9:continue
  acc=(1.5*c['mass_kg']-2*b['mass_kg']+.5*a['mass_kg'])/dt
  res=acc+c['net_outward_mass_kg_s'];pct=100*res/c['inward_mass_kg_s']
  peaks.append(dict(t=c['time_s'],budget_pct=pct,accumulation_kg_s=acc,outward_kg_s=c['net_outward_mass_kg_s'],water_m3=c['water_volume_m3'],mass_kg=c['mass_kg'],speed=c['max_speed_m_s'],cfl=c['interface_CFL']))
 out[key]=dict(peaks=sorted(peaks,key=lambda x:abs(x['budget_pct']),reverse=True)[:8])
(R/'wave_mass_peak_details.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out))
