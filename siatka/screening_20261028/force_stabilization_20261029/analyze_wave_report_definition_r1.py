from pathlib import Path
import json,math
import run_until_settled as e
R=Path(__file__).resolve().parent
A=Path('E:/ntnu/quasi2d_waves_20261029/W20_H24_X4_R4_t0p750_report_definition_audit_r1')
old=e.read(A/'existing_report_definitions.json',[])
fresh=e.read(A/'independent_unsmoothed_reports.json',{})
saved=e.read(A/'saved_history_reference.json',{})
result=e.read(A/'controller_result.json',{})
if not result.get('source_unchanged') or result.get('audit',{}).get('steps_taken')!=0:raise RuntimeError('Audit not complete')
physical=[x for x in old if x.get('field_function',{}).get('getFunctionName') in ['Density','VolumeFractionwater','FaceFlux']]
if not all(x.get('smooth') is False and not x.get('error_log') and isinstance(x.get('value'),(int,float)) and math.isfinite(x['value']) for x in physical):raise RuntimeError('Invalid physical report definitions')
flux=[x for x in physical if x['class']=='star.flow.MassFlowReport']
fh=saved['history']
comparisons=dict(mass_kg=fresh['integrals']['Mass_kg']-float(fh['mass_kg']),water_volume_m3=fresh['integrals']['WaterVolume_m3']-float(fh['water_volume_m3']),net_mass_kg_s=fresh['net_outward_mass_kg_s']-float(fh['net_outward_mass_kg_s']))
out=dict(updated_at=e.stamp(),status='definitions_and_saved_values_verified_next_phase_flux_consistency',source_unchanged=True,steps_taken=0,physical_reports=len(physical),all_physical_reports_unsmoothed=True,all_boundary_mass_reports_idealization_off=all(x.get('idealization') is False for x in flux),all_physical_report_errors_empty=True,difference_vs_original_history=comparisons,native_mixture_flux_function='FaceFlux',VOF=dict(scheme='HRIC',face_density_reconstruction='FIRST_ORDER',temporal_order='SECOND_ORDER',actual_substeps=1),interpretation='Smoothing does not explain residual. Inspect volume-flux-based VOF phase-flux consistency before attributing global FaceFlux budget to discrete phase conservation. Do not change physics or relax gate without evidence.',note='Reflective bare FieldFunction.getValue errors are not report evaluation failures; actual report error logs empty. Analytic wave inventory remains unavailable at zero-step checkpoint load and is excluded.',mass_gate_pct=.01,R8_short_mass_gate_pass=False)
e.write(R/'wave_report_definition_review.json',out)
print(json.dumps(out))
