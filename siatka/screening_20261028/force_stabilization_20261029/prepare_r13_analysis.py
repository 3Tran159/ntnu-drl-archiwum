from pathlib import Path
import ast
R=Path(__file__).resolve().parent;p=R/'analyze_wave_vof_tolerance_r13.py'
assert not p.exists()
s=(R/'analyze_wave_linear_trace_r12.py').read_text().replace('linearTrace_dt1ms_r12','vofTol001_dt1ms_r13').replace("['steps']==150","['steps']==250").replace('==1500','==2500').replace('expected_inner_samples=1500','expected_inner_samples=2500').replace('<=.650+1e-8','<=.750+1e-8')
s=s.replace("status='reporting_trace_completed'","status='single_control_VOF_tolerance_probe_completed'").replace("settings='unchanged SO1ms10inner; native monitoring and LOW AMG logging only'","settings='SO1ms10inner unchanged; ONLY VOF AMGrelative tolerance .1 to .001; pressuretol .1 and allothercontrols unchanged'")
s=s.replace("all(x['ratio']<=.1 for x in b)","all(x['ratio']<=(.001 if solver=='VOF' else .1) for x in b)")
s=s.replace("inferred_active_stop='relative convergence tolerance 0.1; cap 30 not reached; epsilon 0 not reached'","requested_tolerance=.001 if solver=='VOF' else .1,stopping_interpretation='Inspect achieved ratios and cap hits; all_below_relative_tolerance must be true before attributing results to requested solve accuracy'")
s=s.replace("scope='Diagnostic trace; relative tolerance is observed linear stopping condition but causation of mass plateau remains unproven. No wave force admission.'","scope='Single-control linear-accuracy test; retains original mass criterion and native/legacy diagnostics. Longer propagation needs scientific review; no wave force admission.'")
needle="e.write(R/'wave_linear_trace_r12_review.json',out)"
assert needle in s
extra="""history=csvrows(A/'history.csv')
out['independent_fields_finite']=all(all(math.isfinite(float(r[k])) for k in ['max_speed_m_s','max_CFL','interface_CFL','alpha_min','alpha_max','mass_kg','water_volume_m3','net_outward_mass_kg_s']) for r in history)
out['max_speed_m_s']=max(float(r['max_speed_m_s']) for r in history)
out['max_interface_CFL']=max(float(r['interface_CFL']) for r in history)
out['alpha_min']=min(float(r['alpha_min']) for r in history);out['alpha_max']=max(float(r['alpha_max']) for r in history)
out['phase_vs_mixture_max_flux_difference_kg_s']=max(abs(float(r['faceflux_minus_phaseflux_kg_s'])) for r in rows)
def cost(path,lo=.510,hi=.650):
 h=csvrows(path/'history.csv');inc=[float(y['wall_s'])-float(x['wall_s']) for x,y in zip(h,h[1:]) if lo-1e-8<=float(y['time_s'])<=hi+1e-8]
 return dict(window_s=[lo,hi],mean_s_per_step=statistics.mean(inc),median_s_per_step=statistics.median(inc),samples=len(inc))
out['cost_same_instrumentation']=dict(R13=cost(A),R12=cost(W/'W20_H24_X4_GPUprop_environmentalOutlet_linearTrace_dt1ms_r12'))
out['native_inventory_consistent']=out['native_vs_BDF2_max_difference_percentage_points']<1e-6 and out['phase_vs_mixture_max_flux_difference_kg_s']<1e-6
out['actual_linear_targets_achieved']=all(v['all_below_relative_tolerance'] and v['cycle_cap_hits']==0 for v in stats.values())
out['short_mass_gate_pass']=out['short_mass_gate_pass'] and out['independent_fields_finite'] and out['native_inventory_consistent'] and out['actual_linear_targets_achieved'] and out['gauge_difference_vs_R10_max_mm']<2 and out['max_speed_m_s']<25
e.write(R/'wave_vof_tolerance_r13_review.json',out)"""
s=s.replace(needle,extra).replace('Audit reporting-only R12','Audit single-control R13')
ast.parse(s);p.write_text(s);print(str(p))
