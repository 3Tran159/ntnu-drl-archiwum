from pathlib import Path
import run_until_settled as e
R=Path(__file__).resolve().parent
now=e.stamp();state=e.read(R/'wave_propagation_state.json',{})
assert state.get('case')=='W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4'
case=Path(state['directory']);binding=e.read(case/'boundary_treatment.json',{});progress=e.read(case/'progress.json',{})
assert binding.get('outlet_backflow_after')=='ENVIRONMENTAL' and binding.get('bed_shear')=='SLIP'
assert progress.get('time_s',0)>0
review=e.read(R/'wave_boundary_recovery_review.json',{})
review.update(updated_at=now,status='fresh_environmental_outlet_slip_bed_pilot_running',current_controller=state,actual_boundary_getters=binding,
correction_to_prior_guidance='Installed Siemens VOF Waves Guidelines explicitly rejects bottom symmetry for wave cases. Prior kinematic reasoning was incomplete; fresh r4 uses slip wall. Spans remain symmetry.',
previous_backflow_audit='r3 outlet STATIC/BOUNDARY_NORMAL/SPECIFIED; top STATIC/EXTRAPOLATED/SPECIFIED. Zero-step controller36776 finished with unchangedsource.',
free_surface_review='C01 extended mesh ~17.5 full cells/H in remote strips; variable polygon/ray resolution in core near20cells/H. Initial pilot candidate, not wavegridaccuracy acceptance. See professor_c01_free_surface_resolution.json and ray_resolution.json.',
next='Complete1.2s guarded pilot, inspect spatialmaxima, actual/referencegauges, equal-phase inventory, BDF2flux+accumulation, then longerpropagation anddt. Never claim1.2s validatesreflection.')
e.write(R/'wave_boundary_recovery_review.json',review)
for name in ['mesh_selection_plan.json','overnight_plan_20261029.json','wave24m_preparation_plan.json']:
 p=R/name;d=e.read(p,{})
 d.update(updated_at=now,current_wave_review=review,execution='Calm settings and M09 selection/time checks complete. GPU15556 runs fresh environmental-outlet + slip-bed no-foil r4. CPUaudit36776 andfoilmeshimport14348 completed. Inspect state/locks beforelaunch.')
 if name.startswith('overnight'):d['near_hour']=[dict(stage='Current',action='R4 no-foil boundary-correction pilot; review finitefields/gauges/inventory, then propagation/time checks and matched C01/W01 grid/BC preparation.')]
 e.write(p,d)
head=f"""LATEST VERIFIED HANDOVER — {now}
ACTIVE GPU: run_wave_environmental_outlet_r4.py PID15556, launcher25656, rootqueue.lock + wave_environmental_outlet_r4.lock. CaseW20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4, freshR5copy,SO1ms10inner,53200cells,target1.2s. Actualprogress {progress.get('time_s'):.3f}s, maxspeed{progress.get('max_speed_m_s'):.6f}m/s, interfaceCFL{progress.get('interface_CFL'):.6f}. Gettersconfirm ENVIRONMENTAL outletbackflow andSLIPwallbed. TopSTATIC,flatoutletpressure/phase and20mdamping retained. Twochanges, notsinglefactorproof. Guardsunchanged; nofailedfieldrestart. Inspectactualstatusbeforeacting; doNOTduplicate.

Zero-stepCPUaudit36776 FINISHED: r3outlet STATIC/BOUNDARY_NORMAL/SPECIFIED,topSTATIC/EXTRAPOLATED/SPECIFIED,sourceunchanged. Documentation explicitlywarnsagainstbottomsymmetry forwavecases; previousassumption superseded. r2airjetfailure0.704s andr3waterjetfailure0.850s preserved. R4velocity/forcingalternative prototype remainsPREPAREDONLY,notlaunched; neverrun concurrentlyoraccidentally.

Calm M09(214908cells) remainsSUPPORTED withmatchedmesh/timechecks. Foil-domain246885cellpreparation passedgeometry/single-span,flowsteps0; actualBC/forcing andFSaccuracy remainpending. Read professor_c01_free_surface_resolution.json and professor_c01_free_surface_ray_resolution.json; remoteFS~17.5cells/H,corevariable. ApproximateH/20guideline isnotitselfconvergenceproof. MatchC01grid/BC/slipbed tofutureW01; preserve24mdepth. Noformalwaveforceadmissionyet.

Afterr4, analyzegauges/phase/mean, perboundaryflux, equalphaseactual/analyticwaterinventory andspatialmaxima. 1.2s<coretraversal1.695s,so cannotvalidatereflections. Longerpropagation/newattemptwithadequatewalltimeanddtcheck followsifstable. Bothdashboardscurrentdynamicstate; latestUIagentQA mayfollow. Sources/attemptsretained; maxM15; otherHFworkuntouched.
"""
p=R/'RESUME_AT_HOME.txt';p.write_text(head+'\n'+p.read_text(encoding='utf-8'),encoding='utf-8')
print('Active r4, completed backflow audit, corrected bed guidance and next gates saved.')
