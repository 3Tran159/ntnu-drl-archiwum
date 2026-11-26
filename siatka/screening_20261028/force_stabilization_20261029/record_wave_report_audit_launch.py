from pathlib import Path
import run_until_settled as e
R=Path(__file__).resolve().parent
state=e.read(R/'wave_report_definition_audit_state.json',{})
d=e.read(R/'wave_numerical_review_current.json',{});d['report_audit']=state;d['current_gpu']=None;d['campaign_reservation']='CPU1 zero-step report audit usesrootqueue.lock;M10retainsCPUpreparation.lock';e.write(R/'wave_numerical_review_current.json',d)
for name in ['mesh_selection_plan.json','overnight_plan_20261029.json','wave24m_preparation_plan.json']:
 p=R/name
 if p.exists():
  v=e.read(p,{});v['updated_at']=e.stamp();v['current_wave_recovery']=d;e.write(p,v)
p=R/'RESUME_AT_HOME.txt'
head='LATEST AUDIT LAUNCH - '+e.stamp()+'\nCPU1 run_wave_report_definition_audit_r1.py controller33140 is active under rootqueue.lock and own auditlock. It inspects disposable R4t0.750 copy with ZERO steps. M10CPU2 keeps preparation.lock and continues. No GPU solve currently; do not race audit reservation. Read wave_report_definition_audit_state.json and output E:/ntnu/quasi2d_waves_20261029/W20_H24_X4_R4_t0p750_report_definition_audit_r1. Analyze report defaults/nativeflux/source settings before changing mass diagnostic or selecting next numerical probe. Primary theory review professor_vof_temporal_budget_review.json is saved. R7/R9 longer prototypes remain blocked.\n\n'
p.write_text(head+p.read_text(encoding='utf-8-sig'),encoding='utf-8')
print(state.get('status'))
