import csv,json,math,statistics,hashlib,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029')
ref=W/'W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4';p=W/'W20_H24_X4_GPUprop_environmentalOutlet_inner20probe_r6'
done=json.loads((p/'completed.json').read_text());ctrl=json.loads((p/'controller_result.json').read_text())
def rows(path):
 with path.open() as f:return [{k:float(v) for k,v in row.items()} for row in csv.DictReader(f)]
def budget(h):
 out={}
 for i in range(2,len(h)):
  a,b,c=h[i-2:i+1];dt=c['time_s']-b['time_s'];v=(3*c['mass_kg']-4*b['mass_kg']+a['mass_kg'])/(2*dt)+c['net_outward_mass_kg_s']
  out[round(c['time_s'],6)]=100*v/c['inward_mass_kg_s']
 return out
a=rows(ref/'history.csv');b=rows(p/'history.csv');ga=rows(ref/'gauges.csv');gb=rows(p/'gauges.csv')
assert all(math.isfinite(v) for x in a+b+ga+gb for v in x.values())
ba=budget(a);bb=budget(b);common=sorted(set(ba)&set(bb));common=[t for t in common if .502-1e-8<=t<=.75+1e-8]
assert common
gmap={(round(x['time_s'],6),x['x_m']):x for x in ga}
diff=[(x['x_m'],x['eta_actual_m']-gmap[(round(x['time_s'],6),x['x_m'])]['eta_actual_m']) for x in gb if (round(x['time_s'],6),x['x_m']) in gmap]
report=dict(updated_at=datetime.datetime.now().astimezone().isoformat(),case=p.name,reference=ref.name,completed=done,source_unchanged=ctrl['source_unchanged'],settings_change='10 to20inner only;SO1ms andsameBC; restartfromsameR4t0.500state',window_s=[min(common),max(common)],history_finite=True,budget_10inner_max_abs_pct=max(abs(ba[t]) for t in common),budget_20inner_max_abs_pct=max(abs(bb[t]) for t in common),budget_10inner_mean_abs_pct=statistics.mean(abs(ba[t]) for t in common),budget_20inner_mean_abs_pct=statistics.mean(abs(bb[t]) for t in common),budget_20inner_samples_above_0p01=sum(abs(bb[t])>.01 for t in common),max_speed_20inner_m_s=max(x['max_speed_m_s'] for x in b),phase_bounds=[min(x['alpha_min'] for x in b),max(x['alpha_max'] for x in b)],max_gauge_difference_20minus10_mm=max(abs(v) for x,v in diff)*1000,RMS_gauge_difference_mm=math.sqrt(statistics.mean(v*v for x,v in diff))*1000,final_mass_difference_kg=b[-1]['mass_kg']-min(a,key=lambda x:abs(x['time_s']-b[-1]['time_s']))['mass_kg'],scope='Short targetedinnerconvergence diagnostic; notlongwave/reflection orfoilforce validation')
report['short_mass_gate_pass']=done['status']=='target_reached' and done['steps']==250 and ctrl['source_unchanged'] and report['budget_20inner_max_abs_pct']<.01
(R/'wave_inner20_probe_r6_review.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
