from pathlib import Path
import run_until_settled as e
R=Path(__file__).resolve().parent
now=e.stamp();review=e.read(R/'wave_pilot_r4_review.json',{});active=e.read(R/'wave_propagation_state.json',{});prep=e.read(R/'wave_foil_case_preparation_state.json',{})
assert review.get('completed',{}).get('status')=='target_reached'
decision=dict(updated_at=now,status='short_pilot_completed_targeted_inner_review_pending',pilot='W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4',source_unchanged=True,completed_time_s=1.2,
peak_mass_budget_pct_inlet=review['BDF2_budget_after_0p2_max_abs_pct_inlet'],
mass_spike_times_s=[.617,.618,.624,.625],mass_peak_time_s=.618,
next='Matched20inner diagnostic fromsame0.500 checkpointto0.750; do notweaken0.01%budgetreviewgate. Ifpasses, boundedlongerpropagationwithnewID, cache-safecontinuationandchoseninnercount; ifnot, inspectdt/inner/VOF consistency.',
current_controller=active,
cache_recovery='r5 innerprobe endedbeforefirststep because analyticwavecachewasNaN atload; physicalfieldreportsfinite,sourcesunchanged. r6 separatelyrecordsunavailablet0theory, requiresfiniteanalyticinventoryandgaugesafterfirstguardedstep, noflowreinitialization.',
interpretation='9.53mm equivalentwhole-domaininventorydifference vsundampedwave includesdampingzone mismatch; notcoreleveldrift orprovedmassleak. Corecyclemeanerrors-1.44to+1.18mm. IntegratedBDF2residual~0.018mm equivalentthroughfirstperiod. Addzonal(equalphase) inventory tolongertrial.',
calm_wave_inputs=prep.get('status'),input_results='wave_foil_case_preparation_results.json',
longer_prototype='run_wave_continuation_r5.py remainsUNLAUNCHED andgated; it lacksnewanalyticcachehandling andassumes10inner. Preparefreshcorrectedlongerattemptonlyafterprobe.',
wave_force_admitted=False)
e.write(R/'wave_boundary_recovery_decision.json',decision)
for n in ['mesh_selection_plan.json','overnight_plan_20261029.json','wave24m_preparation_plan.json']:
 p=R/n;d=e.read(p,{})
 d.update(updated_at=now,current_wave_recovery=decision,execution='CalmM09configuration/mesh/time gatescomplete. Nofoilr4 completed1.2s; GPU36724 runs matched20innerprobe r6 for4massbudgetspikes. PairedC01/W01zero-stepinputsfinished; longpropagation/time/FSchecksremain.')
 if n.startswith('overnight'):d['near_hour']=[dict(stage='Current',action='Complete targeted20innerprobe; reviewmatchedmass/gauges, thenboundedlongerpropagationandwave-specifictimechecks. PairedC01/W01readyasinputs, noflowadmission.')]
 e.write(p,d)
head=f"""LATEST VERIFIED HANDOVER — {now}
NO-FOIL R4 FINISHED1200steps/1.2s,sourceunchanged,controller15556ended. Environmentaloutlet+SLIPbed removedthepreviousguardfailureoverthisshorttrial. DoNOTcallfinalwavevalidation. wave_pilot_r4_review.json: maxhistoryspeed24.373m/s,interfaceCFLmax.19527; finalwatermax18.471,finalmax23.9395in4aircellsbyoutlet. GaugesRMS3.61–4.34mm; firstcyclefundamentalamplitude+.48..1.17%,phase−.37..−.47deg; sampledheight+1.26..2.02%. Startupincluded.

CONSERVATIONREVIEW:4spikes.617/.618/.624/.625s,maxBDF2budget.01451936%inlet; last1.0–1.2smax.00059541%. Keep.01%reviewgate; investigate. Whole-domain+9.53mmwatervolume-equivalentvsundampedanalyticwaveisNOTcoreleveldrift: dampingzone intentionallydiffers. Corecyclemeans−1.44..+1.18mm; integratednumericalresidualonly~.018mmequivalent. See professor_r4_pilot_interpretation.json. Longertrialneedzonalactual/analytic/flat inventories andequal-phasecyclecomparison.

ACTIVEGPU: run_wave_inner20_probe_r6.py PID36724 underrootqueue.lock andwave_inner20_probe_r6.lock, caseW20_H24_X4_GPUprop_environmentalOutlet_inner20probe_r6. RestartsR4checkpoint_t0.500.sim, ONLY10to20inner,SO1ms/BCunchanged,target0.750s250steps. r5probe39180endedbeforefirststepdueanalyticreferenceNaNoncheckpointload; preservedit. R6recordsload-cacheunavailabilityseparately,requiresfiniteanalytictheoryafterfirstguardedstep,andNEVERreinitializesphysicalfields. Verifyactualprogress/getters. Afterfinishrun analyze_wave_inner20_probe_r6.py tocompareexact0.502–.750windowwithR4. No duplicatecontrollers.

CPU27120r1failedcompilebeforeflow(Map.of>10pairs),preserved. CPU36284r2FINISHEDbothC01_W20L4_M09_env_setup_r2 andW01_W20L4_M09_env_setup_r2, prepared.sim,zeroFlowSteps,sourceunchanged. wave_foil_case_preparation_results.json records246885cells,actualboundaryareas/planes,gauges,SO1ms10inner,matchedENVIRONMENTALoutlet,SLIPbed,STATICtop,20mforcing/damping; W01FifthOrder,H.5,L20,H24,firstfrontfalse. INPUTPREPARATIONONLY; guardedstartup,wave-specificdt/FSresolutionandpropagationgatesremain.

UNLAUNCHEDprototypes: run_wave_continuation_r5.py (long1.2to4s,10inner,blockedbyR4budget andneedsnewcachehandling); run_wave_forcing_outlet_r4.py alternatevelocity/forcingBC. DoNOTlaunchblindly. IfR6passespreparefreshlongerattemptwithvalidatedinnercount,cache-safeguards,zonalinventory andcheckpoints. Ifnotpass, controlleddt/innerdiagnostics withoutguardrelaxation.

Dashboards currentdynamicstate; paired_input_preparation_ui_review.json passed1360/390and18-pageprint; wave_guard_completed_ui_review.json includes1920QA. M09calmselection,24mdepth,maxM15,original-before-extra scopeunchanged. PreserveotherHFwork andallsources. NewfilesonE.
"""
p=R/'RESUME_AT_HOME.txt';p.write_text(head+'\n'+p.read_text(encoding='utf-8'),encoding='utf-8')
print('Completed r4, targeted r6, paired preparedinputs and scientificlimits saved.')
