from pathlib import Path
import json
import run_until_settled as e
R=Path(__file__).resolve().parent
now=e.stamp()
entry=dict(updated_at=now,status='short_diagnostics_completed_mass_gate_failed_report_audit_next',R4=dict(case='W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4',time_s=1.2,inner=10,dt_s=.001,max_budget_pct=.01451935956931171),R6=dict(case='W20_H24_X4_GPUprop_environmentalOutlet_inner20probe_r6',time_s=.75,inner=20,dt_s=.001,max_budget_pct=.0113353042957,short_mass_gate_pass=False),R8=e.read(R/'wave_halfdt_probe_r8_review.json',{}),current_gpu=None,pending='Zero-step saved-state report-definition audit before further numerical changes; documented VOF BDF2 accumulation is retained and wave forcing has no phase source. Do not alter mass accounting or relax0.01%gate without evidence.',blocked_prototypes=['run_wave_long_inner20_r7.py','run_wave_long_halfdt_r9.py'],CPU_mesh=e.read(R/'wave_fs_refinement_state.json',{}),paired_inputs='C01_W20L4_M09_env_setup_r2 and W01_W20L4_M09_env_setup_r2:246885cells,zero steps,source preserved; not flow admission',wave_force_admitted=False)
e.write(R/'wave_numerical_review_current.json',entry)
for name in ['mesh_selection_plan.json','overnight_plan_20261029.json','wave24m_preparation_plan.json']:
 p=R/name
 if not p.exists():continue
 d=e.read(p,{})
 hist=d.setdefault('execution_history',[])
 for key in ['wave_preparation','selected_mesh_time','CPU_wave_pilot','current_wave_pilot','current_wave_recovery']:
  if key in d:hist.append(dict(archived_at=now,key=key,value=d.pop(key)))
 d['updated_at']=now;d['current_wave_recovery']=entry
 d['selected_mesh_time']=dict(status='completed_passed',controller_finished=True,decision='selected_mesh_decision.json')
 d['current_CPU_preparation']=entry['CPU_mesh'];d['maximum_mesh_number']=15
 d['presentation_views']=dict(operational='../dashboard.html',research_review='../professor_dashboard.html',latest_QA='wave_numerics_fs_ui_review.json',print_pages=18)
 e.write(p,d)
p=R/'RESUME_AT_HOME.txt'
old=p.read_text(encoding='utf-8-sig')
head=f"""LATEST VERIFIED HANDOVER - {now}
R6 and R8 are FINISHED. Do not restart controllers36724/29860. R6 SO1ms20inner: max BDF2 budget0.0113353%inlet, still fails0.01%. R8 SO0.5ms10inner: all497 half-step budget samples in0.502-0.750s, max0.0166372%,6 exceedances, source unchanged,finite fields,maxspeed21.569m/s,maxgaugechange0.263315mm. Small gauge changes are not a mass-gate pass. R7long20 and R9longhalfdt remain UNLAUNCHED/BLOCKED. GPU currently free; inspect actual locks/processes before any new launch.

NEXT: read wave_numerical_review_current.json and scientific agent audit. Installed Siemens temporal-subcycling theory explicitly retains BDF2 VOF accumulation even with substeps. Wave forcing uses momentum sources only, no phase sources. Verify actual MassFlowReport smoothing/idealization/representation and inventory report defaults on disposable saved-state copy before further numerical changes. Preserve old reports and histories. Never silently redefine budget or relax0.01%gate.

CPU M10_FS020_r1 build active controller33444,2CPU/noGPU, W/preparation.lock purpose 'Wave free-surface M10 variant CPU2 build; no GPU'. State wave_fs_refinement_state.json. Only nominal FS control28.5714->20.000mm; foil/prisms/outer settings retained. Actual cells/edges still need audit; short domain then coherent80m extension, STARimport and own pairedcalm/W01. Previous M10 LE/TE idea remains UNBUILT, actualM10 now prioritizes waveFS. Do not rerun one-shot builders.

Paired base M09 C01/W01 inputs remain prepared at246885cells,zero steps,matchedENVIRONMENTALoutlet/SLIPbed/STATICtop/20mforcing+damping. No force admission. M09 calm selection and SO1ms10inner remain supported; wave configuration still under review.

Both dashboards dynamic: R6 and R8 numerical probes plus M10 preparation; latest wave_numerics_fs_ui_review.json passed1360/390 and18-pageprint. Preserve24mdepth,z-22..8,waterline2,FifthOrder waves,maxM15,source/attempts and separateHF work. New large filesE.

"""
p.write_text(head+old,encoding='utf-8')
print(json.dumps({'updated_at':now,'R8_mass_gate':False,'M10_status':entry['CPU_mesh'].get('status'),'plans_updated':True}))
