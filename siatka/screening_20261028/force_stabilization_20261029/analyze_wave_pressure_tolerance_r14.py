"""Audit single-control R14 without changing scientific gates."""
from pathlib import Path
import csv,json,math,re,statistics
import run_until_settled as e
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029')
A=W/'W20_H24_X4_GPUprop_environmentalOutlet_pressureTol01_dt1ms_r14'
B=W/'W20_H24_X4_GPUprop_environmentalOutlet_phaseBudget_dt1ms_r10'
done=e.read(A/'controller_result.json',{})
assert done.get('source_unchanged') and done['completed']['steps']==250 and done['returncode']==0
def csvrows(p):
 with p.open() as f:return list(csv.DictReader(f))
phase=csvrows(A/'native_phase_budget.csv')
water=csvrows(A/'native_water_per_inner.csv');air=csvrows(A/'native_air_per_inner.csv')
assert len(water)==len(air)==2500
wk=list(water[0])[1];ak=list(air[0])[1]
assert all(int(w['Iteration'])==5001+i==int(air[i]['Iteration']) for i,w in enumerate(water))
assert all(math.isfinite(float(w[wk])) and math.isfinite(float(a[ak])) for w,a in zip(water,air))
traces=[]
for row in phase:
 j=int(row['step']);mass=float(row['inward_mass_kg_s']);dt=float(row['dt_s'])
 idx=range((j-1)*10,j*10)
 seq=[100*(abs(float(water[k][wk]))+abs(float(air[k][ak])))/dt/mass for k in idx]
 end=sum([float(water[j*10-1][wk]),float(air[j*10-1][ak])])/dt
 assert abs(end-float(row['native_sum_error_kg_s']))<1e-8
 traces.append(dict(time_s=float(row['time_s']),native_abs_phase_error_pct_by_inner=seq))
peak=max(phase,key=lambda r:float(r['native_abs_sum_pct_inward_mass']))
pi=int(peak['step'])-1
log=(A/'star.log').read_text(encoding='utf-8',errors='replace')
pat=r'(Solving PPrime\.\.\.|Solving for volume fractions\.\.\.)(.*?)Total Reduction in Residual:\s*([0-9.eE+\-]+)'
blocks=[]
for m in re.finditer(pat,log,re.S):
 body=m.group(2);it=re.search(r'Total Iterations:\s*(\d+)',body)
 ini=re.search(r'Ini\s+\S+\s+([0-9.eE+\-]+)',body);fin=re.search(r'Final Residual:\s*([0-9.eE+\-]+)',body)
 blocks.append(dict(solver='pressure' if 'PPrime' in m.group(1) else 'VOF',cycles=int(it[1]),initial=float(ini[1]),final=float(fin[1]),ratio=float(m[3])))
stats={}
for solver in ('VOF','pressure'):
 b=[x for x in blocks if x['solver']==solver]
 assert b
 stats[solver]=dict(solves=len(b),cycles_min=min(x['cycles'] for x in b),cycles_max=max(x['cycles'] for x in b),ratio_min=min(x['ratio'] for x in b),ratio_median=statistics.median(x['ratio'] for x in b),ratio_max=max(x['ratio'] for x in b),all_below_relative_tolerance=all(x['ratio']<=(.1 if solver=='VOF' else .01) for x in b),cycle_cap_hits=sum(x['cycles']>=30 for x in b),nonzero_final_residuals=sum(x['final']>0 for x in b),requested_tolerance=.1 if solver=='VOF' else .01,stopping_interpretation='Inspect achieved ratios and cap hits; all_below_relative_tolerance must be true before attributing results to requested solve accuracy')
metrics={}
rows=[r for r in phase if float(r['time_s'])>=.502-1e-8]
for col in ('native_abs_sum_pct_inward_mass','bdf2_plus_faceflux_pct_inward_mass'):
 vals=[abs(float(r[col])) for r in rows];metrics[col]=dict(max_abs=max(vals),mean_abs=statistics.mean(vals))
