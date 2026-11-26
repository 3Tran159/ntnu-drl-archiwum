from pathlib import Path
from datetime import datetime
import json,shutil
import run_until_settled as e
R=Path(__file__).resolve().parent;B=R.parent;now=e.stamp();tag=datetime.now().strftime('%Y%m%d_%H%M%S')
case=Path('E:/ntnu/quasi2d_waves_20261029/W20_H24_X4_GPUprop_environmentalOutlet_pressureTol01_dt1ms_r14')
done=e.read(case/'controller_result.json',{});review=e.read(R/'wave_pressure_tolerance_r14_review.json',{})
assert done['completed']['status']=='target_reached' and done['source_unchanged']
assert (case/'final.sim').stat().st_size>0 and not (R/'queue.lock').exists()
pause=dict(status='paused_by_user',updated_at=now,reason='Transport to NTNU; user requested stopping this campaign.',automation_status='PAUSED',stop_marker=str(R/'STOP_ALL'),last_case=case.name,last_completed_local='2026-10-30T02:05:40.924948+01:00',last_field=str(case/'final.sim'),last_time_s=.750,own_controller_running=False,last_source_unchanged=True,separate_HF_session='Explicitly left running by user instruction at morning pause',next='Resume only on explicit user request. Review calibrated local phase imbalance fields; no further wave-force admission.',R14_native_mass_peak_pct=review['metrics']['native_abs_sum_pct_inward_mass']['max_abs'],mass_limit_pct=.01)
e.write(R/'campaign_pause_20261030.json',pause)
e.write(R/'queue_state.json',dict(status='paused_by_user',active=None,updated_at=now,purpose='User pause for transport; completed attempts preserved'))
old=(R/'RESUME_AT_HOME.txt').read_text(encoding='utf-8');(R/f'handover_history_{tag}.txt').write_text(old,encoding='utf-8')
header=f"""PAUSED BY USER - {now}
This campaign is stopped for transport to NTNU. Automation PAUSED and STOP_ALL present.
Do not start any solver or controller until explicit user resume. Keep all sources/attempts.
The separate HF_012_C003_regular_waves session is intentionally left running by the user's explicit morning reply.

Last own GPU controller R14 finished successfully at 02:05:40 local, 250steps to0.750s, source unchanged.
Final saved file: {case/'final.sim'}
No subsequent own CFD runs were launched. Agent usage-limit errors were reported around02:03; do not imply calculation continued all night.
Morning postprocessing confirms R14 pressure AMG target0.01 achieved (4-6cycles), but native phase mass peak0.014247575876% still exceeds0.01%.
R14 map calibration passed at0.612/0.617/0.618/0.625: cell sums exactly equal native phase report/dt. Spatial interpretation remains pending.
Calm M09 remains supported. M10 coarse/fine paired wave inputs are prepared; no accepted foil-wave force comparison completed.
Read campaign_pause_20261030.json and OVERNIGHT_SUMMARY_20261030.txt for the pause record.
Prior handover below is HISTORICAL; its R14-active language is superseded by this pause.

"""
(R/'RESUME_AT_HOME.txt').write_text(header+old,encoding='utf-8')
for name in ['mesh_selection_plan.json','overnight_plan_20261029.json','wave24m_preparation_plan.json','wave_numerical_review_current.json']:
 d=e.read(R/name,{})
 e.write(R/f'{Path(name).stem}_history_{tag}.json',d)
 d['updated_at']=now;d['campaign_status']='paused_by_user';d['pause']=pause
 d['latest_execution']='Paused by user. R14 completed02:05local; massgate still failed. No accepted foil-wave forces. Separate HF session intentionally left running.'
 d['next_diagnostic']=pause['next'];d['current_wave']=e.read(R/'wave_propagation_state.json',{});d['current_wave_snapshot']=d['current_wave']
 if name=='wave_numerical_review_current.json':d['status']='paused_by_user_R14_completed_mass_criterion_not_met';d['R14']=review
 if name=='overnight_plan_20261029.json':d['execution']=d['latest_execution'];d['near_hour']=[dict(stage='Paused',action=pause['next'])]
 e.write(R/name,d)
