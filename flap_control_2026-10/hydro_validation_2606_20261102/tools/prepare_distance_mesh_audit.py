from pathlib import Path
import subprocess,json,datetime,py_compile,shutil,hashlib
h=Path(__file__).resolve().parents[1]
source=h/'cases/SP_C_split0_overset/c0_overlap_audit_20261103_002030/audit_error.sim'
digest=hashlib.file_digest(source.open('rb'),'sha256').hexdigest()
s=(h/'macros/FinalizeC0MeshAudit.java').read_text(encoding='utf8')
s=s.replace('class FinalizeC0MeshAudit','class FinalizeC0DistanceMeshAudit').replace('c0_overlap_audit_"+id','c0_overlap_distance_audit_"+id')
s=s.replace('cases/SP_C_split0_overset/c0_overlap1mm_20261103_001516/SP_C_repair_error_20261103_001516.sim','cases/SP_C_split0_overset/c0_overlap_audit_20261103_002030/audit_error.sim')
s=s.replace('17efa0187726bc27cfd6370e15d92fa70a5d5270b017e732c04259c991fe77ec',digest)
s=s.replace('s.getSolution().initializeSolution();','for(Interface iface:s.getInterfaceManager().getObjects())if(iface instanceof IndirectRegionInterface)((IndirectRegionInterface)iface).getConditions().get(OversetMeshInterpolationOption.class).setSelected(OversetMeshInterpolationOption.Type.DISTANCE);\ns.getSolution().initializeSolution();')
s=s.replace('Files.copy(input.getParent().resolve("normalization.json"),','Files.copy(root.resolve("cases/SP_C_split0_overset/normalization.json"),')
s=s.replace('Read-back and field-storage activation only,','Same saved overlap-refined mesh; interpolation changed LINEARQUASI2D to DISTANCE to resolve one difficult stencil; comparison reference is preserved C0 DISTANCE control. Read-back and field-storage activation,')
s=s.replace('if(total!=expected||active<1||acceptor<1||errors!=0||fallback!=0)','if(methods.size()!=1||methods.getOrDefault(0,0L)!=acceptor)throw new IllegalStateException("Expected DISTANCE for every acceptor");\nif(total!=expected||active<1||acceptor<1||errors!=0||fallback!=0)')
p=h/'macros/FinalizeC0DistanceMeshAudit.java';p.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(p)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for name in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/name,backup/name)
p=h/'tools/night_native.py';s=p.read_text(encoding='utf8').replace("'FinalizeC0MeshAudit.java':1}","'FinalizeC0MeshAudit.java':1,'FinalizeC0DistanceMeshAudit.java':1}");assert "'FinalizeC0DistanceMeshAudit.java':1" in s;p.write_text(s,encoding='utf8')
p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8').replace("'FinalizeC0MeshAudit.java'}","'FinalizeC0MeshAudit.java','FinalizeC0DistanceMeshAudit.java'}").replace("'FinalizeC0MeshAudit.java':'c0_overlap_audit_',","'FinalizeC0DistanceMeshAudit.java':'c0_overlap_distance_audit_','FinalizeC0MeshAudit.java':'c0_overlap_audit_',");p.write_text(s,encoding='utf8')
p=h/'tools/night_dashboard.py';s=p.read_text(encoding='utf8').replace("case={'FinalizeC0MeshAudit.java'","case={'FinalizeC0DistanceMeshAudit.java':'C0 — audyt tej samej siatki z interpolacją odległościową, bez przepływu','FinalizeC0MeshAudit.java'");p.write_text(s,encoding='utf8')
for name in ['night_queue.py','night_native.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/name),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text(encoding='utf8'))
job=dict(id='c0_overlap_distance_mesh_audit',macro='FinalizeC0DistanceMeshAudit.java',input=str(source),initial_time_s=0,angle_deg=0,approved=True,purpose='Same generated mesh, no remeshing or flow; change interpolation to DISTANCE and require all3096 acceptors method0, zero errors/fallback. Compare later with saved DISTANCE control, not attribute mixed-method difference to mesh alone.')
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job)
cfg.setdefault('release_failure_hold',{})['c0_overlap_mesh_finalize']='Strict audit rejected one type4 stencil at x.7586638452,z-.0351466178; cell quality.572, ratio1.166, nativeerror0. Resolve by documented DISTANCE method on same mesh then re-audit.'
cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_mesh_audit_decision',job=job,input_sha256=digest,background_identity_pass=True,linear_quasi2D_difficult_cells=1,new_max_size_ratio=4.695452489441969,scientific_gate=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+ev['at']+' Full overlap mesh audit:424982 cells, negative/unclosed0, OversetError0 but1 type4 difficult interpolation cell; strict gate rejected it. Background304810 cells identical (max center error2.85e-14m). Max size ratio4.695 vsold9.212. Next: same mesh with DISTANCE, no remesh/no flow. Reference for future mesh comparison is saved DISTANCE control.\n')
print(json.dumps(ev,indent=2))
