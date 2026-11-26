from pathlib import Path
import json,datetime,subprocess,shutil,py_compile
h=Path(__file__).resolve().parents[1];state=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text());assert not state.get('active')
source=h/'cases/SP_C_split0_overset/c0_layers36_zero_storage_20261103_021548/layer_audit_error.sim'
s=r'''package macro;
import star.common.*;import star.vis.*;import star.base.neo.*;import star.base.report.*;import java.nio.file.*;import java.io.*;import java.util.*;
public class InspectC0LayerFailure extends StarMacro{
public void execute(){Simulation s=getActiveSimulation();Path root=Paths.get("F:/ntnu/flap_control/hydro_validation_2606_20261102"),input=Paths.get(s.getSessionPath()).toAbsolutePath().normalize(),out=root.resolve("cases/SP_C_split0_overset/c0_layers36_error_audit_"+System.getenv("NTNU_HYDRO_RUN_ID"));
try{
if(!input.equals(root.resolve("cases/SP_C_split0_overset/c0_layers36_zero_storage_20261103_021548/layer_audit_error.sim")))throw new IllegalStateException("Only failed owned mesh audit allowed");
java.security.MessageDigest md=java.security.MessageDigest.getInstance("SHA-256");try(InputStream f=Files.newInputStream(input)){byte[] b=new byte[1048576];int n;while((n=f.read(b))!=-1)md.update(b,0,n);}
if(!java.util.HexFormat.of().formatHex(md.digest()).equals("f80624ba9f078d2af01dd4d4f50f68ed751f24b548f0274615d1dcf0211f42ab"))throw new IllegalStateException("Source fingerprint changed");
Files.createDirectories(out);s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
double time=s.getSolution().getPhysicalTime();int iteration=s.getSimulationIterator().getCurrentIteration();
Representation full=s.getRepresentationManager().getObject("Overset Mesh");StringBuilder info=new StringBuilder("source="+input+"\nphysical_time="+time+"\nnative_iteration="+iteration+"\n");
List<FieldFunction> fields=new ArrayList<>();for(String name:List.of("OversetCellStatus","OversetErrorStatus","OversetInterpolationType","Volume","CellQuality"))fields.add(s.getFieldFunctionManager().getFunction(name));
for(String name:List.of("Background","FlapOverset")){Region r=s.getRegionManager().getRegion(name);PlaneSection p=s.getPartManager().createImplicitPart(List.of(r),List.of(0.,1.,0.),List.of(0.,.02,0.),0,1,new DoubleVector(new double[]{0}));
XyzInternalTable t=s.getTableManager().createTable(XyzInternalTable.class);t.getParts().setObjects(p);t.setRepresentation(full);t.setExtractVertexData(false);t.setFieldFunctions(fields);t.extract();t.export(out.resolve(name+"_failed_full_plane.csv").toString());
for(Boundary b:r.getBoundaryManager().getBoundaries())if(b.getBoundaryType() instanceof WallBoundary&&!b.getPresentationName().endsWith("bottom")){info.append(name+" wall="+b.getPresentationName()+" dynamic="+b.getConditions().get(DynamicOversetBehaviour.class).getSelected());try{info.append(" activeLayers="+b.getValues().get(NumActiveLayers.class).getNumLayers());}catch(Exception e){info.append(" no_activeLayers");}info.append("\n");}}
for(Interface iface:s.getInterfaceManager().getObjects())if(iface instanceof IndirectRegionInterface){IndirectRegionInterface i=(IndirectRegionInterface)iface;info.append("interface="+i.getPresentationName()+" alternate="+i.getUseAlternateHoleCutting()+" close="+i.getCloseProximity()+" prism_shrink="+i.getPrismLayerShrinkage()+" errors_as_warning="+i.getTreatErrorAsWarning()+"\n");}
Files.writeString(out.resolve("native_settings.txt"),info.toString());
if(s.getSimulationIterator().getCurrentIteration()!=iteration||s.getSolution().getPhysicalTime()!=time)throw new IllegalStateException("Inspection changed counters");
Files.writeString(out.resolve("status.json"),"{\"status\":\"inspection_complete\",\"solver_steps\":0,\"simulation_saved\":false,\"scientific_approved\":false,\"training_approved\":false}");
}catch(Exception e){try{Files.writeString(out.resolve("error.txt"),e.toString());}catch(Exception ignored){}throw new RuntimeException(e);}
}}
'''
macro=h/'macros/InspectC0LayerFailure.java';assert not macro.exists();macro.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for n in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/n,backup/n)
p=h/'tools/night_native.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('allowed={',"allowed={'"+macro.name+"':1,",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_queue.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('ALLOWED={',"ALLOWED={'"+macro.name+"',",1).replace('prefix={',"prefix={'"+macro.name+"':'c0_layers36_error_audit_',",1);p.write_text(t,encoding='utf8')
for n in ['night_native.py','night_queue.py']:py_compile.compile(str(h/'tools'/n),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text())
job=dict(id='c0_wall_layers36_failure_inspection',macro=macro.name,input=str(source),initial_time_s=0,angle_deg=0,approved=True,purpose='Read-only1CPU localization of native Overset Error Status6 from failed36-layer actual reassembly. No initialization, no field/motion/mesh changes, no solver steps, no simulation save.')
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job);cfg['release_failure_hold']['c0_wall_layers36_zero_storage']='Reject36-layer candidate; allow only read-only localization of generated error6, no flow approval.';cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_wall36_rejected_orphan_cells',job=job,scientific_approved=False,outcome='Actual reassembly fails: Background acceptors outside FlapOverset, ErrorStatus6, zero donor. No PDE steps; error checkpoint520766038bytes SHA256f80624ba9f078d2af01dd4d4f50f68ed751f24b548f0274615d1dcf0211f42ab. Source1850 remains intact.')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+ev['at']+' '+ev['outcome']+'\n')
p=h/'WORK_CURRENT_REVIEW.json';v=json.loads(p.read_text(encoding='utf8'));v['at']=ev['at'];v['next']='Odczyt współrzędnych komórek z błędem6 po pełnym wyznaczeniu36 aktywnych warstw. Ten wariant został odrzucony; brak zgody na przepływ lub wychylenia.';v['obstacle']='36-warstwowy wariant generuje akceptory bez dawców poza regionem klapki. Błąd sił0° nadal nierozstrzygnięty.';v['mesh']+=' Po rzeczywistym odtworzeniu łączności wariant36warstw nie przeszedł kontroli: błąd6/zero donor. Zatrzymany przed obliczeniami przepływu.';p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps(ev,indent=2))
