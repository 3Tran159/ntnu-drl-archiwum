import csv,json,math,statistics,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029')
ref=W/'W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4';p=W/'W20_H24_X4_GPUprop_environmentalOutlet_halfdt10inner_r8'
done=json.loads((p/'completed.json').read_text());ctrl=json.loads((p/'controller_result.json').read_text())
def rows(path):
 with path.open() as f:return [{k:float(v) for k,v in row.items()} for row in csv.DictReader(f)]
def budget(h):
 out={}
 for i in range(2,len(h)):
  a,b,c=h[i-2:i+1];dt=c['time_s']-b['time_s'];v=(3*c['mass_kg']-4*b['mass_kg']+a['mass_kg'])/(2*dt)+c['net_outward_mass_kg_s']
  out[round(c['time_s'],7)]=100*v/c['inward_mass_kg_s']
 return {t:v for t,v in out.items() if .502-1e-8<=t<=.75+1e-8}
a=rows(ref/'history.csv');b=rows(p/'history.csv');ga=rows(ref/'gauges.csv');gb=rows(p/'gauges.csv')
assert all(math.isfinite(v) for x in a+b+ga+gb for v in x.values())
ba=budget(a);bb=budget(b);assert ba and bb
gmap={(round(x['time_s'],6),x['x_m']):x for x in ga}
diff=[x['eta_actual_m']-gmap[(round(x['time_s'],6),x['x_m'])]['eta_actual_m'] for x in gb if (round(x['time_s'],6),x['x_m']) in gmap]
report=dict(updated_at=datetime.datetime.now().astimezone().isoformat(),case=p.name,reference=ref.name,completed=done,source_unchanged=ctrl['source_unchanged'],settings_change='1ms to0.5ms only;10inner andsameBC; restartfromsameR4t0.500state',window_s=[.502,.750],history_finite=True,budget_1ms10inner_max_abs_pct=max(map(abs,ba.values())),budget_halfdt10inner_max_abs_pct=max(map(abs,bb.values())),budget_1ms_mean_abs_pct=statistics.mean(map(abs,ba.values())),budget_halfdt_mean_abs_pct=statistics.mean(map(abs,bb.values())),budget_halfdt_samples_above_0p01=sum(abs(v)>.01 for v in bb.values()),budget_sample_counts=[len(ba),len(bb)],halfdt_all_steps_included=True,max_speed_halfdt_m_s=max(x['max_speed_m_s'] for x in b),phase_bounds=[min(x['alpha_min'] for x in b),max(x['alpha_max'] for x in b)],max_gauge_difference_halfdtminus1ms_mm=max(map(abs,diff))*1000,RMS_gauge_difference_mm=math.sqrt(statistics.mean(v*v for v in diff))*1000,final_mass_difference_kg=b[-1]['mass_kg']-min(a,key=lambda x:abs(x['time_s']-b[-1]['time_s']))['mass_kg'],scope='Targetedtimestep diagnostic, allhalfstepmasssamplesincluded; notlongwave/reflection orfoilforce validation')
report['short_mass_gate_pass']=done['status']=='target_reached' and done['steps']==500 and ctrl['source_unchanged'] and report['budget_halfdt10inner_max_abs_pct']<.01
(R/'wave_halfdt_probe_r8_review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
