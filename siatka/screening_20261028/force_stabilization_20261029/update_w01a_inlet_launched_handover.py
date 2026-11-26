from pathlib import Path
import json,datetime,shutil
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029')
now=datetime.datetime.now().astimezone().isoformat();tag=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
p=R/'RESUME_AT_HOME.txt';shutil.copy2(p,R/f'handover_history_{tag}.txt')
text=f"""CURRENT W01a INLET WAVE LAUNCHED - {now}
Controller11916 owns rootqueue.lock andw01a_inlet_wave_r1.lock, launcher33412. Inspect actualprocesses/state before acting. Do NOT launchduplicate.
Case E:/ntnu/quasi2d_waves_20261029/W01a_W20L4_M10_inlet_wave_r1. run_w01a_inlet_wave_r1.py --run launched after CPU three-step audit passed/finished and preplock released; current initialstate GPUloading. Need firstGPUphysicalprogress confirmation.
Computedcalmsource t=.587 SHA bb2f9004ba8993ed6a7c8401be27b15be56d54d04c7743b15013a8925d9a131d. Source/input copiedhashverified. CPUaudit36264 complete0.590, no reinit,3finite steps and exactexpression/setteranalyticreferences atnearzeroH. Full-height ramp validity still monitored, notclaimed.
Wave beginsimmediately atphysical.587; H1e-6->.5 over1.6945346414s cosine. No calmforcesettlingwait. Onlyinlet/upstreamforcing bindingschanged; initialphysicalfields retained; no initializeSolution/clear. SO1ms10inner pressureAMG.01; fixeddepth24, M10 317277cells80m. Native signedvorticity componentVorticityVector[1] added toviews/CSV. 50m/s,phase,resource/sourceguards retained. .01%massflagdiagnostic/userexploratoryexception.
Observecasewave_runtime.csv, wave_activation.json,history/gauges/native_phase_budget.csv,computedcheckpoints. AnalyticloadcachemayNaN butmustfiniteafterfirststep. Stageinlet_wave_ramp/full_amplitude; analysis_origin_snullpendingactualarrival. Newcyclehistoryonly;4repeatedcompleteeligiblecyclesstop,10indicative,20reviewcap. Currentmacrobounded20123stepsfrom.587to20.710; arrival-awareearliercyclescreenstillneedsbinding, do nottreatcalm/rampaswavecycles.
OriginalW01failed1.064preserved, neverrestartitsfields. BriefW01acalmcontroller30672 finishednormally. Autonomousbatch/manuallegacyfull-domainpresetsstillblockeduntilnewrecipevalidated. HF_012_C003_regular_waves untouched. Automationpaused.
Exportfortheothermeshagent: E:/ntnu/handoffs/W01a_domain_settings_20261030_120423.zip. LatestUIagentupdatingnewinletstagewithrichprogress/ETA; nooldW01history.
Previoushandoverbelowisarchival; currentPIDandno-forcesettlingruleaboveoverrideit.
\n"""
p.write_text(text+p.read_text(encoding='utf8'),encoding='utf8')
r=R/'RATUNKOWY_KONTYNUACJA_CHAT.txt';shutil.copy2(r,R/f'RATUNKOWY_KONTYNUACJA_CHAT_history_{tag}.txt');r.write_text(text+'Read actual lock/process/history before every action. This local controller works independently of Work. Stop via case STOP marker for save at physicalstep; neverrestartcompletedattempt.\n',encoding='utf8')
for n in ['overnight_plan_20261029.json','wave_numerical_review_current.json']:
 p=R/n;d=json.loads(p.read_text(encoding='utf8-sig'));d['updated_at']=now;d['current_wave_action']={'status':'GPU_launched_loading','controller_pid':11916,'launcher_pid':33412,'macro':'W01aInletWaveR1.java','controller':'run_w01a_inlet_wave_r1.py','case':'W01a_W20L4_M10_inlet_wave_r1','source_time_s':.587,'calm_settling_required':False,'audit':'w01a_inlet_ramp_step_audit_result.json'};p.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({'saved':now,'controller_pid':11916}))
