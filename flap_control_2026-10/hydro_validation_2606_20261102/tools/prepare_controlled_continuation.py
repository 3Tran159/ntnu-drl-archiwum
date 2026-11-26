from pathlib import Path
import sys,json,csv,datetime,hashlib,subprocess,shutil,py_compile
h=Path(__file__).resolve().parents[1];folder=Path(sys.argv[1]).resolve();mode=sys.argv[2]
assert folder.is_relative_to(h/'cases/SP_C_split0_overset')
settings={
 'flux':('ContinueC0Flux','c0_flux_recovery_','FIRST_ORDER','FIRST_ORDER','NONE','FIRST_ORDER','FIRST_ORDER','FLUX_CORRECTION',1000),
 'momentum2':('ContinueC0MomentumSecond','c0_momentum_second_','FIRST_ORDER','FIRST_ORDER','FLUX_CORRECTION','SECOND_ORDER','FIRST_ORDER','FLUX_CORRECTION',500),
 'turbulence2':('ContinueC0TurbulenceSecond','c0_turbulence_second_','SECOND_ORDER','FIRST_ORDER','FLUX_CORRECTION','SECOND_ORDER','SECOND_ORDER','FLUX_CORRECTION',1000)}
assert mode in settings
name,prefix,oldflow,oldturb,oldflux,newflow,newturb,newflux,cap=settings[mode]
state=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text());assert not state.get('active'),'Do not overlap owned STAR jobs'
source=folder/'steady_checkpoint.sim';status=json.loads((folder/'status.json').read_text())
assert status['status'] in ['paused_by_marker','steady_diagnostic_ready','steady_initialization_incomplete']
rows=list(csv.DictReader((folder/'steady_iterations.csv').open()));last=rows[-1]
start=int(last.get('native_iteration') or last['iteration'])
assert float(last['p_absolute_min_Pa'])>12339.214766776897 and float(last['mass_imbalance_relative'])<1e-4
assert float(last['omega_floor_cells'])==0 and float(last['k_floor_cells'])==0 and float(last['max_turbulent_viscosity_ratio'])<99999 and float(last['overset_error_cells'])==0
cache=state['checkpoint_integrity'][str(source)];assert cache['native_save_complete'] and cache['saved_time_s']==0
digest=hashlib.file_digest(source.open('rb'),'sha256').hexdigest();assert digest==cache['sha256'] and source.stat().st_size==cache['bytes']
native=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'starccm+.exe' -and $_.CommandLine -match ' -batch ' } | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
jobs=json.loads(native.stdout) if native.stdout.strip() else [];jobs=[jobs] if isinstance(jobs,dict) else jobs
assert not any(str(h).lower() in j['CommandLine'].lower() for j in jobs),'Owned native batch still active'
s=(h/'macros/FreshC0RelaxedInit.java').read_text(encoding='utf8')
s=s.replace('class FreshC0RelaxedInit','class '+name).replace('c0_relaxed_init_',prefix)
s=s.replace('cases/SP_C_split0_overset/c0_overlap_band05mm_20261103_003837/SP_C_mesh_ready.sim',source.relative_to(h).as_posix())
s=s.replace('35b44cb5cd54d35cf7e7b849140524b9f2be5d4ffc8b583da44495db5ba88865',digest)
s=s.replace('Only protected pre-motion mesh source allowed','Only exact reviewed steady checkpoint allowed').replace('Fresh uninitialized mesh required; solved checkpoints protected','Saved steady physical time must remain0; no reset permitted').replace('Source mesh fingerprint changed','Source checkpoint fingerprint changed')
s=s.replace('if(!Files.readString(base.resolve("initialization_status.json")).contains("steady_initialization_incomplete"))throw new IllegalStateException("Only incomplete steady initializer may be continued");','')
needle='((UserFieldFunction)s.getFieldFunctionManager().getFunction("HYDRO_HydrostaticGauge"))';assert needle in s
rb='StringBuilder loaded=new StringBuilder("physical_time_s="+s.getSolution().getPhysicalTime()+" source_iteration='+str(start)+'\\n");\n'
for key,report in [('Fx_N','HF_Fx_N'),('Fz_N','HF_Fz_N'),('Mh_Nm','HF_Mh_Nm'),('CL_hydro','HF_CL_hydro'),('CD','HF_CD')]:
 v=float(last[key]);var='loaded_'+key
 rb+=f'double {var}=rv("{report}");if(!Double.isFinite({var})||Math.abs({var}-({v:.17g}))>1e-6*Math.max(1,Math.abs({v:.17g})))throw new IllegalStateException("Saved {key} readback mismatch");loaded.append("{key}="+{var}+"\\n");\n'
