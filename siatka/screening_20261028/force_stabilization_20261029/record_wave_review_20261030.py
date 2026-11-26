from pathlib import Path
import json
import run_until_settled as e
R=Path(__file__).resolve().parent
now=e.stamp()
review=dict(updated_at=now,status='boundary_treatment_under_review',wave_admitted=False,
calm_mesh='M09,214908cells,SO1ms10inner,supported',
attempts=[
 dict(case='W20_H24_X4_CPUprop_dt1ms_r2',stop_time_s=.704,reason='stability_guard',max_speed_m_s=50.734771,phase='air',x_m=44.9,z_m=1.9375,source_unchanged=True),
 dict(case='W20_H24_X4_GPUprop_flatOutlet_dt1ms_r3',stop_time_s=.850,reason='stability_guard',max_speed_m_s=50.09167377,phase='water',x_m=44.9,z_m=1.9125,ux_m_s=-50.088761,pressure_Pa=59676.635,source_unchanged=True)],
interpretation='Flat outlet pressure/phase did not remove localized downstream backflow. Core gauges and small mass residual alone do not establish stability. Exact backflow pressure/scalar settings being audited without time advancement.',
prepared_alternative=dict(controller='run_wave_forcing_outlet_r4.py',launched=False,change='Velocity components and phase from same FifthOrder wave at both ends; 20m forcing each, FORCING only; protected core -15..25; same mesh/SO1ms10inner/50m/s guard',scope='Fresh bounded1.2s pilot, not final reflection or force validation'),
foil_mesh=dict(case='C01_W20L4_M09_mesh_r1',cells=246885,status='geometry_and_single_span_pass',flow_steps=0,pending=['Actual boundary/profile and wave-zone setup','Wave-resolution review','Matched C01 and W01 short trials after boundary decision']),
completed_controllers=[38828,5240,28480,14348,15800,1852],
active_diagnostic=dict(controller='run_wave_backflow_audit_r1.py',pid=36776,workers=1,gpu=False,steps=0))
e.write(R/'wave_boundary_recovery_review.json',review)
for name in ['mesh_selection_plan.json','overnight_plan_20261029.json','wave24m_preparation_plan.json']:
 p=R/name;d=e.read(p,{})
 d.update(updated_at=now,current_wave_review=review,execution='Calm settings and M09 mesh/time gates completed. Wave r2/r3 stopped on outlet stability guard; zero-step backflow audit36776 precedes fresh boundary-treatment pilot. Foil extended mesh246885 cells audited, no flow. Inspect actual state/locks.')
 if name.startswith('overnight'):
  d['near_hour']=[dict(stage='Current',action='Resolve no-foil downstream boundary failure; audit extended M09 wave resolution and prepare matched C01/W01 boundary configuration.')]
  d['overnight_priority'][0]='Completed: calm SECOND_ORDER1ms10inner configuration and selectedM09 halfdt check.'
  d['overnight_priority'][1]='Completed: M09 common-window agreement with two component-wise finer cases; supported_calm_mesh_template. Wave gates remain separate.'
 e.write(p,d)
head=f"""LATEST VERIFIED HANDOVER — {now}
Calm configuration and M09 selection/time gate PASSED. selected_mesh_decision.json=supported_calm_mesh_template, waves_admitted=false. Completed controllers38828/5240 must never restart.

R3 GPU controller28480 FINISHED at0.850s on unchanged50m/s stability guard. Flat outlet pressure/phase correction did NOT cure failure: water jet ux=-50.088761m/s atx44.9,z1.9125,0.1mfromoutlet,pressure59676.635Pa. CPUr2 earlierfailed at0.704s inair. Bothsources/attemptspreserved; do notcontinuefailedfields. See wave_boundary_recovery_review.json and wave_pilot_r3_spatial_diagnostic.json.

CPU36776 currently runs ZERO-STEP audit of r3 backflow pressure/direction/scalar settings, caseW20_H24_X4_GPUprop_r3_backflow_audit_r1, preparation.lock. Inspect current result, neverduplicate. R4 velocity/forcing-outlet pilot is PREPARED ONLY (run_wave_forcing_outlet_r4.py); notlaunched. Ifactualr3STATIC pressure, consider focusedENVIRONMENTAL comparison before broadboundarychange. Do notuseBLOCKED tohidefailure. Ifalternativechosen: sameFifthOrderwave, bothendvelocityCOMPONENTS/phase,20mforcingeach,regionFORCING,coreunforced,dampingoff,unchangednumericalguards.

Foil domain import controller14348 FINISHED. C01_W20L4_M09_mesh_r1 has246885cells,negative/unclosed/degenerate0,single-spanvalid,alloriginalM09cells/foilprismspreserved,x-35..45,z-22..8. No flow. ActualBC/profile/wave-zone setup and FS-resolution review pending. MatchfutureC01boundarytreatmenttoW01; do notlaunchunmatchedbaseline.

Bothdashboards source currentJSON; matched_fields_provenance.json covers commonendpoint2.040s M09/M08/M07. Lastcomplete QA passed1920/1360/390 and18-pageprint (calm_support_wave_trial_ui_review.json); agentnowupdatesfailedr3/preparedfoil status. MaxM15,24mwaterdepth,FifthOrderwaves,originals-before-boundedextras,sourcepreservation andseparateHF-sessionprotection unchanged.

"""
p=R/'RESUME_AT_HOME.txt'
p.write_text(head+p.read_text(encoding='utf-8'),encoding='utf-8')
print('Latest completed/failed/prepared stages saved; no solver changed.')
