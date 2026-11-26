from pathlib import Path
import json,datetime,subprocess,shutil,py_compile
h=Path(__file__).resolve().parents[1];state=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text());assert not state.get('active')
e=json.loads((h/'validation/C0_wall36_error_localization.json').read_text())['regions']['Background'];assert e['error_cell_count']==195 and e['errors_inside_flap']==195 and e['errors_outside_outer_box']==0
s=(h/'macros/PrepareC0WallLayersZeroStorage.java').read_text(encoding='utf8').replace('class PrepareC0WallLayersZeroStorage','class PrepareC0ForewallLayers').replace('c0_layers36_zero_storage_','c0_forewall36_')
needle='StringBuilder changes=new StringBuilder(';i=s.index(needle)
split=r'''
// Numerical boundary partition only; identical physical wall vertices and no remeshing.
// Protection ends at x=0.80m (x/c=0.6723), not at the hinge x/c=0.80.
UserFieldFunction zone=field("C0_ForewallProtectionPartition","($$Position[0] < <0.80 m>) ? 1 : 2",new Dimensions());
s.get(MeshManager.class).splitBoundariesByFunction(zone,List.of(target));
fixed.clear();Boundary fore=null;int nativePieces=0;
StringBuilder partition=new StringBuilder("Protection threshold x=0.80m; physical hinge remains x=0.952m.\n");
for(Boundary b:s.getRegionManager().getRegion("Background").getBoundaryManager().getBoundaries())if(b.getBoundaryType() instanceof WallBoundary&&!b.getPresentationName().endsWith("bottom")){
fixed.add(b);if(b.getPresentationName().contains("Hydro_Main.NativeSkin")){nativePieces++;
MinReport lo=s.getReportManager().createReport(MinReport.class);MaxReport hi=s.getReportManager().createReport(MaxReport.class);lo.getParts().setObjects(b);hi.getParts().setObjects(b);lo.setFieldFunction(s.getFieldFunctionManager().getFunction("Position").getComponentFunction(0));hi.setFieldFunction(s.getFieldFunctionManager().getFunction("Position").getComponentFunction(0));
double xmin=lo.getReportMonitorValue(),xmax=hi.getReportMonitorValue();s.getReportManager().removeObjects(lo,hi);partition.append(b.getPresentationName()+" xmin="+xmin+" xmax="+xmax+"\n");
if(xmax<.802&&xmin<.01){if(fore!=null)throw new IllegalStateException("Ambiguous forewall");fore=b;}else if(xmin<.798)throw new IllegalStateException("Unexpected aft partition extent");
}}
if(nativePieces!=2||fixed.size()!=3||fore==null)throw new IllegalStateException("Expected exactly two NativeSkin partitions plus unchanged hinge arc");
target=fore;
List<Boundary> allWalls=new ArrayList<>(fixed);allWalls.addAll(flap);
for(String reportName:List.of("HF_Fx_N","HF_Fz_N","HF_yplus_mean","HF_yplus_max"))((AnalysisReport)s.getReportManager().getReport(reportName)).getParts().setObjects(allWalls);
((AnalysisReport)s.getReportManager().getReport("HF_pabs_fixed")).getParts().setObjects(fixed);
Files.writeString(out.resolve("wall_partition.txt"),partition.toString());
exportNativeWallVertices("partitioned");
'''
s=s[:i]+split+'\n'+s[i:]
s=s.replace('on main NativeSkin','on forewall NativeSkin partition')
s=s.replace('Changed only "+target.getPresentationName()+" to ALWAYS_ACTIVE','Changed only forewall "+target.getPresentationName()+" to ALWAYS_ACTIVE')
s=s.replace('hinge arc and flap boundaries retained.','aft main wall,hinge arc and flap boundaries retained.')
s=s.replace('\\\"protected_layers\\\":36','\\\"protected_layers\\\":36,\\\"protection_x_limit_m\\\":0.80,\\\"native_wall_partition_only\\\":true')
macro=h/'macros/PrepareC0ForewallLayers.java';assert not macro.exists();macro.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for n in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/n,backup/n)
p=h/'tools/night_native.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('allowed={',"allowed={'"+macro.name+"':1,",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_queue.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('ALLOWED={',"ALLOWED={'"+macro.name+"',",1).replace('prefix={',"prefix={'"+macro.name+"':'c0_forewall36_',",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_dashboard.py';t=p.read_text(encoding='utf8').replace('case={',"case={'"+macro.name+"':'C0 — ochrona warstw ograniczona do przedniej części płata',",1);p.write_text(t,encoding='utf8')
for n in ['night_native.py','night_queue.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/n),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text())
job=dict(id='c0_forewall36_audit',macro=macro.name,input=str(h/'cases/SP_C_split0_overset/c0_overlap_band05mm_20261103_003837/SP_C_mesh_ready.sim'),initial_time_s=0,angle_deg=0,approved=True,purpose='1CPU zero-flow-step audit of36protected layers only on main wall x<0.80m, away from hinge. NativeSkin split by existing wall-face position; coordinates and mesh remain unchanged; both no-slip partitions included in force reports. Hinge staysx/c0.80,x0.952m. Native cold assembly on exact zero-step source only. Must pass full mesh identity, zero error/difficult stencil and native-solid containment before any flow proposal.')
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job);cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_localized_forewall_protection_audit',job=job,scientific_approved=False,rationale='All195nativeError6acceptors from whole-wall36 test are inside flap nose,x0.9325..0.9572,z-0.0134..0.05494; none outside cage. Limit protection toforewallx0.80m. Estimated36tangentialwall-cell layers~0.103m gives separation from flap nose x~0.917m; this estimate must be checked natively, not assumed valid.')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+ev['at']+' '+ev['rationale']+'\n')
p=h/'WORK_CURRENT_REVIEW.json';v=json.loads(p.read_text(encoding='utf8'));v['at']=ev['at'];v['next']='Audyt ochrony warstw tylko w przedniej części głównego płata,x<0.80m. Wszystkie195błędnych akceptorów poprzedniej próby leżą wewnątrz klapki przy zawiasie. Nowy podział ściany ma zachować dokładnie te same wierzchołki,warunki no-slip i sumowanie sił.1CPU,bez przepływu.';p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps(ev,indent=2))
