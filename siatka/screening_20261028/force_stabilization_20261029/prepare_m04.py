from pathlib import Path
import shutil,json,hashlib,subprocess,sys
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
out=Q/'M04'
out.mkdir(exist_ok=False)
mesh=(Q/'MeshQ2DM03.java').read_text()
mesh=mesh.replace('MeshQ2DM03','MeshQ2DM04').replace('20261029/M03','20261029/M04')
mesh=mesh.replace('setValue(.0001799);','setValue(.000003);\nauto.getDefaultValues().get(NumPrismLayers.class).setNumLayers(40);')
mesh=mesh.replace('\\"prism_layers\\":15','\\"prism_layers\\":40').replace('0.0001799','0.000003')
mesh=mesh.replace('s.saveState(out.resolve("mesh_before_audit.sim").toString());','s.saveState(out.resolve("mesh_before_audit.sim").toString());\nStarScript audit=new StarScript(s,Paths.get("'+str(R/'AuditQ2DM04.java').replace('\\','/')+'").toFile());audit.play();if(audit.getInterruptedByException())throw new IllegalStateException("Mesh audit macro failed");')
(R/'MeshQ2DM04.java').write_text(mesh)
audit=(Q/'AuditQ2DM03.java').read_text().replace('AuditQ2DM03','AuditQ2DM04').replace('20261029/M03','20261029/M04').replace('"M03"','"M04"')
(R/'AuditQ2DM04.java').write_text(audit)
source=Q/'M03/mesh.sim';copy=out/'input_M03_mesh_copy.sim';shutil.copy2(source,copy)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(copy)==sha(source)
(out/'source_identity.json').write_text(json.dumps({'source':str(source),'sha256':sha(source),'first_layer_m':3e-6,'layers':40,'total_prism_m':.01546,'other_mesh_controls':'M03 unchanged','status':'meshing'},indent=2))
job={'source':str(copy),'macro':str(R/'MeshQ2DM04.java'),'log':str(out/'mesh_build.log'),'np':2,'timeout_s':1800}
(R/'m04_mesh_job.json').write_text(json.dumps(job))
print('M04 prepared from verified M03 mesh; 3 micrometres, 40 layers; 2 CPU workers.')
