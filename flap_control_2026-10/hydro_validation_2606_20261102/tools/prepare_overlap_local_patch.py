from pathlib import Path
import subprocess,json,datetime,py_compile,shutil
h=Path(__file__).resolve().parents[1]
s=(h/'macros/PrepareC0OverlapRefinement.java').read_text(encoding='utf8').replace('class PrepareC0OverlapRefinement','class PrepareC0OverlapPatch').replace('c0_overlap1mm_"+id','c0_overlap_patch05mm_"+id')
line='volume(sourceMesh,"C0 overlap resolution 1mm",new double[]{.70,-.1,-.10},new double[]{.955,.1,.15},.001,base);'
assert line in s;s=s.replace(line,line+'\nvolume(sourceMesh,"C0 local donor stencil patch 0p5mm",new double[]{.752,-.1,-.043},new double[]{.766,.1,-.028},.0005,base);')
s=s.replace('OversetMeshInterpolationOption.Type.LINEARQUASI2D','OversetMeshInterpolationOption.Type.DISTANCE').replace('linear_quasi2D_set=','distance_weighted_set=')
s=s.replace('Interface uses LINEARQUASI2D, matching the original C0 control.','Local patch0.5mm at x[.752,.766],z[-.043,-.028]m surrounds the one difficult stencil from the1mm candidate. Interface DISTANCE matches saved distance control.')
s=s.replace('for(Interface iface:s.getInterfaceManager().getObjects())if(iface instanceof IndirectRegionInterface)s.getInterfaceManager().initializeInterfaces(List.of(iface));auditFull("mesh",total);','s.getSolverManager().getSolver(SegregatedFlowSolver.class).setContinuityInitialization(false);s.getSolution().initializeSolution();for(Interface iface:s.getInterfaceManager().getObjects())if(iface instanceof IndirectRegionInterface)s.getInterfaceManager().initializeInterfaces(List.of(iface));auditFull("mesh",total);')
s=s.replace('if(total!=expected||active<1||acceptor<1||errors!=0||fallback!=0)','if(methods.size()!=1||methods.getOrDefault(0,0L)!=acceptor)throw new IllegalStateException("Expected DISTANCE for every acceptor");\nif(total!=expected||active<1||acceptor<1||errors!=0||fallback!=0)')
s=s.replace(r'\"background_identity_pending\":true',r'\"field_storage_initialized\":true,\"background_identity_pending\":true')
p=h/'macros/PrepareC0OverlapPatch.java';p.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(p)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for name in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/name,backup/name)
p=h/'tools/night_native.py';s=p.read_text(encoding='utf8').replace("'FinalizeC0DistanceMeshAudit.java':1}","'FinalizeC0DistanceMeshAudit.java':1,'PrepareC0OverlapPatch.java':8}");assert "'PrepareC0OverlapPatch.java':8" in s;p.write_text(s,encoding='utf8')
p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8').replace("'FinalizeC0DistanceMeshAudit.java'}","'FinalizeC0DistanceMeshAudit.java','PrepareC0OverlapPatch.java'}").replace("'FinalizeC0DistanceMeshAudit.java':'c0_overlap_distance_audit_',","'PrepareC0OverlapPatch.java':'c0_overlap_patch05mm_','FinalizeC0DistanceMeshAudit.java':'c0_overlap_distance_audit_',");p.write_text(s,encoding='utf8')
p=h/'tools/night_dashboard.py';s=p.read_text(encoding='utf8').replace("case={'FinalizeC0DistanceMeshAudit.java'","case={'PrepareC0OverlapPatch.java':'C0 — lokalna poprawka0,5mm przy jednym trudnym stencilu Overset','FinalizeC0DistanceMeshAudit.java'");p.write_text(s,encoding='utf8')
for name in ['night_queue.py','night_native.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/name),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text(encoding='utf8'))
job=dict(id='c0_overlap_local_patch',macro='PrepareC0OverlapPatch.java',input=str(h/'cases/SP_C_split0_overset/SP_C_build_error_20261102_191807.sim'),initial_time_s=0,angle_deg=0,approved=True,purpose='1mm overlap plus local0.5mm patch x[.752,.766],z[-.043,-.028] around persistent type4 acceptor; same physical geometry/background source. DISTANCE. Zero solver steps; strict full connectivity gate unchanged.')
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job)
cfg.setdefault('release_failure_hold',{})['c0_overlap_distance_mesh_audit']='Same single difficult type4 cell persisted with DISTANCE. Installed2606 field documentation advises local mesh improvement. Approve small local0.5mm patch only; no flow or gate relaxation.'
cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_local_mesh_remedy',job=job,reference='Installed2606 User Guide GUID-E2FC1BB1-3676-4C83-AA10-22E15160F6BC: interpolation types4/5/6 difficult inverse-distance; improve overlap mesh',scientific_gate=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+ev['at']+' DISTANCE audit of1mm overlap still has1 type4 difficult acceptor, so no flow allowed. Small0.5mm patch around x.758664,z-.035147 follows installed2606 guidance. Same background source/geometry. Field storage initialized without continuity iterations before full native audit. All diagnostics and failed checkpoints retained.\n')
print(json.dumps(ev,indent=2))
