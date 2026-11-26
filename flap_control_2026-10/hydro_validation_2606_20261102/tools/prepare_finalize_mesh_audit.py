from pathlib import Path
import subprocess,json,datetime,py_compile,shutil,hashlib
h=Path(__file__).resolve().parents[1]
source=h/'cases/SP_C_split0_overset/c0_overlap1mm_20261103_001516/SP_C_repair_error_20261103_001516.sim'
digest=hashlib.file_digest(source.open('rb'),'sha256').hexdigest()
s=(h/'macros/PrepareC0OverlapRefinement.java').read_text(encoding='utf8');s=s[:s.index('public void execute(){')]
s=s.replace('class PrepareC0OverlapRefinement','class FinalizeC0MeshAudit')
s+=r'''public void execute(){s=getActiveSimulation();variant="SP_C";String id=System.getenv("NTNU_HYDRO_RUN_ID");out=root.resolve("cases/SP_C_split0_overset/c0_overlap_audit_"+id);try{
Path input=Paths.get(s.getSessionPath()).toAbsolutePath().normalize();
if(!input.equals(root.resolve("cases/SP_C_split0_overset/c0_overlap1mm_20261103_001516/SP_C_repair_error_20261103_001516.sim")))throw new IllegalStateException("Exact mesh-only source required");
Files.createDirectories(out);guard();
if(Math.abs(s.getSolution().getPhysicalTime())>1e-12)throw new IllegalStateException("Never initialize a solved flow checkpoint");
java.security.MessageDigest md=java.security.MessageDigest.getInstance("SHA-256");try(InputStream stream=Files.newInputStream(input)){byte[] buffer=new byte[1048576];int n;while((n=stream.read(buffer))!=-1)md.update(buffer,0,n);}
if(!java.util.HexFormat.of().formatHex(md.digest()).equals("__HASH__"))throw new IllegalStateException("Mesh-only source fingerprint changed");
for(Region r:s.getRegionManager().getRegions()){if(!List.of("Background","FlapOverset").contains(r.getPresentationName()))throw new IllegalStateException("Unexpected region");regions.add(r);for(Boundary b:r.getBoundaryManager().getBoundaries()){if(b.getPresentationName().contains("Hydro_Main"))fixed.add(b);if(b.getPresentationName().contains("Hydro_Flap"))flap.add(b);}}
if(fixed.isEmpty()||flap.isEmpty()||regions.size()!=2)throw new IllegalStateException("Expected foil groups absent");
FvRepresentation fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");if(fv.getCellCount()!=424982)throw new IllegalStateException("Source mesh count changed");
s.getSolverManager().getSolver(SegregatedFlowSolver.class).setContinuityInitialization(false);
note("Activate field storage on zero-step mesh with continuity initialization disabled; no solve or remesh");
s.getSolution().initializeSolution();
for(Interface iface:s.getInterfaceManager().getObjects())if(iface instanceof IndirectRegionInterface)s.getInterfaceManager().initializeInterfaces(List.of(iface));
meshAudit();auditFull("mesh",424982);
Files.copy(input.getParent().resolve("normalization.json"),out.resolve("normalization.json"),StandardCopyOption.REPLACE_EXISTING);
Files.writeString(out.resolve("numerical_change.txt"),"Read-back and field-storage activation only, continuity initialization=false; no mesh operations and no solver iterations. Physical time0. Geometry/source mesh preserved. Full Overset fields become available after initialization.");
if(Math.abs(s.getSolution().getPhysicalTime())>1e-12)throw new IllegalStateException("Audit advanced physical time");
scene();s.saveState(out.resolve("SP_C_mesh_ready.sim").toString());
Files.writeString(out.resolve("status.json"),"{\"status\":\"mesh_connectivity_prepared\",\"cells\":424982,\"solver_steps\":0,\"physical_time_s\":0,\"field_storage_initialized\":true,\"background_identity_pending\":true,\"scientific_approved\":false,\"training_approved\":false}");note("MESH_AUDITED_NO_FLOW_STEPS");
}catch(Exception e){try{Files.writeString(out.resolve("error.txt"),e.toString());s.saveState(out.resolve("audit_error.sim").toString());Files.writeString(out.resolve("status.json"),"{\"status\":\"mesh_audit_error\",\"scientific_approved\":false,\"training_approved\":false}");}catch(Exception ignored){}throw new RuntimeException(e);}}}'''
s=s.replace('__HASH__',digest)
p=h/'macros/FinalizeC0MeshAudit.java';p.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(p)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for name in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/name,backup/name)
p=h/'tools/night_native.py';s=p.read_text(encoding='utf8').replace("'PrepareC0OverlapRefinement.java':8}","'PrepareC0OverlapRefinement.java':8,'FinalizeC0MeshAudit.java':1}");assert "'FinalizeC0MeshAudit.java':1" in s;p.write_text(s,encoding='utf8')
p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8').replace("'PrepareC0OverlapRefinement.java'}","'PrepareC0OverlapRefinement.java','FinalizeC0MeshAudit.java'}")
s=s.replace("'PrepareC0OverlapRefinement.java':'c0_overlap1mm_',","'FinalizeC0MeshAudit.java':'c0_overlap_audit_','PrepareC0OverlapRefinement.java':'c0_overlap1mm_',")
s=s.replace("rec['macro'].startswith('Prepare')","rec['macro'].startswith(('Prepare','Finalize'))");p.write_text(s,encoding='utf8')
p=h/'tools/night_dashboard.py';s=p.read_text(encoding='utf8').replace("case={'PrepareC0OverlapRefinement.java'","case={'FinalizeC0MeshAudit.java':'C0 — końcowy audyt zapisanej siatki 424982 komórek, bez rozwiązywania przepływu','PrepareC0OverlapRefinement.java'");p.write_text(s,encoding='utf8')
for name in ['night_queue.py','night_native.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/name),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text(encoding='utf8'))
job=dict(id='c0_overlap_mesh_finalize',macro='FinalizeC0MeshAudit.java',input=str(source),initial_time_s=0,angle_deg=0,approved=True,purpose='Finish audit of already generated mesh: allocate field storage without continuity solve, no remeshing/no timesteps. Overset status before initialization was native unavailable sentinel DBL_MAX.')
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job)
cfg.setdefault('release_failure_hold',{})['c0_overlap1mm_mesh']='Mesh integrity passed; full Overset state unavailable before field initialization. Recover saved mesh copy without remeshing, 1CPU audit.'
cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_audit_recovery',job=job,input_sha256=digest,mesh_cells=424982,min_quality=.05800954773408175,negative_volume=0,unclosed=0,scientific_gate=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+ev['at']+' Overlap mesh generated424982 cells, negative/unclosed0, minQ.0580095. Full Overset audit encountered DBL_MAX unavailable fields before initialization; saved mesh-only error checkpoint. FinalizeC0MeshAudit allocates initial field storage with continuity initialization off, no iterations or mesh operations, then repeats full audit in separate output. Source preserved.\n')
print(json.dumps(ev,indent=2))
