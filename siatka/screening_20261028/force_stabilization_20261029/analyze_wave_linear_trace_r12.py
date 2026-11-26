"""Audit reporting-only R12 without changing scientific gates."""
from pathlib import Path
import csv,json,math,re,statistics
import run_until_settled as e
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029')
A=W/'W20_H24_X4_GPUprop_environmentalOutlet_linearTrace_dt1ms_r12'
B=W/'W20_H24_X4_GPUprop_environmentalOutlet_phaseBudget_dt1ms_r10'
done=e.read(A/'controller_result.json',{})
assert done.get('source_unchanged') and done['completed']['steps']==150 and done['returncode']==0
def csvrows(p):
 with p.open() as f:return list(csv.DictReader(f))
phase=csvrows(A/'native_phase_budget.csv')
water=csvrows(A/'native_water_per_inner.csv');air=csvrows(A/'native_air_per_inner.csv')
assert len(water)==len(air)==1500
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
 stats[solver]=dict(solves=len(b),cycles_min=min(x['cycles'] for x in b),cycles_max=max(x['cycles'] for x in b),ratio_min=min(x['ratio'] for x in b),ratio_median=statistics.median(x['ratio'] for x in b),ratio_max=max(x['ratio'] for x in b),all_below_relative_tolerance=all(x['ratio']<=.1 for x in b),cycle_cap_hits=sum(x['cycles']>=30 for x in b),nonzero_final_residuals=sum(x['final']>0 for x in b),inferred_active_stop='relative convergence tolerance 0.1; cap 30 not reached; epsilon 0 not reached')
metrics={}
rows=[r for r in phase if float(r['time_s'])>=.502-1e-8]
for col in ('native_abs_sum_pct_inward_mass','bdf2_plus_faceflux_pct_inward_mass'):
 vals=[abs(float(r[col])) for r in rows];metrics[col]=dict(max_abs=max(vals),mean_abs=statistics.mean(vals))
def gauges(p):
 return {(round(float(r['time_s']),6),float(r['x_m'])):float(r['eta_actual_m']) for r in csvrows(p/'gauges.csv') if .502-1e-8<=float(r['time_s'])<=.650+1e-8}
ga,gb=gauges(A),gauges(B);d=[1000*(ga[k]-gb[k]) for k in ga.keys()&gb.keys()]
counts=csvrows(A/'amg_cycle_counts.csv')
out=dict(updated_at=e.stamp(),case=A.name,status='reporting_trace_completed',source_unchanged=True,settings='unchanged SO1ms10inner; native monitoring and LOW AMG logging only',completed_time_s=done['completed']['time_s'],expected_inner_samples=1500,water_samples=len(water),air_samples=len(air),native_inner_endpoints_match_physical_history=True,AMG=stats,AMG_API_counters_constant=all(float(r['vof_cycles_this_step'])==float(r['pressure_cycles_this_step'])==0 for r in counts),AMG_counter_limitation='API total cycles remained unchanged; use actual LOW log solves, not this getter, for sequencing or cost',metrics=metrics,peak_time_s=float(peak['time_s']),peak_inner_trace=traces[pi],native_vs_BDF2_max_difference_percentage_points=max(abs(float(r['native_sum_pct_inward_mass'])-float(r['bdf2_plus_faceflux_pct_inward_mass'])) for r in rows),gauge_difference_vs_R10_max_mm=max(map(abs,d)),gauge_difference_vs_R10_RMS_mm=math.sqrt(statistics.mean(x*x for x in d)),short_mass_gate_pass=all(v['max_abs']<.01 for v in metrics.values()),original_threshold_pct=.01,scope='Diagnostic trace; relative tolerance is observed linear stopping condition but causation of mass plateau remains unproven. No wave force admission.')
e.write(R/'wave_linear_trace_r12_review.json',out)
e.write(A/'native_inner_trace_analysis.json',dict(traces=traces,AMG_solves=blocks))
print(json.dumps(out,indent=2))