summary="""OVERNIGHT CFD SUMMARY - 30 OCTOBER 2026
Campaign paused by the user for transport. Automation paused, STOP_ALL set. Separate HF_012_C003_regular_waves intentionally left running.

SUPPORTED CALM RESULT
M09:214908 cells, second-order time integration, dt1ms,10inner.
Matched1.840-2.040s comparisons:
M09/M07: CD+0.466698%, CL-0.164252%.
M09/M08: CD-0.025574%, CL+0.016736%.
Both coefficients satisfy1% against both finer comparable meshes.
M09 half-dt sensitivity: CD-0.002423%, CL+0.001453%.
Pressure/viscous drag remain separately reported; this is practical convergence support, not formal GCI.

PREPARED WAVE INPUTS
Depth24m retained; FifthOrderVofWave.
M09 long80m domain:246885cells.
M10 refined free-surface:282379cells shortdomain,317277cells longdomain.
Foil/prisms preserved; calm and H0.5m/L20m paired inputs saved with matched BCs.
Prepared inputs are not validated wave-force results.

WAVE DIAGNOSTICS
Environmental pressure outlet plus slip bed removed the prior short-pilot instability. Basepilot reached1.2s.
The0.01% inlet-normalized mass criterion remains unmet.
R11:40inner, native absolute phase peak0.011171%.
R12:reporting-only trace proved VOF updates everyinner; error is not a reporting mismatch.
R13:tighter VOF linear tolerance achieved, peak0.014625%; no remedy.
R14:tighter pressure linear tolerance achieved, peak0.014248%; no remedy.
Small gauge differences do not establish conservation. R14 calibrated local phase imbalance fields are saved for localization.
No accepted original C01/W01/W02 foil-force comparisons or extra-wave campaign completed.

TIMELINE AND LIMITATION
Last own GPU test R14 ended02:05:40 local,0.750s,source unchanged,final.sim saved.
Agent usage-limit errors occurred around02:03. No later own CFD launches are recorded; it would be incorrect to describe this as calculation continuing until morning.
Morning work only verified/summarized saved output and paused the campaign.

PRESENTATION
English operational and professor dashboards were developed with mesh/control comparisons, experiment history, pressure/viscous drag, cost data and saved-state figures.
Night readability checks covered1920/1360/390px and19-page print. R12/R13 diagnostic figure assets are saved; final optional figure integration should be verified after resume.
Next work after explicit resume: localize the calibrated phase mass error, resolve it with a supported controlled test, then propagation/reflection/FS-grid/time checks and original waves.
"""
(R/'OVERNIGHT_SUMMARY_20261030.txt').write_text(summary,encoding='utf-8')
p=R/'configured_mesh_panel.py';s=p.read_text(encoding='utf-8')
shutil.copy2(p,R/f'configured_mesh_panel_before_pause_{tag}.py')
old="'wave_linear_trace_r12_review.json','wave_vof_tolerance_r13_review.json')];mass_failed="
assert old in s;s=s.replace(old,"'wave_linear_trace_r12_review.json','wave_vof_tolerance_r13_review.json','wave_pressure_tolerance_r14_review.json')];mass_failed=",1)
needle=" if mass_failed:stage='Completed — mass-budget criterion not met'"
assert needle in s;s=s.replace(needle,needle+"\n if (R/'STOP_ALL').exists():stage='Paused by user; last pilot completed'",1)
needle=" if mass_failed:next_gate='Audit report definitions and the saved balance before further propagation.'"
assert needle in s;s=s.replace(needle,needle+"\n if (R/'STOP_ALL').exists():next_gate='Paused for transport. Resume only after an explicit user request.'",1)
p.write_text(s,encoding='utf-8')
print(json.dumps(pause,indent=2))
