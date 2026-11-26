from pathlib import Path
from datetime import datetime
import run_until_settled as e
R=Path(__file__).resolve().parent;now=e.stamp();cpu=e.read(R/'wave_fs_case_preparation_state.json',{});gpu=e.read(R/'wave_propagation_state.json',{})
d=e.read(R/'wave_numerical_review_current.json',{});d['updated_at']=now;d['current_wave']=gpu;d['current_CPU']=cpu;d['M10_paired_inputs']=e.read(R/'wave_fs_case_preparation_results.json',{});e.write(R/'wave_numerical_review_current.json',d)
for name in ['mesh_selection_plan.json','overnight_plan_20261029.json','wave24m_preparation_plan.json']:
 p=R/name
 if not p.exists():continue
 x=e.read(p,{});x['updated_at']=now;x['current_wave_recovery']=d;x['current_CPU_preparation']=cpu
 if 'execution' in x:
  x.setdefault('execution_history',[]).append(dict(archived_at=now,key='execution',value=x['execution']))
  x['execution']='CalmM09 supported. R10 native phase balance confirms original BDF2 diagnostic; R11 SO1ms40inner probe active. M10 short/80m meshes andpairedC01/W01 zero-stepinputs complete. Longerpropagation, wave-specificdt/FSchecks andfoilforces remain.'
 if 'near_hour' in x:x['near_hour']=[dict(stage='Current',action='CompleteR11and compare native/legacybudget,10/20/40inner gauges/cost; ifsupportedpreparefreshlongertrialwithzonalinventories/checkpoints,otherwisecontrolledsolverdiagnostic. Noautomaticgatechange. M10pairedinputs ready,notflowadmitted.')]
 if x.get('created_at'):
  try:x['elapsed_from_plan_creation_s']=(datetime.fromisoformat(now)-datetime.fromisoformat(x['created_at'])).total_seconds()
  except ValueError:pass
 e.write(p,x)
p=R/'RESUME_AT_HOME.txt';t=p.read_text(encoding='utf-8')
t=t.replace('CURRENT CPU\nrun_foil_wave_m10_setup_r1.py --run controller39192 ownsW/preparation.lock purpose', 'M10 INPUT PREPARATION FINISHED\nrun_foil_wave_m10_setup_r1.py --run controller39192 FINISHED both copies at01:21:19; CPUlockreleased. Previouslockpurpose')
t=t.replace('It preparesC01_W20L4_M10_FS020_env_setup_r1 thenW01_W20L4_M10_FS020_env_setup_r1,317277cells,zeroFlowSteps.', 'BothC01_W20L4_M10_FS020_env_setup_r1 andW01_W20L4_M10_FS020_env_setup_r1 are prepared,317277cells,zeroFlowSteps,sourceunchanged.')
t='LATEST VERIFIED UPDATE - '+now+'\nR11physicalprogress confirmed at0.501s with40inner andfiniteindependentreports; controller36136 active. M10pairedCPU39192finishedbothzero-stepinputs,sourceunchanged. Readcurrentstatebeforeacting.\n\n'+t
p.write_text(t,encoding='utf-8')
print({'GPU':gpu.get('progress'),'CPU':cpu.get('status'),'updated':now})
