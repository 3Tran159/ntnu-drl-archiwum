from pathlib import Path
import json
import run_until_settled as e
R=Path(__file__).resolve().parent;now=e.stamp()
decision=e.read(R/'selected_mesh_decision.json',{});dt=e.read(R/'selected_mesh_time_results.json',{})
wave=e.read(R/'wave_propagation_state.json',{});prep=e.read(R/'wave_foil_mesh_preparation_state.json',{})
for name in ['mesh_selection_plan.json','overnight_plan_20261029.json']:
 p=R/name;obj=e.read(p,{})
 obj['updated_at']=now;obj['latest_decision']='M09 is the supported calm template: SECOND_ORDER,1ms,10inner. Both finer common-window comparisons and selected-mesh halfdt test passed. Wave propagation and newdomain checks remain.'
 obj['selected_calm_mesh']={'mesh':'M09','cells':214908,'decision_file':'selected_mesh_decision.json','status':decision.get('status'),'settings':decision.get('configuration'),'dt_difference_pct':dt.get('half_vs_1ms_difference_pct'),'waves_admitted':False}
 obj['current_wave_pilot']={'case':wave.get('case'),'controller':'run_wave_flat_outlet_r3.py','controller_pid':28480,'state':'wave_propagation_state.json','change':'Fresh R5 initialization with outlet pressure/phase bound to existing flat wave; source unchanged; no failed-flow continuation','target_s':1.2,'gpu':True,'validation_pending':True}
 obj['wave_failure_diagnostic']={'case':'W20_H24_X4_CPUprop_dt1ms_r2','stop_s':.704,'review':'wave_pilot_spatial_diagnostic.json','max_speed_m_s':50.734771114938454,'phase':'air','location_m':[44.9,1.9375],'guard_unchanged':True}
 obj['foil_wave_mesh_preparation']={'controller':'run_wave_domain_import_r1.py','controller_pid':14348,'state':'wave_foil_mesh_preparation_state.json','directory':prep.get('directory'),'cells':246885,'original_M09_cells_preserved':214908,'added_remote_cells':31977,'flow_steps':0,'status':prep.get('status')}
 for c in obj.get('next_candidates',[]):
  if c.get('id')=='M09':c['flow_status']='Supported calm mesh/template after matched finer meshes and selected-mesh timestep check.'
 e.write(p,obj)
p=R/'wave24m_preparation_plan.json';obj=e.read(p,{})
obj.update(updated_at=now,status=wave.get('status'),controller='run_wave_flat_outlet_r3.py',controller_pid=28480,case=wave.get('directory'),workers=1,gpu=True)
obj['recovery']='CPU r2 guard stop at0.704s; air backflow at outlet localized by zero-step field audit. Fresh corrected-outlet GPU r3 uses flat pressure/phase per installed Siemens guidance, with FifthOrder inlet/initial wave and same guards.'
obj['target_s']=1.2;obj['next']='Review passage of the old failure time, full-cycle wave traces, mean level, conservation and final spatial fields. Further time-step/reflection checks before foil-wave forces.'
e.write(p,obj)
note=f"""LATEST VERIFIED HANDOVER — {now}
MESH AND CALM SETTINGS COMPLETE. selected_mesh_decision.json supports M09 (214908 cells), SECOND_ORDER,dt1ms,10inner. Controller38828 finished. Halfdt changes CD−0.00242319%,CL+0.00145333%; BDF2 mass residual max0.00004904%inlet; independent inner forces passed. Common-window mesh differences against M07/M08 both below1%. No formalGCI claim; wave checks remain.

CURRENT GPU: run_wave_flat_outlet_r3.py PID28480 owns rootqueue.lock and wave_flat_outlet_r3.lock. Case W20_H24_X4_GPUprop_flatOutlet_dt1ms_r3 onE, fresh R5 zero-time copy, corrected outlet pressure/phase use existing flat reference (HydrostaticPressureWave0/VolumeFractionHeavyFluidWave0), FifthOrder inlet/initial wave unchanged. SO1ms10inner,1200steps/1.2s,guard50m/s unchanged. Physical progress confirmed beyond0.5s; inspect actual lateststate/history. Not validated yet; do notduplicate.

PRESERVED FAILURE: CPU r2 stopped on stability guard at0.704s. Adopter15800 and audit28100 finished; neverrestart. Zero-step saved-field audit found50.7348m/s inair atx44.9,z1.9375,ux−50.0077,0.1mfromoutlet. Water/interface maxima18.48m/s. All>20m/scells wereair. wave_pilot_spatial_diagnostic.json/png and wave_pilot_stability_review.json record this. Pressure/phase mismatch at dampedoutlet is corrective hypothesis; installed Siemens VOFWavesGuidelines recommend flat-wavepressure/phase there (wave_outlet_local_documentation.json). No extension of failedfields.

CURRENT CPU PREPARATION: run_wave_domain_import_r1.py PID14348 owns E:/ntnu/quasi2d_waves_20261029/preparation.lock. C01_W20L4_M09_mesh_r1 extends acceptedM09 to x−35..45,z−22..8,y.01..03 without changing anyoriginal cell polygon/coordinate. 246885cells=214908original+31977remote strips. Offline exact topology/volume checks pass; STARCPU1 import/quality and independent topology audits run,zero flowsteps. Inputmesh.CGNS preserved; STARexports mesh_star_export.CGNS and mesh.sim. Inspect wave_foil_mesh_preparation_state.json beforeacting; actualbounds/boundaryareas/regionwave-zone settings and matchedC01 flow stillpending.

Do notrerunone-shot prepare/build scripts. Newlargefiles onE. LatestavailablediskE291GB,F183GB; preserve otherwork. No interference with HF_012_C003_regular_waves. Original24mdepth, FifthOrderwaves, maxM15 and original-before-bounded-extras unchanged.

PRESENTATION: plot_matched_fields.py completed common-endpoint M09/M08/M07 instantaneous pressure/streamlines at2.040s, allfinite,0%displayclipping. matched_fields_provenance.json keeps exactsources; priorconfigured/FOfigures preserved. Dashboardagent updating latestfieldsection, completedselecteddt, failedCPU versuscurrentGPUwavepilot, andseparatewave-meshpreparation. Read newest QA record. update_status.py refreshes case-matchedpartialgaugeplots every75s. A pilotplot is not validatedwaveforce evidence.

"""
p=R/'RESUME_AT_HOME.txt';p.write_text(note+p.read_text(encoding='utf-8-sig'),encoding='utf-8')
e.write(R/'night_stage_2347_record.json',{'at':now,'selected_mesh':'M09','GPU_controller':28480,'CPU_preparation_controller':14348,'wave_trial':wave,'foil_mesh_preparation':prep})
print('Current wave-stage handover and plans saved.')
