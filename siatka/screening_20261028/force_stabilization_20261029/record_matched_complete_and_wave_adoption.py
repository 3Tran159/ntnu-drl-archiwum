from pathlib import Path
import json,datetime
import run_until_settled as e
R=Path(__file__).resolve().parent
matched=e.read(R/'matched_endpoint_results.json',{})
waves=e.read(R/'wave_propagation_state.json',{})
dt=e.read(R/'selected_mesh_time_state.json',{})
now=e.stamp()
for n in ['mesh_selection_plan.json','overnight_plan_20261029.json']:
 p=R/n;obj=e.read(p,{})
 obj['updated_at']=now
 obj['latest_decision']='M09 meets the 1% CD and CL mesh criterion against M08 and M07 at the common 1.840–2.040 s window. The selected-mesh half-time-step screen is running; final calm-template decision is pending.'
 obj['matched_endpoint']={'status':'completed_pending_selection_review','state':'matched_endpoint_state.json','results':'matched_endpoint_results.json','pairs':matched.get('pairs',[]),'controller_pid':5240,'controller_finished':True}
 obj['selected_mesh_time']={'status':dt.get('status'),'controller_pid':38828,'controller':'run_selected_mesh_time_screen.py','state':'selected_mesh_time_state.json','active':dt.get('active'),'scope':'One SO0.5ms10inner branch versus reused SO1ms10inner branch from the identical t1.640 checkpoint; compare1.840–2.040. Calm-only decision.'}
 obj['CPU_wave_pilot']={'status':waves.get('status'),'controller_pid':15800,'controller':'adopt_wave24m_pilot_r2.py','launcher_pid':36304,'case':waves.get('case'),'state':'wave_propagation_state.json','recovery':'Original1852 failed on status-file replace; solver kept advancing and was adopted without restart. Check actual processes and locks.'}
 for c in obj.get('next_candidates',[]):
  if c.get('id')=='M09':c['flow_status']='Common-window agreement passed against both M08 and M07; selected-mesh dt screen running.'
 e.write(p,obj)
p=R/'wave24m_preparation_plan.json';obj=e.read(p,{})
obj.update(updated_at=now,status=waves.get('status'),controller='adopt_wave24m_pilot_r2.py',controller_pid=15800,launcher_pid=36304)
obj['status_io_recovery']='PID1852 exited after a transient Windows access error while publishing status. Existing solver36304 continued; adopter15800 restores process/resource/time/progress supervision and owns preparation.lock. No duplicate solve.'
obj['next']='Inspect partial completion and final/checkpoint source. If wall-budget exit, preserve partial-cycle evidence and prepare a controlled new-ID continuation, preferably sequential GPU after the selected-mesh test when resources permit. No full propagation/reflection or force claim yet.'
e.write(p,obj)
note=f"""LATEST VERIFIED HANDOVER — {now}
1. The common-endpoint mesh comparison is complete. Controller5240 has finished; do not restart it. All three meshes use SO1ms10inner and window1.840–2.040s. M09 vs M07: CD+0.466698%, CL−0.164252%; vs M08: CD−0.025574%, CL+0.016736%. Both finer confirmations pass the user’s1% coefficient criterion. The earlier own-window M09/M07 CD+1.014846% failure remains preserved. Pressure Fx vs M07 still differs+1.555173%; report components separately.

2. Controller38828 is now running M09_SO_dt05ms_common_t2040_r1 under selected_mesh_time_20261029/controller.lock and root queue.lock. One SO0.5ms10inner branch from the same M09t1.640 checkpoint is compared with the already-completed1ms branch. No duplicate1ms baseline. Inspect selected_mesh_time_state/plan/results.json and selected_mesh_decision.json. Only status supported_calm_mesh_template permits describing M09 as selected for calm work. No automatic wave admission.

3. CPU wave pilot r2 never stopped calculating. Original controller1852 exited on a Windows status-file sharing error; existing launcher36304 kept advancing. Adopter15800 now owns E:/ntnu/quasi2d_waves_20261029/preparation.lock and supervises that same solver. Inspect wave_propagation_state.json and actual processes. Last plotted trace reaches0.420s, history0.424s, independent fields finite, alpha[0,1], maximum interfaceCFL0.11153. Original star.log stopped with the old controller pipe; independent CSV/progress files remain current. Macro wall budget may yield a partial final state. Preserve it, then make a new-ID continuation; never call partial-cycle evidence validated.

4. Future run_until_settled.write imports now use per-process temporary files and bounded retries for transient Windows sharing errors. Existing active processes keep their already-imported implementation, so inspect orphan solvers before any recovery. CPU adopter has a separate resilient publisher.

5. Both dashboards show common-window progress/results, candidate timestep status and partial wave traces. overnight_ui_progress_review.json passed1360/390 and17-page print before final pair rows. Read the newest agent/QA report for populated rows and1920px checks. Main dashboard writer temporary-file collision is fixed. Configured M07/M08/M09 accepted fields are rendered with separate provenance.

6. Continue in order: selected calm mesh/time screen, then matched24m-depth C01 and FifthOrder W01/W02 with new horizontal-domain/free-surface checks, followed by the authorized bounded extras. Maximum M15. Preserve source simulations and all attempts. No optional questions, no duplicate GPU/CPU controllers, no interference with HF_012_C003_regular_waves.

"""
p=R/'RESUME_AT_HOME.txt';e.write(R/'night_stage_2315_record.json',{'at':now,'matched_pairs':matched.get('pairs',[]),'dt_state':dt,'wave_state':waves,'ui_review':'overnight_ui_progress_review.json'})
p.write_text(note+p.read_text(encoding='utf-8-sig'),encoding='utf-8')
print(json.dumps({'handover_updated':True,'matched_comparison_complete':True,'active_GPU':38828,'active_CPU_adopter':15800}))
