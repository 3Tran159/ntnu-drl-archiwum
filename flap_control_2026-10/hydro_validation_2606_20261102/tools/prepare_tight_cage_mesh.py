from pathlib import Path
import json,hashlib,datetime,subprocess,shutil,py_compile
h=Path(__file__).resolve().parents[1]
assert not json.loads((h/'NIGHT_QUEUE_STATE.json').read_text()).get('active')
g=json.loads((h/'geometry/c0_tight_cage_v1/geometry_screen.json').read_text())
assert g['native_main_screened'] and g['native_flap_screened'] and g['minimum_main_clearance_m']>.001 and g['minimum_flap_outer_clearance_m']>.001
for n,v in g['physical_geometry_sha256'].items():assert hashlib.sha256((h/'geometry/gap_002500um'/n).read_bytes()).hexdigest()==v
s=(h/'macros/PrepareC0OverlapBand.java').read_text()
s=s.replace('class PrepareC0OverlapBand','class PrepareC0TightCage').replace('c0_overlap_band05mm_','c0_tight_cage_v1_')
# Preserve the same source-mesh controls. Only the numerical outer cage is replaced.
needle='volume(a,name+"_hinge",new double[]{xh-.045,-.1,zh-.045},new double[]{xh+.045,.1,zh+.045},.00035,base);'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
if(inner){volume(a,"C0 overlap resolution 1mm",new double[]{.70,-.1,-.10},new double[]{.955,.1,.15},.001,base);volume(a,"C0 inner overlap band 0p5mm",new double[]{.74,-.1,-.08},new double[]{.955,.1,.13},.0005,base);}
''')
start=s.index('MeshOperationPart bgp=(MeshOperationPart)')
end=s.index('bg=exactExtrude(bgp,bg,"Background",false);',start)
s=s[:start]+r'''
MeshOperationPart bgp=(MeshOperationPart)s.getGeometryPartManager().getPart("Hydro_Background_fluid");
Set<GeometryPart> beforeImport=new HashSet<>(s.getGeometryPartManager().getLeafParts());
Path cageFile=root.resolve("geometry/c0_tight_cage_v1/Hydro_TightCage.stl");
s.get(PartImportManager.class).importStlParts(List.of(cageFile.toString()),"OneSurfacePerPatch","OnePartPerFile",s.getUnitsManager().getObject("m"),true,1e-8);
List<GeometryPart> added=new ArrayList<>();for(GeometryPart p:s.getGeometryPartManager().getLeafParts())if(!beforeImport.contains(p))added.add(p);
if(added.size()!=1||!(added.get(0) instanceof MeshPart))throw new IllegalStateException("Exactly one numerical cage expected");
MeshPart cage=(MeshPart)added.get(0);cage.setPresentationName("Hydro_TightCage");
MeshPart physicalFlap=(MeshPart)s.getGeometryPartManager().getPart("Hydro_Flap");
MeshOperationPart ovp=subtract(cage,List.of(physicalFlap),"Hydro_TightOverset");
PhysicsContinuum pc=ov.getPhysicsContinuum();
Region replacement=region(ovp,"TightOverset source",true);replacement.setPhysicsContinuum(pc);
List<Boundary> oldWalls=new ArrayList<>(ov.getBoundaryManager().getBoundaries());flap.removeAll(oldWalls);fixed.removeAll(oldWalls);regions.remove(ov);s.getRegionManager().removeRegions(List.of(ov));ov=replacement;
if(s.getSimulationIterator().getCurrentIteration()!=0)throw new IllegalStateException("Never remesh a progressed solution");
Files.copy(root.resolve("geometry/c0_tight_cage_v1/geometry_screen.json"),out.resolve("cage_geometry_screen.json"));
Files.writeString(out.resolve("numerical_change.txt"),"Numerical outer cage only: front arc radius0.03635113219921941m centered at original hinge, then aft expansion. Original Hydro_Flap/Hydro_Main physical parts,2.5mm gap,span,physics,background source mesh and controls unchanged. New Overset source mesh uses the same base/prism/hinge/overlap-band targets as c0_overlap_band05mm. Strict DISTANCE/flux/global/close-proximity controls retained. Exact original pre-flow source; no progressed checkpoint reset. Source and before/after fields are not hydrodynamic results.\n");
note("Generating only replacement Overset directed source mesh in tight numerical cage");
directed(ovp,"Tight Overset directed mesh",true);
''' + s[end:]
helper=(h/'macros/PrepareC0ForewallCoverage.java').read_text()
a=helper.index('void exportNativeWallVertices(');b=helper.index('public void execute()',a)
s=s.replace('public void execute()',helper[a:b]+'\npublic void execute()',1)
s=s.replace('auditFull("mesh",total);scene();','auditFull("mesh",total);exportNativeWallVertices("mesh");scene();')
s=s.replace('if(Files.exists(out))throw new IllegalStateException("Unique output required");','if(s.getSimulationIterator().getCurrentIteration()!=0)throw new IllegalStateException("Zero-iteration source required");if(Files.exists(out))throw new IllegalStateException("Unique output required");')
s=s.replace('\\"background_identity_pending\\":true','\\"background_identity_pending\\":true,\\"tight_cage_v1\\":true')
macro=h/'macros/PrepareC0TightCage.java';assert not macro.exists();macro.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for n in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/n,backup/n)
p=h/'tools/night_native.py';t=p.read_text();assert macro.name not in t;t=t.replace('allowed={',"allowed={'"+macro.name+"':8,",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_queue.py';t=p.read_text();assert macro.name not in t;t=t.replace('ALLOWED={',"ALLOWED={'"+macro.name+"',",1).replace('prefix={',"prefix={'"+macro.name+"':'c0_tight_cage_v1_',",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_dashboard.py';t=p.read_text(encoding='utf8').replace('case={',"case={'"+macro.name+"':'C0 — siatka z obszarem Overset ograniczonym do klapki',",1);p.write_text(t,encoding='utf8')
for n in ['night_native.py','night_queue.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/n),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text())
source=h/'cases/SP_C_split0_overset/SP_C_build_error_20261102_191807.sim'
job=dict(id='c0_tight_cage_v1_mesh_audit',macro=macro.name,input=str(source),initial_time_s=0,angle_deg=0,approved=True,purpose='8CPU mesh-only diagnostic. Replace numerical Overset outer cage; physical foil/flap parts and gap unchanged. Keep exact background source mesh and all previous numerical controls. Require zero-iteration source,positive volumes,zero donor/errors,full exported mesh and background identity before any flow. No nonzero angles, no solved checkpoint reset.',input_sha256=hashlib.file_digest(source.open('rb'),'sha256').hexdigest())
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job);cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_tight_cage_mesh_audit',job=job,geometry_screen=str(h/'geometry/c0_tight_cage_v1/geometry_screen.json'),minimum_main_clearance_m=g['minimum_main_clearance_m'],minimum_flap_clearance_m=g['minimum_flap_outer_clearance_m'],scientific_approved=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+ev['at']+' Tight-cage mesh-only audit: physical geometry unchanged; full native mesh checks required; all flow/angles remain gated.\n')
print(json.dumps(ev,indent=2))
