from pathlib import Path
import json,datetime
R=Path(__file__).resolve().parent;stamp=datetime.datetime.now().astimezone().isoformat()
record={'updated_at':stamp,'status':'CPU_preparation_running','controller':'run_wave24m_preparation.py','controller_pid':37384,'state_file':'wave_preparation_state.json','cpu_lock':'E:/ntnu/quasi2d_waves_20261029/preparation.lock','case':'E:/ntnu/quasi2d_waves_20261029/W20_H24_X4_Q2D_r1','workers':2,'gpu':False,'scope':'Build and zero-step initial/profile audit only; not transient propagation or foil forces','changes_from_reference':{'water_depth_m':24,'bottom_z_m':-22,'top_z_m':8,'span_m':.02,'first_wave_front':False,'time_order':'SECOND_ORDER','dt_s':.001},'documentation':'wave_front_local_documentation.json','interpretation':'Installed Siemens documentation says First Wave Front is enabled by default and leaves flat water downstream of Point on Water Level. This is consistent with R4 near-flat initial gauges. Newcase explicitly disables the front and audits the actual setting/bindings/gauges; historicalsource remains untouched. Verify initial_audit.json thenCGNS topology andtransientpropagation before acceptance.'}
(R/'wave24m_preparation_plan.json').write_text(json.dumps(record,indent=2))
for name in ['mesh_selection_plan.json','overnight_plan_20261029.json']:
 p=R/name;a=json.loads(p.read_text(encoding='utf-8-sig'));a['wave_preparation']=record;p.write_text(json.dumps(a,indent=2))
p=R/'RESUME_AT_HOME.txt';text=p.read_text(encoding='utf-8-sig')
note=f"""HEARTBEAT UPDATE — {stamp}
M09 SO1ms10inner is healthy and physically progressing (0.860s/840steps, maxspeedinallcheckedhistory<23m/s; finite independentreports). PID15952/rootlock remainactive; do not duplicate. Latest0.2s means stillsettling; no meshselected.
NEW modestCPU preparation PID37384 run_wave24m_preparation.py: twoCPUworkers, noGPU. Own lock E:/ntnu/quasi2d_waves_20261029/preparation.lock, live state wave_preparation_state.json. Case E:/ntnu/quasi2d_waves_20261029/W20_H24_X4_Q2D_r1 uses verified baseline_clean copy, depth24m,bottom−22,top8,20mmspanoutsidefoil, FifthOrderVofWave,firstwavefrontFALSE,SO1ms. This build only meshes/initializes/exportsCGNS/auditsprofiles and takes ZERO transientsteps. Preserveallattempts; inspectbeforelaunchinganyfurtherCPUbuilder. Aftercompletionaudit initial_audit.json andmesh.CGNS thenpreparetransientgauges.
Installed Siemens documentation (wave_front_local_documentation.json) explains FirstWaveFront defaultON leavesflatwaterahead; consistentwithR4 initialflatgauges. Newcase explicitly disables thisfront and auditsgetter/bindings. No claimofvalidatedpropagationyet. Localreferencepathsandexactsnippetsstored;original16m sourcesuntouched.
Plans cleanedofstale T04pending/M09notlaunchedtop-levelstatus. Bothdashboardscontinuedautomaticrefresh; privatepublisherhealthy; professor_final_qa.json PASS recordedpreviousrelease.

"""
p.write_text(note+text,encoding='utf-8')
print('Wave preparation and live campaign state recorded')
