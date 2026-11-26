from pathlib import Path
import csv,json,hashlib,subprocess,datetime,shutil,py_compile
h=Path(__file__).resolve().parents[1];folder=h/'cases/SP_C_split0_overset/c0_flux_recovery_20261103_012140';source=folder/'steady_checkpoint.sim'
state=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text());assert not state.get('active'),'Owned STAR still active'
digest=hashlib.file_digest(source.open('rb'),'sha256').hexdigest();assert digest=='932e6c274be656cdfab3c5d19c78c5f5d6f1fda8d3226b9633e950c3b637ee18'
last=list(csv.DictReader((folder/'steady_iterations.csv').open()))[-1];assert int(last['native_iteration'])==1850 and float(last['p_absolute_min_Pa'])>12339.2148 and float(last['omega_floor_cells'])==0 and float(last['k_floor_cells'])==0
source_text=(h/'macros/FreshC0RelaxedInit.java').read_text(encoding='utf8');s=source_text[:source_text.index('public void execute()')].replace('class FreshC0RelaxedInit','class PrepareC0WallLayers36')
body=r'''
public void execute(){s=getActiveSimulation();variant=System.getenv("NTNU_HYDRO_VARIANT");Path input=Paths.get(s.getSessionPath()).toAbsolutePath().normalize();out=root.resolve("cases/SP_C_split0_overset/c0_layers36_"+System.getenv("NTNU_HYDRO_RUN_ID"));
try{
if(!input.equals(root.resolve("cases/SP_C_split0_overset/c0_flux_recovery_20261103_012140/steady_checkpoint.sim"))||!"SP_C".equals(variant))throw new IllegalStateException("Only reviewed first-order flux checkpoint allowed");
if(Math.abs(s.getSolution().getPhysicalTime())>1e-12)throw new IllegalStateException("Steady time0 required");
java.security.MessageDigest md=java.security.MessageDigest.getInstance("SHA-256");try(InputStream stream=Files.newInputStream(input)){byte[] chunk=new byte[1048576];int n;while((n=stream.read(chunk))!=-1)md.update(chunk,0,n);}
if(!java.util.HexFormat.of().formatHex(md.digest()).equals("932e6c274be656cdfab3c5d19c78c5f5d6f1fda8d3226b9633e950c3b637ee18"))throw new IllegalStateException("Source fingerprint changed");
Files.createDirectories(out);guard();
PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getObject("HYDRO water SST singlephase");
if(pc.getModelManager().getModel(SteadyModel.class)==null||pc.getModelManager().getModel(SegregatedFlowModel.class).getUpwindOption().getSelected()!=FlowUpwindOption.Type.FIRST_ORDER.getValue()||pc.getModelManager().getModel(SstKwTurbModel.class).getUpwindOption().getSelected()!=UpwindOption.Type.FIRST_ORDER.getValue()||pc.getModelManager().getModel(OversetConservationModel.class).getOversetConservationOption().getSelected()!=OversetConservationOption.Type.FLUX_CORRECTION.getValue())throw new IllegalStateException("Source settings mismatch");
for(Region r:s.getRegionManager().getRegions())if(pc.equals(r.getPhysicsContinuum())){regions.add(r);if(!(r.getValues().get(MotionSpecification.class).getMotion() instanceof StationaryMotion))throw new IllegalStateException("Static source required");for(Boundary b:r.getBoundaryManager().getBoundaries())if(b.getBoundaryType() instanceof WallBoundary&&!b.getPresentationName().endsWith("bottom")){if(b.getPresentationName().contains("Hydro_Flap"))flap.add(b);else fixed.add(b);}}
if(regions.size()!=2||fixed.size()!=2||flap.size()!=2)throw new IllegalStateException("Unexpected wall grouping");
READBACK_PLACEHOLDER
savedFlapBounds=flapBounds();captureComparison("source");captureFields("source");auditFull("before",579468);
Boundary target=null;for(Boundary b:fixed)if(b.getPresentationName().endsWith("Hydro_Main.NativeSkin")){if(target!=null)throw new IllegalStateException("Ambiguous target wall");target=b;}if(target==null)throw new IllegalStateException("Main NativeSkin missing");
StringBuilder changes=new StringBuilder("Source native iteration1850; zero solver steps; geometry and mesh coordinates unchanged. Numerical hole-cutting diagnostic only.\\n");
for(Boundary b:fixed)changes.append("before "+b.getPresentationName()+" dynamic="+b.getConditions().get(DynamicOversetBehaviour.class).getSelected()+"\\n");
target.getConditions().get(DynamicOversetBehaviour.class).setSelected(DynamicOversetBehaviour.Type.ALWAYS_ACTIVE);
target.getValues().get(NumActiveLayers.class).setNumLayers(36);
changes.append("Changed only "+target.getPresentationName()+" to ALWAYS_ACTIVE, NumberActiveLayers="+target.getValues().get(NumActiveLayers.class).getNumLayers()+"; hinge arc and flap boundaries retained.\\n");
for(Interface iface:s.getInterfaceManager().getObjects())if(iface instanceof IndirectRegionInterface){IndirectRegionInterface in=(IndirectRegionInterface)iface;if(in.getTreatErrorAsWarning()||!in.getConditions().get(OversetHoleCuttingOptions.class).getBoolean("ZeroDonorCheckOption"))throw new IllegalStateException("Strict Overset guards required");s.getInterfaceManager().initializeInterfaces(List.of(iface));}
checkPose("after_layer_protection");auditFull("after",579468);captureComparison("after");captureFields("after");
for(Boundary b:fixed)changes.append("after "+b.getPresentationName()+" dynamic="+b.getConditions().get(DynamicOversetBehaviour.class).getSelected()+"\\n");
Files.writeString(out.resolve("numerical_change.txt"),changes.toString());
Files.copy(input.getParent().resolve("normalization.json"),out.resolve("normalization.json"));
String seed="{\"source_native_iteration\":1850,\"physical_time_s\":0,\"solver_steps\":0,\"Fx_N\":"+rv("HF_Fx_N")+",\"Fz_N\":"+rv("HF_Fz_N")+",\"CL_hydro\":"+rv("HF_CL_hydro")+",\"CD\":"+rv("HF_CD")+",\"Mh_Nm\":"+rv("HF_Mh_Nm")+",\"p_absolute_min_Pa\":"+rv("HF_pabs_liquid_all")+"}";
Files.writeString(out.resolve("checkpoint_seed.json"),seed);
s.saveState(out.resolve("layer_candidate.sim").toString());
Files.writeString(out.resolve("status.json"),"{\"status\":\"mesh_connectivity_prepared\",\"cells\":579468,\"source_native_iteration\":1850,\"saved_time_s\":0,\"solver_steps\":0,\"protected_layers\":36,\"mesh_regenerated\":false,\"geometric_active_cell_audit_pending\":true,\"scientific_approved\":false,\"training_approved\":false}");
note("Native connectivity candidate saved; Work must verify active cells outside both bodies and stencil placement before any solve");
}catch(Exception e){try{Files.writeString(out.resolve("preparation_error.txt"),e.toString());Files.writeString(out.resolve("status.json"),"{\"status\":\"mesh_preparation_error\",\"solver_steps\":0,\"saved_time_s\":0,\"scientific_approved\":false}");s.saveState(out.resolve("layer_audit_error.sim").toString());}catch(Exception ignored){}throw new RuntimeException(e);}
}}
'''
rb='StringBuilder loaded=new StringBuilder("physical_time_s=0 source_iteration=1850\\n");\n'
for key,report in [('Fx_N','HF_Fx_N'),('Fz_N','HF_Fz_N'),('Mh_Nm','HF_Mh_Nm'),('CL_hydro','HF_CL_hydro'),('CD','HF_CD')]:
 v=float(last[key]);var='loaded_'+key
 rb+=f'double {var}=rv("{report}");if(!Double.isFinite({var})||Math.abs({var}-({v:.17g}))>1e-6*Math.max(1,Math.abs({v:.17g})))throw new IllegalStateException("Readback {key} mismatch");loaded.append("{key}="+{var}+"\\n");\n'
