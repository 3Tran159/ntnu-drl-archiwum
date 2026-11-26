from pathlib import Path
import csv,json,datetime,subprocess,hashlib,shutil,py_compile
h=Path(__file__).resolve().parents[1];oldrun=h/'cases/SP_C_split0_overset/c0_relaxed_init_20261103_005648';source=oldrun/'steady_checkpoint.sim'
state=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text());assert not state.get('active'),'Owned STAR still active'
nativecheck=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'starccm+.exe' -and $_.CommandLine -match ' -batch ' } | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
jobs=json.loads(nativecheck.stdout) if nativecheck.stdout.strip() else [];jobs=[jobs] if isinstance(jobs,dict) else jobs
assert not any(str(h).lower() in j['CommandLine'].lower() for j in jobs),'Owned native batch still active'
saved=json.loads((oldrun/'status.json').read_text());assert saved['status']=='paused_by_marker' and saved['iterations']==430
digest=hashlib.file_digest(source.open('rb'),'sha256').hexdigest();assert digest=='945353bf97a01ea6b57148c99c073db548cdbf24c9aa33ccd5130ecaf684c09a'
rows=list(csv.DictReader((oldrun/'steady_iterations.csv').open()));last=rows[-1];assert int(last['iteration'])==430
s=(h/'macros/FreshC0RelaxedInit.java').read_text(encoding='utf8').replace('class FreshC0RelaxedInit','class ContinueC0FirstOrder').replace('c0_relaxed_init_','c0_first_order_')
s=s.replace('cases/SP_C_split0_overset/c0_overlap_band05mm_20261103_003837/SP_C_mesh_ready.sim','cases/SP_C_split0_overset/c0_relaxed_init_20261103_005648/steady_checkpoint.sim')
s=s.replace('35b44cb5cd54d35cf7e7b849140524b9f2be5d4ffc8b583da44495db5ba88865',digest)
s=s.replace('Only protected pre-motion mesh source allowed','Only reviewed430-iteration steady checkpoint allowed').replace('Fresh uninitialized mesh required; solved checkpoints protected','Saved steady physical time must remain0; no reset permitted').replace('Source mesh fingerprint changed','Source checkpoint fingerprint changed')
s=s.replace('if(!Files.readString(base.resolve("initialization_status.json")).contains("steady_initialization_incomplete"))throw new IllegalStateException("Only incomplete steady initializer may be continued");','if(!Files.readString(base.resolve("status.json")).contains("paused_by_marker"))throw new IllegalStateException("Expected Work-paused steady source");')
needle='((UserFieldFunction)s.getFieldFunctionManager().getFunction("HYDRO_HydrostaticGauge"))'
assert needle in s
readback='StringBuilder loaded=new StringBuilder("physical_time_s="+s.getSolution().getPhysicalTime()+" source_iteration=430\\n");\n'
for key,report in [('Fx_N','HF_Fx_N'),('Fz_N','HF_Fz_N'),('Mh_Nm','HF_Mh_Nm'),('CL_hydro','HF_CL_hydro'),('CD','HF_CD')]:
 expected=float(last[key]);var='loaded_'+key
 readback+=f'double {var}=rv("{report}");if(!Double.isFinite({var})||Math.abs({var}-({expected:.17g}))>1e-6*Math.max(1,Math.abs({expected:.17g})))throw new IllegalStateException("Saved {key} readback mismatch");loaded.append("{key}="+{var}+"\\n");\n'