rb+='Files.writeString(out.resolve("checkpoint_readback.txt"),loaded.toString());\n'
s=s.replace(needle,rb+needle,1)
needle='conservation.getOversetConservationOption().setSelected(OversetConservationOption.Type.NONE);';assert s.count(needle)==1
s=s.replace(needle,'if(conservation.getOversetConservationOption().getSelected()!=OversetConservationOption.Type.'+oldflux+'.getValue())throw new IllegalStateException("Unexpected source conservation setting");\nconservation.getOversetConservationOption().setSelected(OversetConservationOption.Type.'+newflux+');')
needle='s.getSolution().initializeSolution();';assert s.count(needle)==1
scheme=f'''// Preserve saved fields/history; no initialization, clearing or remeshing.
SegregatedFlowModel momentumModel=pc.getModelManager().getModel(SegregatedFlowModel.class);
SstKwTurbModel turbulenceModel=pc.getModelManager().getModel(SstKwTurbModel.class);
if(momentumModel.getUpwindOption().getSelected()!=FlowUpwindOption.Type.{oldflow}.getValue()||turbulenceModel.getUpwindOption().getSelected()!=UpwindOption.Type.{oldturb}.getValue())throw new IllegalStateException("Unexpected source convection scheme");
momentumModel.getUpwindOption().setSelected(FlowUpwindOption.Type.{newflow});turbulenceModel.getUpwindOption().setSelected(UpwindOption.Type.{newturb});
Files.writeString(out.resolve("convection_change.txt"),"flow {oldflow} to {newflow}; turbulence {oldturb} to {newturb}; conservation {oldflux} to {newflux}; source_iteration={start}; no reset");
'''
s=s.replace(needle,scheme)
s=s.replace('if(dynamicUrf)throw','if(Math.abs(oldVelocityUrf-.3)>1e-12||Math.abs(oldPressureUrf-.1)>1e-12)throw new IllegalStateException("Unexpected source relaxation");\nif(dynamicUrf)throw')
s=s.replace('"fresh_initialized"','"continuation_initial"')
i=s.index('Files.writeString(out.resolve("numerical_change.txt"),');j=s.index('\n',i)
description=f'Continue exact saved steady fields at native iteration{start}, time0. Numerical diagnostic mode {mode}: flow {oldflow} to {newflow}, SST {oldturb} to {newturb}, Overset conservation {oldflux} to {newflux}. Preserve579468-cell mesh,DISTANCE,U18,rho1000,mu.001,URF0.3/0.1,0deg geometry. No reset/remeshing. Strict pressure/mass/turbulence/Overset guards from first block. No scientific approval until matched second-order URANS is evaluated. CSV iteration=additional; native_iteration={start}+iteration.'
s=s[:i]+'Files.writeString(out.resolve("numerical_change.txt"),"'+description+'");'+s[j:]
s=s.replace('max_absolute_pressure_Pa\\n','max_absolute_pressure_Pa,native_iteration\\n')
s=s.replace('","+umax+","+pmax+"\\n"','","+umax+","+pmax+","+('+str(start)+'+k)+"\\n"')
s=s.replace('k<=1500','k<='+str(cap)).replace('+"/1500','+"/'+str(cap))
needle='if(!Double.isFinite(oe+omega+kfloor+visc)||oe>0)throw new IllegalStateException("Overset or field diagnostic invalid");'
assert needle in s
s=s.replace(needle,needle+'\nif(p<=12339.214766776897||bal>=1e-4||omega>0||kfloor>0||visc>=99999)throw new IllegalStateException("Strict pressure/mass/turbulence gate violated");')
macro=h/'macros'/(name+'.java');assert not macro.exists(),'Do not overwrite an existing diagnostic macro';macro.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for f in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/f,backup/f)
p=h/'tools/night_native.py';s=p.read_text(encoding='utf8');assert name not in s;s=s.replace('allowed={',"allowed={'"+name+".java':8,",1);p.write_text(s,encoding='utf8')
p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8');assert name not in s;s=s.replace('ALLOWED={',"ALLOWED={'"+name+".java',",1).replace('prefix={',"prefix={'"+name+".java':'"+prefix+"',",1);p.write_text(s,encoding='utf8')
p=h/'tools/night_dashboard.py';s=p.read_text(encoding='utf8');s=s.replace("case={","case={'"+name+".java':'C0 — "+mode+", kontynuacja od"+str(start)+" iteracji',",1);p.write_text(s,encoding='utf8')
for f in ['night_native.py','night_queue.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/f),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text(encoding='utf8'))
sourcejob=next(job['id'] for job in state['jobs'].values() if job.get('output')==str(folder))
guards=dict(minimum_absolute_pressure_Pa=12339.214766776897,maximum_mass_imbalance_relative=1e-4,maximum_omega_floor_cells=0,maximum_k_floor_cells=0,maximum_turbulent_viscosity_ratio=99999,maximum_overset_error_cells=0)
job=dict(id='c0_'+mode+'_continuation',macro=macro.name,input=str(source),initial_time_s=0,angle_deg=0,approved=True,purpose=description,runtime_guards=guards)
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job)
cfg['release_failure_hold'][sourcejob]='Reviewed deliberate pause of unapproved numerical initialization; next isolated numerical change documented; strict source and runtime guards retained.'
cfg['controller_exit_requested']=True
marker=h.parent/'STOP_OWNED_CFD.json'
if marker.exists():
 m=json.loads(marker.read_text());assert m.get('target_job')==sourcejob and m.get('source')=='Work','Do not release unrelated or safety-triggered marker'
 dest=h/'audit'/('STOP_'+mode+'_handover_'+stamp+'.json');assert dest.resolve().is_relative_to(h.resolve());marker.rename(dest)
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_approved_controlled_continuation',job=job,input_sha256=digest,source_native_iteration=start,scientific_approved=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+ev['at']+' '+description+'\n')
print(json.dumps(ev,indent=2))