rb+='Files.writeString(out.resolve("checkpoint_readback.txt"),loaded.toString());'
s+=body.replace('READBACK_PLACEHOLDER',rb);assert 'getSimulationIterator().step' not in body and 'initializeSolution' not in body
macro=h/'macros/PrepareC0WallLayers36.java';assert not macro.exists();macro.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for n in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/n,backup/n)
p=h/'tools/night_native.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('allowed={',"allowed={'"+macro.name+"':1,",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_queue.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('ALLOWED={',"ALLOWED={'"+macro.name+"',",1).replace('prefix={',"prefix={'"+macro.name+"':'c0_layers36_',",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_dashboard.py';t=p.read_text(encoding='utf8').replace('case={',"case={'"+macro.name+"':'C0 — audyt36 aktywnych warstw przy zewnętrznej ścianie płata',",1);p.write_text(t,encoding='utf8')
for n in ['night_native.py','night_queue.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/n),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text());job=dict(id='c0_wall_layers36_audit',macro=macro.name,input=str(source),initial_time_s=0,angle_deg=0,approved=True,purpose='Mesh-connectivity-only diagnostic,1CPU,zero solver steps. Force36 active cell layers only on main NativeSkin, retaining hinge arc/flap settings and mesh coordinates. Geometric active-cell check and placement audit required before any solve. Uses retained safe first-order flux state1850, not failed momentum2 state.')
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job);cfg['release_failure_hold']['c0_momentum2_continuation']='Pressure gate stopped90 iterations; pure momentum second-order restoration recreated near-wall Overset jet/pressure undershoot with zero SST clipping. No repeat; only1CPU native connectivity experiment on safe retained source.'
marker=h.parent/'STOP_OWNED_CFD.json'
if marker.exists():
 m=json.loads(marker.read_text());assert m.get('target_job')=='c0_momentum2_continuation' and m.get('reason')=='scientific_runtime_gate'
 dst=h/'audit'/('STOP_momentum2_safety_'+stamp+'.json');assert dst.resolve().is_relative_to(h.resolve());marker.rename(dst)
cfg['controller_exit_requested']=True;tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_approved_wall_layer_connectivity_audit',job=job,input_sha256=digest,scientific_approved=False,rationale='Measured active/acceptor transition at geometric layer26-29,0.5-0.75mm from smooth main wall.36th layer near2.2mm and normal size0.35mm, closer to0.5mm Overset cells. This is a test, not assumed safe: force no active cells inside either solid before solving.')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+ev['at']+' '+ev['rationale']+' Native1CPU audit only; no flow.\\n')
print(json.dumps(ev,indent=2))