readback+='Files.writeString(out.resolve("checkpoint_readback.txt"),loaded.toString());\n'
s=s.replace(needle,readback+needle,1)
needle='s.getSolution().initializeSolution();'
assert s.count(needle)==1
s=s.replace(needle,r'''// Intentional continuation: never initialize, clear solution/history, or remesh.
SegregatedFlowModel momentumModel=pc.getModelManager().getModel(SegregatedFlowModel.class);
SstKwTurbModel turbulenceModel=pc.getModelManager().getModel(SstKwTurbModel.class);
int oldFlowOrder=momentumModel.getUpwindOption().getSelected(),oldTurbOrder=turbulenceModel.getUpwindOption().getSelected();
if(oldFlowOrder!=FlowUpwindOption.Type.SECOND_ORDER.getValue()||oldTurbOrder!=UpwindOption.Type.SECOND_ORDER.getValue())throw new IllegalStateException("Expected second-order control schemes");
momentumModel.getUpwindOption().setSelected(FlowUpwindOption.Type.FIRST_ORDER);turbulenceModel.getUpwindOption().setSelected(UpwindOption.Type.FIRST_ORDER);
Files.writeString(out.resolve("convection_change.json"),"{\"flow_before\":"+oldFlowOrder+",\"turbulence_before\":"+oldTurbOrder+",\"flow_after\":"+momentumModel.getUpwindOption().getSelected()+",\"turbulence_after\":"+turbulenceModel.getUpwindOption().getSelected()+",\"start_iteration\":430,\"reset_solution\":false,\"physical_conditions_changed\":false}");
''')
s=s.replace('"fresh_initialized"','"continuation_initial"')
start=s.index('Files.writeString(out.resolve("numerical_change.txt"),');end=s.index('\n',start)
s=s[:start]+r'''Files.writeString(out.resolve("numerical_change.txt"),"Continue exact saved steady fields at iteration430, physical time0, without initialization/clear/remeshing. Only governing numerical change: flow and SST convection SECOND_ORDER to FIRST_ORDER for bounded startup recovery. Retain579468-cell mesh,DISTANCE,NONE conservation,velocity URF0.3,pressure URF0.1,U18,rho1000,mu.001,geometry0deg. Readback verified against source forces. Added iterations recorded separately from native_iteration. This first-order state is diagnostic only; restore second-order convection and matched FLUX_CORRECTION/URANS before any approval.");'''+s[end:]
s=s.replace('max_absolute_pressure_Pa\\n','max_absolute_pressure_Pa,native_iteration\\n')
s=s.replace('","+umax+","+pmax+"\\n"','","+umax+","+pmax+","+(430+k)+"\\n"')
assert 'native_iteration' in s and '(430+k)' in s
macro=h/'macros/ContinueC0FirstOrder.java';macro.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for name in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/name,backup/name)
p=h/'tools/night_native.py';s=p.read_text(encoding='utf8');needle="'FreshC0RelaxedInit.java':8}";assert needle in s
p.write_text(s.replace(needle,"'FreshC0RelaxedInit.java':8,'ContinueC0FirstOrder.java':8}"),encoding='utf8')
p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8');needle="'FreshC0RelaxedInit.java'}";assert needle in s
s=s.replace(needle,"'FreshC0RelaxedInit.java','ContinueC0FirstOrder.java'}")
s=s.replace("'FreshC0RelaxedInit.java':'c0_relaxed_init_',","'ContinueC0FirstOrder.java':'c0_first_order_','FreshC0RelaxedInit.java':'c0_relaxed_init_',")
s=s.replace(".startswith('FreshC0')",".startswith(('FreshC0','ContinueC0'))").replace("('Fresh','Prepare','Finalize','Inspect')","('Fresh','ContinueC0','Prepare','Finalize','Inspect')")
s=s.replace("metrics['iteration']=int(row['iteration']);","metrics['iteration']=int(row.get('native_iteration') or row['iteration']);metrics['additional_iterations']=int(row['iteration']);")
p.write_text(s,encoding='utf8')
p=h/'tools/night_dashboard.py';s=p.read_text(encoding='utf8').replace("case={'FreshC0RelaxedInit.java'","case={'ContinueC0FirstOrder.java':'C0 — kontynuacja od430 iteracji, diagnostyczny schemat1.rzędu','FreshC0RelaxedInit.java'").replace(".startswith('FreshC0')",".startswith(('FreshC0','ContinueC0'))")
p.write_text(s,encoding='utf8')
for name in ['night_native.py','night_queue.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/name),doraise=True)
now=datetime.datetime.now().astimezone().isoformat()
conclusion=dict(at=now,status='work_paused_numerical_anomaly',native_iterations=430,physical_time_s=0,omega_floor_cells=834,k_floor_cells=5,max_viscosity_ratio=100000,checkpoint=str(source),sha256=digest,scientific_approved=False,limitation='Partial steady startup, not proof of asymptotic divergence. Lower relaxation prevents gross blowup but local abnormal head and turbulence clipping develop. Retain fields for controlled first-order recovery.')
(oldrun/'work_conclusion.json').write_text(json.dumps(conclusion,indent=2),encoding='utf8')
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text(encoding='utf8'))
job=dict(id='c0_first_order_continuation',macro=macro.name,input=str(source),initial_time_s=0,angle_deg=0,approved=True,purpose='Continue saved430iteration solution without reset. Change flow/SST convection to first order only for diagnostic recovery; all mesh/physics unchanged. Must restore second order plus matched URANS/FLUX before scientific acceptance.')
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job)
cfg['release_failure_hold']['c0_relaxed_initialization']='Work-paused430iterations with834omega-floor,5k-floor,viscosity cap and abnormal local mean-flow head. Controlled first-order continuation of saved fields, no reset; original result stays unapproved.'
cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
marker=h.parent/'STOP_OWNED_CFD.json'
assert marker.is_file();assert json.loads(marker.read_text())['target_job']=='c0_relaxed_initialization'
dest=h/'audit'/('STOP_relaxed_work_pause_'+stamp+'.json');assert dest.resolve().is_relative_to(h.resolve())
marker.rename(dest)
ev=dict(at=now,kind='work_approved_first_order_recovery',job=job,input_sha256=digest,previous_conclusion=conclusion,scientific_gate=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+now+' Relaxed startup paused after430iterations; complete checkpoint847104592bytes. Approve documented first-order flow/SST convection continuation on exact saved fields, no initialize/clear/remesh.8CPU. First-order result cannot be accepted; restore high-order/matched physics before comparison. No angles.\n')
print(json.dumps(ev,indent=2))