def gauges(p):
 return {(round(float(r['time_s']),6),float(r['x_m'])):float(r['eta_actual_m']) for r in csvrows(p/'gauges.csv') if .502-1e-8<=float(r['time_s'])<=.750+1e-8}
ga,gb=gauges(A),gauges(B);d=[1000*(ga[k]-gb[k]) for k in ga.keys()&gb.keys()]
counts=csvrows(A/'amg_cycle_counts.csv')
out=dict(updated_at=e.stamp(),case=A.name,status='single_control_pressure_tolerance_probe_completed',source_unchanged=True,settings='SO1ms10inner unchanged; ONLY pressure AMGrelative tolerance .1 to .01; VOFtol .1 and allothercontrols unchanged',completed_time_s=done['completed']['time_s'],expected_inner_samples=2500,water_samples=len(water),air_samples=len(air),native_inner_endpoints_match_physical_history=True,AMG=stats,AMG_API_counters_constant=all(float(r['vof_cycles_this_step'])==float(r['pressure_cycles_this_step'])==0 for r in counts),AMG_counter_limitation='API total cycles remained unchanged; use actual LOW log solves, not this getter, for sequencing or cost',metrics=metrics,peak_time_s=float(peak['time_s']),peak_inner_trace=traces[pi],native_vs_BDF2_max_difference_percentage_points=max(abs(float(r['native_sum_pct_inward_mass'])-float(r['bdf2_plus_faceflux_pct_inward_mass'])) for r in rows),gauge_difference_vs_R10_max_mm=max(map(abs,d)),gauge_difference_vs_R10_RMS_mm=math.sqrt(statistics.mean(x*x for x in d)),short_mass_gate_pass=all(v['max_abs']<.01 for v in metrics.values()),original_threshold_pct=.01,scope='Single-control linear-accuracy test; retains original mass criterion and native/legacy diagnostics. Longer propagation needs scientific review; no wave force admission.')
history=csvrows(A/'history.csv')
out['independent_fields_finite']=all(all(math.isfinite(float(r[k])) for k in ['max_speed_m_s','max_CFL','interface_CFL','alpha_min','alpha_max','mass_kg','water_volume_m3','net_outward_mass_kg_s']) for r in history)
out['max_speed_m_s']=max(float(r['max_speed_m_s']) for r in history)
out['max_interface_CFL']=max(float(r['interface_CFL']) for r in history)
out['alpha_min']=min(float(r['alpha_min']) for r in history);out['alpha_max']=max(float(r['alpha_max']) for r in history)
out['phase_vs_mixture_max_flux_difference_kg_s']=max(abs(float(r['faceflux_minus_phaseflux_kg_s'])) for r in rows)
def cost(path,lo=.510,hi=.650):
 h=csvrows(path/'history.csv');inc=[float(y['wall_s'])-float(x['wall_s']) for x,y in zip(h,h[1:]) if lo-1e-8<=float(y['time_s'])<=hi+1e-8]
 return dict(window_s=[lo,hi],mean_s_per_step=statistics.mean(inc),median_s_per_step=statistics.median(inc),samples=len(inc))
out['cost_same_instrumentation']=dict(R14=cost(A),R12=cost(W/'W20_H24_X4_GPUprop_environmentalOutlet_linearTrace_dt1ms_r12'))
out['native_inventory_consistent']=out['native_vs_BDF2_max_difference_percentage_points']<1e-6 and out['phase_vs_mixture_max_flux_difference_kg_s']<1e-6
out['actual_linear_targets_achieved']=all(v['all_below_relative_tolerance'] and v['cycle_cap_hits']==0 for v in stats.values())
out['short_mass_gate_pass']=out['short_mass_gate_pass'] and out['independent_fields_finite'] and out['native_inventory_consistent'] and out['actual_linear_targets_achieved'] and out['gauge_difference_vs_R10_max_mm']<2 and out['max_speed_m_s']<25
e.write(R/'wave_pressure_tolerance_r14_review.json',out)
e.write(A/'native_inner_trace_analysis.json',dict(traces=traces,AMG_solves=blocks))
print(json.dumps(out,indent=2))
