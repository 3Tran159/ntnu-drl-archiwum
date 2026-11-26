from pathlib import Path
import json,datetime,subprocess,shutil,py_compile
h=Path(__file__).resolve().parents[1]
state=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text());assert not state.get('active')
previous=h/'cases/SP_C_split0_overset/c0_layers36_20261103_014813'
review=json.loads((previous/'work_wall_layer_audit.json').read_text());assert not review['connectivity_changed']
s=(h/'macros/PrepareC0WallLayers36.java').read_text(encoding='utf8')
s=s.replace('class PrepareC0WallLayers36','class PrepareC0WallLayersRecut').replace('c0_layers36_','c0_layers36_recut_')
old='s.getInterfaceManager().initializeInterfaces(List.of(iface));'
assert s.count(old)==1
s=s.replace(old,'in.setVerbosity(IndirectRegionInterfaceVerbosity.DIAGNOSTICS);s.getInterfaceManager().resetInterfaces(List.of(iface));'+old)
helper=r'''
void exportNativeWallVertices(String label)throws Exception{
int i=0;for(List<Boundary> bs:List.of(fixed,flap)){String name=i++==0?"main":"flap";
XyzInternalTable table=s.getTableManager().createTable(XyzInternalTable.class);table.getParts().setObjects(bs);table.setRepresentation(s.getRepresentationManager().getObject("Volume Mesh"));table.setExtractVertexData(true);table.setFieldFunctions(List.of(s.getFieldFunctionManager().getFunction("Pressure")));table.extract();table.export(out.resolve(name+"_"+label+"_native_wall_vertices.csv").toString());s.getTableManager().removeObjects(table);}
}
'''
s=s.replace('public void execute()',helper+'\npublic void execute()',1)
s=s.replace('savedFlapBounds=flapBounds();captureComparison("source")','savedFlapBounds=flapBounds();exportNativeWallVertices("source");captureComparison("source")')
s=s.replace('captureComparison("after");captureFields("after");','captureComparison("after");captureFields("after");exportNativeWallVertices("after");')
s=s.replace('\\\\n','\\n')
macro=h/'macros/PrepareC0WallLayersRecut.java';assert not macro.exists();macro.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for n in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/n,backup/n)
p=h/'tools/night_native.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('allowed={',"allowed={'"+macro.name+"':1,",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_queue.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('ALLOWED={',"ALLOWED={'"+macro.name+"',",1).replace('prefix={',"prefix={'"+macro.name+"':'c0_layers36_recut_',",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_dashboard.py';t=p.read_text(encoding='utf8').replace('case={',"case={'"+macro.name+"':'C0 — ponowne wyznaczenie Overset, 36 warstw, bez obliczeń przepływu',",1);p.write_text(t,encoding='utf8')
for n in ['night_native.py','night_queue.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/n),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text())
job=dict(id='c0_wall_layers36_recut',macro=macro.name,input=str(h/'cases/SP_C_split0_overset/c0_flux_recovery_20261103_012140/steady_checkpoint.sim'),initial_time_s=0,angle_deg=0,approved=True,purpose='1CPU zero-solver-step interface reset+initialize to actually recompute wall-layer hole cutting. Prior initialize-only audit changed zero statuses; no efficacy claim. Export native wall vertices to distinguish remeshed wall from input STL. Work geometry/connectivity review mandatory before flow.')
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job);cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_connectivity_recut_audit',job=job,scientific_approved=False,prior_outcome='Native settings saved but 579468 statuses and coordinates identical; setting not proven effective. Recompute existing interface using supported resetInterfaces+initializeInterfaces, no solution initialization or mesh generation.')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+ev['at']+' '+ev['prior_outcome']+'\n')
print(json.dumps(ev,indent=2))
