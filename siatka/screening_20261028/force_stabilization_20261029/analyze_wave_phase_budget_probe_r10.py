"""Compare native phase balance and preserved mixture FaceFlux diagnostic without redefining gates."""
from pathlib import Path
import csv,json,math
import run_until_settled as e
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029')
A=W/'W20_H24_X4_GPUprop_environmentalOutlet_phaseBudget_dt1ms_r10';B=W/'W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4'
result=e.read(A/'controller_result.json',{})
if not result.get('source_unchanged') or result.get('completed',{}).get('status')!='target_reached' or result.get('completed',{}).get('steps')!=250:raise RuntimeError('Completed preserved probe prerequisite')
with (A/'native_phase_budget.csv').open() as f:raw=list(csv.DictReader(f))
rows=[r for r in raw if .502-1e-8<=float(r['time_s'])<=.750+1e-8]
cols=['native_water_error_kg_s','native_air_error_kg_s','native_sum_error_kg_s','native_sum_pct_inward_mass','native_abs_sum_pct_inward_mass','bdf2_plus_faceflux_pct_inward_mass','bdf2_plus_phaseflux_pct_inward_mass','faceflux_minus_phaseflux_kg_s']
stats={}
for col in cols:
 vals=[float(r[col]) for r in rows]
 if not vals or not all(math.isfinite(x) for x in vals):raise RuntimeError('Nonfinite native budget')
 stats[col]=dict(max_abs=max(map(abs,vals)),mean_abs=sum(map(abs,vals))/len(vals))
if any(r.get('native_water_error_log') or r.get('native_air_error_log') for r in rows):raise RuntimeError('Native report error log nonempty')
def gauges(p):
 with (p/'gauges.csv').open() as f:return {(round(float(r['time_s']),6),float(r['x_m'])):float(r['eta_actual_m']) for r in csv.DictReader(f) if .502-1e-8<=float(r['time_s'])<=.750+1e-8}
ga,gb=gauges(A),gauges(B);common=sorted(ga.keys()&gb.keys());diff=[1000*(ga[k]-gb[k]) for k in common]
if not common:raise RuntimeError('No matched gauges')
equivalence=max(abs(float(x['native_sum_pct_inward_mass'])-float(x['bdf2_plus_faceflux_pct_inward_mass'])) for x in rows)
phasefluxdiff=max(abs(float(x['faceflux_minus_phaseflux_kg_s'])) for x in rows)
nativepass=stats['native_abs_sum_pct_inward_mass']['max_abs']<.01
legacy=stats['bdf2_plus_faceflux_pct_inward_mass']['max_abs']<.01
out=dict(updated_at=e.stamp(),case=A.name,source_unchanged=True,settings='ExactR4 SO1ms10inner; additional reporting only',window_s=[.502,.75],samples=len(rows),metrics=stats,native_vs_inventory_max_difference_pct=equivalence,phase_vs_mixture_max_flux_difference_kg_s=phasefluxdiff,reporting_equivalence_supported=equivalence<1e-6 and phasefluxdiff<1e-6 and max(map(abs,diff))<.05,native_phase_mass_gate_pass=nativepass,legacy_faceflux_mass_gate_pass=legacy,original_threshold_pct=.01,max_gauge_replay_difference_mm=max(map(abs,diff)),gauge_replay_RMS_difference_mm=math.sqrt(sum(x*x for x in diff)/len(diff)),scope='Diagnostic comparison. Native phase errors are sums of phase transport residual timesdt perSiemensGUID-187276CC-89DA-4F69-B1AE-500038C45DE8. LegacyBDF2+FaceFlux retained. Nativephasefluxanddensityreconstructionreview requiredbeforeanygateinterpretation. Nofoilforceadmission.')
e.write(R/'wave_phase_budget_probe_r10_review.json',out)
print(json.dumps(out,indent=2))
