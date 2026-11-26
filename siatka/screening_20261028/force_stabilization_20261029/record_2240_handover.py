import json,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029')
now=datetime.datetime.now().astimezone().isoformat()
wave={'updated_at':now,'status':'CPU_exact_mesh_import_initialization_running','controller':'run_wave24m_preparation_r5.py','controller_pid':32996,'state_file':'wave_preparation_state.json','cpu_lock':str(W/'preparation.lock'),'case':str(W/'W20_H24_X4_Q2D_r5'),'workers':2,'gpu':False,'cells':53200,'scope':'Exact Cartesian no-foil build and zero-step gauge audit. No transient results yet.','mesh':{'dx_m':.2,'dz_free_surface_m':.025,'span_m':.02,'depth_m':24,'volume_m3':48},'preserved_attempts':{'r1':'time order setter compile error','r2':'native thin-slab geometry/boundary failure','r3':'area report class compile error','r4':'thin-slab failure retained after fresh BC mapping; incomplete gauge height29.018m'},'next':'After R5 build: audit_nofoil_cgns.py <case>; verify geometry_pass, initial gauge area/calm/H, then run_wave24m_propagation_r1.py. Pilot is CPU2/noGPU1000stepsSO1ms10inner; check lock first. Pilot macro/controller prepared but NOT launched.'}
for name in ['mesh_selection_plan.json','overnight_plan_20261029.json']:
 p=R/name;d=json.loads(p.read_text());d['updated_at']=now;d['wave_preparation']=wave
 if name.startswith('mesh_selection'):
  d['latest_decision']='M09 SO1ms10inner settled at1.640s; M08 thenM07 matched-setting continuations under existingPID15952. No finalmeshselected. M09 diagnostics passed; nofoil wave preparation being repaired/audited independently.'
  for c in d.get('next_candidates',[]):
   if c['id']=='M09':c['flow_status']='SO1ms10inner settled at1.640s; waiting matchedM08/M07 and finaldiagnostics.'
 else:
  d['execution']='Existing GPU controllerPID15952: M09 completed; M08 running, M07 next. CPU2 exact nofoilwave preparationPID32996 separate; no GPU duplication.'
 p.write_text(json.dumps(d,indent=2))
(R/'wave24m_preparation_plan.json').write_text(json.dumps(wave,indent=2))
block=f"""CURRENT HEARTBEAT HANDOVER — {now}
M09_SO1ms_inner10_r1 ACCEPTED FORCE SETTLING at1.640s: meanCD0.007505918315,CL0.313128896794; changes-0.494611%CD,+0.240116%CL; pressureFx8.185500N,viscousFx20.754319N. Finite independentfields, sourcepreserved, medianstep1.07753s. configured_mesh_diagnostic_audit.json: final200steps innerFxmaxchange0.001374%,Fz0.000644%, BDF2massbudgetmax0.00009899%inlet. wallY+MAX253.60 is TEoutlier; do not confusewithp95, inspectdistributionbeforeselection.
GPUcontroller15952/rootqueue.lock remainsactive; M08_SO1ms_inner10_r1 running,lastobserved1.830s, M07 follows. Do notrestartcontroller. Read currentstate,results,lock,processes. NewSOcohort separatefromFO. M09ownacceptedwindow1.44–1.64 differsfromupcomingM08/M07; obtainmatchedendpointfollowups ifdrift/near1%requires. No finalmeshselectionyet.
CPUwaveprep: R1/R3compilefailurespreserved; R2/R4native thin-slab meshes FAILED geometry/BC audit (no usefulinlet, incompletegaugeheight29.018m andcalmoffset-0.489m). No transientsteps wereeveradmitted. Fresh boundaryassignmentalone didnotfixtrimming. Reportswave_preparation_r2_review.json/r4_review.json.
NEW run_wave24m_preparation_r5.py PID32996 activeCPU2/noGPU. W/W20_H24_X4_Q2D_r5 imports exactCartesianCGNS53200cells,dx0.2,dz0.025nearFS,gradedoutside,20mmonecellspan,24mdepth,volume48m3. Native remeshingdisabled. Sourcebaselinecopyhashverified. Inspectwave_preparation_state.json andW/preparation.lock. Preserveallattempts.
AfterR5build, run audit_nofoil_cgns.py with caseabsolute path using bundled SiemensPython/deps311. Require geometry_pass, all6correctboundaryplanes, single span, volume48 andinitialplaneheight30m,calmreference~0,waveH~0.5. Onlythen run_wave24m_propagation_r1.py (PREPARED,NOTLAUNCHED) whichenforcesgates andcreates W20_H24_X4_CPUprop_dt1ms_r1 fromnewcopy. PilotCPU2/noGPU1000stepsSO1ms10inner,target1s,independentgauges/mass/alpha/CFL/checkpoints. Use sameCPUpreparation.lock; no GPUlockchanges. Pilot is too shortforfinalreflectionvalidation; analyzefirst,thenmatchedtime/domainchecks.
WavePropagationCheck.java andrun_wave24m_propagation_r1.py are preparedbutnotruntimecompiledyet. Ifcompilefails,preserveattemptandcorrectintonewID. Do notrerun any prepare_wave24m_rN.py orbuild_exact_wave24m_r5.py—theycreateuniquefolders.
DashboardagentaddedwaveprepstatusfromliveJSONtobothmainandprofessorviews,includingCPU/noGPU,stage,case,nextgateandclearpreparationonlylabel. QA1360/390and13pageprintpassed; reportwave_preparation_ui_review.json. No changes toGPUqueue. NeedfuturefieldrenderingforacceptedSOstateswithcohort/provenance.
Latestscopeunchanged: configuration->mesh->C01/W01/W02FifthOrder at24m->boundedextras;maxM15. Fullolderhandoverbelowretained.
 
"""
p=R/'RESUME_AT_HOME.txt';p.write_text(block+p.read_text(encoding='utf-8'),encoding='utf-8')
(R/'heartbeat_20261029_2240_audit.json').write_text(json.dumps({'updated_at':now,'M09_force_settled':True,'configured_controller_pid':15952,'CPU_preparation':wave,'dashboard_qa':'wave_preparation_ui_review.json'},indent=2))
print(json.dumps({'handover_updated':True,'plans_updated':True,'wave_attempt':'r5','M09_settled':True}))
