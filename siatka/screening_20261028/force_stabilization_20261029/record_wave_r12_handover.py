from pathlib import Path
from datetime import datetime
import shutil
import run_until_settled as e
R=Path(__file__).resolve().parent;now=e.stamp();A=Path('E:/ntnu/quasi2d_waves_20261029/W20_H24_X4_R4_t0p750_solver_controls_audit_r1')
settings=e.read(A/'model_solver_source_settings.json',{});rows=settings['solvers']
vof=next(x for x in rows if x['class'].endswith('.SegregatedVofSolver'));flow=next(x for x in rows if x['class'].endswith('.SegregatedFlowSolver'))
summary=dict(updated_at=now,source=str(A),zero_steps=True,source_unchanged=e.read(A/'controller_result.json',{}).get('source_unchanged'),VOF_AMG=vof['getAMGLinearSolver'],pressure_AMG=flow['getPressureSolver']['getAMGLinearSolver'],velocity_AMG=flow['getVelocitySolver']['getAMGLinearSolver'],VOF_URF=vof['getUrf']['getValue'],pressure_URF=flow['getPressureSolver']['getUrfQuantity']['getValue'],velocity_URF=flow['getVelocitySolver']['getUrfQuantity']['getValue'],scheme=flow['getScheme']['getSelected'],nonorthogonal_correctors=flow['getPressureSolver']['getNumNonOrthogonalCorrectors'],next='Read R12nativeperinner/AMGcycletrace before selectingone numericallysupportedcontrolchange.')
e.write(R/'wave_solver_controls_review.json',summary)
gpu=e.read(R/'wave_propagation_state.json',{});review=e.read(R/'wave_inner40_phase_probe_r11_review.json',{})
for name in ['wave_numerical_review_current.json','mesh_selection_plan.json','overnight_plan_20261029.json','wave24m_preparation_plan.json']:
 p=R/name
 if not p.exists():continue
 d=e.read(p,{});d['updated_at']=now;d['current_wave_snapshot']=gpu;d['R11_completed_review']=review;d['solver_controls']=summary;d['next_diagnostic']='R12 reporter-only SO1ms10innertrace .500to.650, LOWAMGverbosity only.605to.635; no numericalchange.'
 if 'execution' in d:d['execution']='CalmM09supported; M10 short/80m meshes andpairedinputsready. R11actual40innerfailedunchanged0.01%gate; nativebudgetequivalenceverified. Solvercontrolsauditcomplete; R12nativeperinner/AMGtrace active. Waveforces notadmitted.'
 e.write(p,d)
p=R/'RESUME_AT_HOME.txt';old=p.read_text(encoding='utf-8');archive=R/('handover_history_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.txt');shutil.copy2(p,archive)
core=old[old.index('CURRENT HANDOVER - '):]
start=core.index('CURRENT GPU\n');end=core.index('M10 WAVE GRID\n',start)
block="""CURRENT GPU - R12, REPORTING ONLY
run_wave_linear_trace_r12.py controller39344 owns rootqueue.lock andwave_linear_trace_r12.lock.
Case E:/ntnu/quasi2d_waves_20261029/W20_H24_X4_GPUprop_environmentalOutlet_linearTrace_dt1ms_r12.
R4checkpoint_t0.500 source, SO1ms10inner UNCHANGED,150steps to0.650. Nativephase reports explicitlymonitored at everyinneriteration (frequency1), exportCSVandverify~1500samples. VOF/pressureAMG LOWverbosity onlyforupcomingtimes0.605-0.635, otherwiseNONE. No numerical/physicschange. ReadsbaselineAMGtol.1,maxcycles30,epsilon0; phase/speed/time/resourceguards retained. Inspectactualprogress/process beforelaunchinganything, no duplicates.
Aftercompletionchecknative_inner_sampling_audit.json, native_water/air_per_inner.csv, amg_cycle_counts.csv andredactedstar.log. DetermineVOF/pressureactiveAMGstoppingcondition: relative.1tol,30cyclecap,orabsoluteepsilon0. Tightenonlydemonstratedlimitingcontrol inmatchednewattempt; do not changeURF/CFL/AMGsimultaneously. FIRSTread professor_wave_mass_plateau_review.json andwave_solver_controls_review.json. Clippingnotproved; highCFLnotseen; no automaticbudgetredefinition.

COMPLETED R11 / SOLVER AUDIT
R11controller36136 FINISHED250steps0.750,sourceunchanged. Actual logcountersprove40innerEVERYstep. Nativeabsphasepeak0.0111712387%,legacy0.0111449892%,native/BDF2agreement4.85e-9percentagepoints;short_mass_gate_passfalse. Gauge40minus10maxdifference0.346148mm. Analyze_wave_inner40_phase_probe_r11.py alreadyran; resultwave_inner40_phase_probe_r11_review.json. No40innerlongertrial.
CPUzero-step solveraudit41084 FINISHED,sourceunchanged. VOF/pressure/velocityAMG relative tolerance0.1,maxcycles30,epsilon0; VOFURF.9,pressureURF.2,velocityURF.5,SIMPLE,0nonorthogonalcorrectors. Native reportdiagnosticconfirmed; no needtochangeguard.
DocsdescribeVOFcorrections atinneriterations. Nonconvectiveterms onceperglobalstep doNOTimplyonce-per-step VOFsolve. CumulativeAMGcounts aloneareinsufficient. R12tracesactualsequencing.
R10reporter-only35120 andM10CPU39192/36760/33444 allFINISHED. Do notrestart.

"""
core=core[:start]+block+core[end:]
core=core.replace('LatestcompleteQA wave_completed_audit_ui_review.json:1360/390,18pageprint.','LatestcompleteQA m10_native_lineage_ui_review.json:1920/1360/390,19pageprint.')
core=core.replace('CurrentR11around2.9s','CompletedR11around2.9s')
p.write_text('LATEST VERIFIED STATE - '+now+'\nR12is theonlycurrentGPUcampaign; allR11andCPUaudits/inputpreparationsfinished. Earlierhandoverpreserved in'+archive.name+'. Inspectactualstate.\n\n'+core,encoding='utf-8')
print(dict(current_gpu=gpu.get('controller_pid'),R11_pass=review.get('short_mass_gate_pass'),VOF_tolerance=summary['VOF_AMG']['getConvergeTol']))
