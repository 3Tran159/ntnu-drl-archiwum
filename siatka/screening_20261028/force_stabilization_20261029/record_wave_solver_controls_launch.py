from pathlib import Path
from datetime import datetime
import run_until_settled as e
R=Path(__file__).resolve().parent;now=e.stamp();cpu=e.read(R/'wave_solver_controls_audit_state.json',{});gpu=e.read(R/'wave_propagation_state.json',{})
for name in ['wave_numerical_review_current.json','mesh_selection_plan.json','overnight_plan_20261029.json','wave24m_preparation_plan.json']:
 p=R/name
 if not p.exists():continue
 d=e.read(p,{});d['updated_at']=now;d['current_solver_controls_audit']=cpu;d['current_wave_snapshot']=gpu
 d['presentation_views']=dict(operational='../dashboard.html',research_review='../professor_dashboard.html',latest_QA='m10_native_lineage_ui_review.json',print_pages=19,viewports=[1920,1360,390])
 if d.get('created_at'):
  try:d['elapsed_from_plan_creation_s']=(datetime.fromisoformat(now)-datetime.fromisoformat(d['created_at'])).total_seconds()
  except ValueError:pass
 e.write(p,d)
p=R/'RESUME_AT_HOME.txt'
note='LATEST AUDIT / PRESENTATION UPDATE - '+now+'\nCPU1 run_wave_solver_controls_audit_r1.py --run controller41084 ownsW/preparation.lock; rootGPUlock remainsR11controller36136. Newdisposablecase W20_H24_X4_R4_t0p750_solver_controls_audit_r1 readsactualVOF/pressure/velocity AMG tolerances,maxcycles,epsilon,cyclecounts,URFs,nonorthogonalcorrectors,scheme frompreservedR4t.750. ZEROsteps,nochanges. State wave_solver_controls_audit_state.json. Read model_solver_source_settings.json aftercompletion; no duplicateaudits. Agentprofessor_evidence primaryreview professor_wave_mass_plateau_review.json pending; SIMPLEC/PISOC notmultiphasecuresperdocs. Moreinneraloneplateaus; nextcontrolledchange mustfollowactualsolvergettersandprimaryguidance.\nBothdashboardsfinalQA passed1920/1360/390; professorprint19 intentionalpages. m10_native_lineage_ui_review.json anddashboard_qa.json verify noJSerrors/overflow/clipping; measuredM10geometry,317277cellextensionandpairedinputsready,R10equivalenceandactiveR11shown. No scientificclaimchanged.\n\n'
p.write_text(note+p.read_text(encoding='utf-8'),encoding='utf-8')
print(dict(cpu=cpu.get('status'),gpu_progress=gpu.get('progress'),QA='m10_native_lineage_ui_review.json'))
