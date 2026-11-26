from pathlib import Path
import json,datetime
R=Path(__file__).resolve().parent
p=R/'campaign_registry.json';a=json.loads(p.read_text(encoding='utf-8-sig'))
backup=R/'campaign_registry_before_M09_configured.json'
if not backup.exists():backup.write_text(json.dumps(a,indent=2),encoding='utf-8')
if not any(c['id']=='M09' for c in a['cases']):
 a['cases'].append({'id':'M09','role':'Remote coarsening of M08; separate second-order screen','first_layer_um':1.530612244897959,'layers':48,'refinement':1.4,'family':'low_yplus','gpu':'Configured screen; see separate live namespace'})
 p.write_text(json.dumps(a,indent=2),encoding='utf-8')
p=R/'build_dashboard_en.py';s=p.read_text(encoding='utf-8')
s=s.replace("sim_links={}\ndef simulation_link","sim_links={}\nconfigured_live=__import__('configured_mesh_panel').snapshot()\ndef simulation_link")
anchor=" last=latest.get(m,{})\n shifts=a.get('window_mean_shift_pct',{})"
replacement=""" last=latest.get(m,{})
 if m=='M09':
  cjobs=[x for x in configured_live.get('jobs',[]) if x.get('mesh')==m]
  active_cfg=next((x for x in cjobs if x['id']==configured_live.get('state',{}).get('active')),None)
  candidate_cfg=next((x for x in cjobs if x.get('result')),None)
  selected_cfg=candidate_cfg or active_cfg
  if selected_cfg:
   pr=selected_cfg.get('progress',{})
   last={'physical_time_s':pr.get('time_s'),'CD':pr.get('CD'),'CL_total':pr.get('CL_total')}
   status=('Guarded startup' if 'startup' in selected_cfg['id'] else selected_cfg['status'])+' · separate SO screen'
   complete=bool(candidate_cfg)
 shifts=a.get('window_mean_shift_pct',{})"""
assert s.count(anchor)==1;s=s.replace(anchor,replacement)
# File URI makes the scope explicit in both local and private-monitor copies.
s=s.replace('<a href="professor_dashboard.html">Research review ↗</a>','<a href="file:///F:/ntnu/mesh_screening_20261028/professor_dashboard.html" title="Local research review on this computer">Research review · local ↗</a>')
p.write_text(s,encoding='utf-8')
stamp=datetime.datetime.now().astimezone().isoformat()
p=R/'RESUME_AT_HOME.txt';old=p.read_text(encoding='utf-8-sig')
new=f"""CURRENT NIGHT CONTINUATION — {stamp}
T01–T04 and both conservation probes COMPLETED. calm_solver_configuration_decision.json supports SECOND_ORDER1ms10inner for calm mesh screening only. T03/T02 tinyCD/CLchange; T04/T02+0.002573%CD/−0.001457%CL. Final T02/T04 audit professor_inner_audit.json verifies finitefields/phasebounds/independentforces. BothBEandBDF2massresiduals includeaccumulation.
run_configured_mesh_screen.py --run controllerPID15952 ACTIVE under rootqueue.lock. Read configured_mesh_state.json/configured_mesh_plan.json/configured_mesh_results.json and configured_mesh_20261029/controller.lock. M09startup40stepsdt0.5ms50inner reached0.020s; thenM09SO1ms10untilsettled, thenM08/M07matchedsettingcontinuations automatically. Do not duplicate. EachattemptEbacked;preservehistoricalFOresults andallattempts. Finalmeshcomparison mayneedmatchedendpoints iffirstsettledwindows/drift matter near1%.
Bothdashboards regenerate through update_status.py. Maindashboard.html includes prominentconfigured-mesh panel; professor_dashboard.html is a separateEnglishresearchreview fromsameJSON. Professorpage: experimentaldesign/restarttree, completionchronology, originalM04 vscontinueddrift, exactmatchedtests, pressure/viscousFx, actualdifferingmeshcontrols, measuredcost, acceptedinstantaneousfields,plannedFifthOrderwaves24m. Itsliveupdate defaultsOFFforpresenting; toggleONforautomaticreload.
User explicitly authorized agentsforprofessionaldesign,scienceaudit,readability. Reports professor_dashboard_design_review.json/professor_evidence_review.json/professor_visual_review_findings.json. BrowserQA1360/1920/390 andprintarebeingcompleted;readlatestQAfiles. plot_professor_fields.py producescuratedfiguresfromacceptedsavedCSV,notillustrations. ExtendbothviewswithnewacceptedSO/waveresults andkeepcohortsseparate. No stalehardcodedconclusions. Privatepublisherlast_synchealthy;donotreadsecrets.
Latestwavescope24m/FifthOrder/maxM15 andboundedW03–W08extensionbelowremainsactive. Currentheartbeatupdatedtofollownewcontroller.
Historicalblocksbelowarecontext,notcurrentstageinstructions.

"""
p.write_text(new+old,encoding='utf-8')
for name in ['mesh_selection_plan.json','overnight_plan_20261029.json']:
 p=R/name;a=json.loads(p.read_text(encoding='utf-8-sig'))
 a['current_configuration_screen']={'decision':'calm_solver_configuration_decision.json','controller':'run_configured_mesh_screen.py','state':'configured_mesh_state.json','results':'configured_mesh_results.json','namespace':'configured_mesh_20261029','started_controller_pid':15952,'settings':{'order':'SECOND_ORDER','dt_s':.001,'inner':10},'scope':'Calm mesh screen only; selected-mesh time and wave propagation checks remain'}
 a['presentation_views']={'operational':'../dashboard.html','research_review':'../professor_dashboard.html','refresh':'update_status.py builds both','checks':'desktop1360/projector1920/mobile390/print; source exact evidence; distinguish cohorts'}
 p.write_text(json.dumps(a,indent=2),encoding='utf-8')
print('M09 registered and nightly handover refreshed')
