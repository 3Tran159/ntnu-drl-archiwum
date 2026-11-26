from pathlib import Path
import json,datetime,subprocess,shutil,py_compile
h=Path(__file__).resolve().parents[1];state=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text());assert not state.get('active')
previous=h/'cases/SP_C_split0_overset/c0_layers36_frozen_20261103_015909'
assert not json.loads((previous/'work_wall_layer_audit.json').read_text())['connectivity_changed']
s=(h/'macros/PrepareC0WallLayersRecut.java').read_text(encoding='utf8').replace('class PrepareC0WallLayersRecut','class PrepareC0WallLayersCold').replace('c0_layers36_recut_','c0_layers36_cold_')
s=s.replace('cases/SP_C_split0_overset/c0_flux_recovery_20261103_012140/steady_checkpoint.sim','cases/SP_C_split0_overset/c0_overlap_band05mm_20261103_003837/SP_C_mesh_ready.sim')
s=s.replace('932e6c274be656cdfab3c5d19c78c5f5d6f1fda8d3226b9633e950c3b637ee18','35b44cb5cd54d35cf7e7b849140524b9f2be5d4ffc8b583da44495db5ba88865')
s=s.replace('Only reviewed first-order flux checkpoint allowed','Only protected zero-step mesh source allowed; solved checkpoints forbidden')
i=s.index('if(pc.getModelManager().getModel(SteadyModel.class)==null||');j=s.index('\n',i)
s=s[:i]+'if(pc.getModelManager().getModel(ImplicitUnsteadyModel.class)==null||s.getSimulationIterator().getCurrentIteration()!=0)throw new IllegalStateException("Exact zero-iteration unsteady mesh source required");'+s[j:]
s=s.replace('if(!(r.getValues().get(MotionSpecification.class).getMotion() instanceof StationaryMotion))throw new IllegalStateException("Static source required");','if(r.getValues().get(MotionSpecification.class).getMotion() instanceof RotatingMotion){String law=((RotationAngle)((RotatingMotion)r.getValues().get(MotionSpecification.class).getMotion()).getRotationSpecification()).getRotationAngle().getDefinition();if(!law.equals("<0 deg>"))throw new IllegalStateException("Zero-angle source required");}')
i=s.index('StringBuilder loaded=new StringBuilder(');j=s.index('savedFlapBounds=flapBounds();',i)
s=s[:i]+'Files.writeString(out.resolve("checkpoint_readback.txt"),"Protected pre-flow mesh source, native_iteration="+s.getSimulationIterator().getCurrentIteration()+", time="+s.getSolution().getPhysicalTime()+"; no resolved flow solution used.");\n'+s[j:]
s=s.replace('Source native iteration1850; zero solver steps;','Source zero-iteration uniform-field mesh only; no solved flow checkpoint reset; zero solver steps;')
needle='for(Interface iface:s.getInterfaceManager().getObjects())if(iface instanceof IndirectRegionInterface){IndirectRegionInterface in=(IndirectRegionInterface)iface;'
assert s.count(needle)==1
s=s.replace(needle,'s.getSolverManager().getSolver(SegregatedFlowSolver.class).setContinuityInitialization(false);s.getSolution().initializeSolution();\n'+needle)
i=s.index('String seed=');j=s.index('s.saveState(out.resolve("layer_candidate.sim")',i)
s=s[:i]+s[j:]
s=s.replace('layer_candidate.sim','mesh_only_candidate.sim')
s=s.replace('\\\"source_native_iteration\\\":1850','\\\"source_native_iteration\\\":0,\\\"field_storage_initial_only\\\":true')
s=s.replace('Native connectivity candidate saved; Work must verify active cells outside both bodies and stencil placement before any solve','Mesh-only candidate, uniform initialization fields. Not a resume solution. Work must audit geometry/connectivity; healthy flow checkpoint remains intact.')
s=s.replace('checkPose("after_layer_protection");','if(s.getSimulationIterator().getCurrentIteration()!=0||Math.abs(s.getSolution().getPhysicalTime())>1e-12)throw new IllegalStateException("Zero-step mesh audit advanced flow");checkPose("after_layer_protection");')
macro=h/'macros/PrepareC0WallLayersCold.java';assert not macro.exists();macro.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for n in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/n,backup/n)
p=h/'tools/night_native.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('allowed={',"allowed={'"+macro.name+"':1,",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_queue.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('ALLOWED={',"ALLOWED={'"+macro.name+"',",1).replace('prefix={',"prefix={'"+macro.name+"':'c0_layers36_cold_',",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_dashboard.py';t=p.read_text(encoding='utf8').replace('case={',"case={'"+macro.name+"':'C0 — test 36 warstw na siatce sprzed obliczeń',",1);p.write_text(t,encoding='utf8')
for n in ['night_native.py','night_queue.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/n),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text())
job=dict(id='c0_wall_layers36_cold',macro=macro.name,input=str(h/'cases/SP_C_split0_overset/c0_overlap_band05mm_20261103_003837/SP_C_mesh_ready.sim'),initial_time_s=0,angle_deg=0,approved=True,purpose='Connectivity-only1CPU audit on retained zero-iteration mesh source. Apply36main-wall layers before native uniform-field initialization, continuity initialization disabled. Never clears/reinitializes the solved1850 checkpoint. No PDE steps, no mesh generation; tests whether earlier unchanged statuses were a cached-assembly effect. Result is not a resumable flow solution.')
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job);cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_cold_mesh_connectivity_control',job=job,scientific_approved=False,prior_outcome='Even native1850->1851 frozen step left all579468 statuses unchanged. Native vertex geometry and active-center containment pass. Isolate initialization sensitivity on preserved zero-step source; do not reset saved hydro state.')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+ev['at']+' '+ev['prior_outcome']+'\n')
print(json.dumps(ev,indent=2))
