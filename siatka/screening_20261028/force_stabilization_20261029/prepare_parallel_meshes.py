from pathlib import Path
import json,shutil
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
variants=[('M04B',4e-6,38,2.0),('M04C',6e-6,36,2.0),('M05',.0001799,15,2.5)]
for name,h,n,refine in variants:
 out=Q/name;out.mkdir(exist_ok=False)
 source=out/'input_M03_copy.sim';shutil.copy2(Q/'M03/mesh.sim',source)
 code=(Q/'MeshQ2DM03.java').read_text().replace('MeshQ2DM03','MeshQ2D'+name).replace('20261029/M03','20261029/'+name)
 code=code.replace('setValue(.0001799);','setValue('+str(h)+');\nauto.getDefaultValues().get(NumPrismLayers.class).setNumLayers('+str(n)+');')
 code=code.replace('/2.0','/'+str(refine)).replace('"+2.0+','"+'+str(refine)+'+')
 code=code.replace('\\"prism_layers\\":15','\\"prism_layers\\":'+str(n)).replace('0.0001799',str(h))
 code=code.replace('s.saveState(out.resolve("mesh_before_audit.sim").toString());','s.saveState(out.resolve("mesh_before_audit.sim").toString());\nStarScript audit=new StarScript(s,Paths.get("'+str(R/('AuditQ2D'+name+'.java')).replace('\\','/')+'").toFile());audit.play();if(audit.getInterruptedByException())throw new IllegalStateException("Audit failed");')
 (R/('MeshQ2D'+name+'.java')).write_text(code)
 audit=(Q/'AuditQ2DM03.java').read_text().replace('AuditQ2DM03','AuditQ2D'+name).replace('20261029/M03','20261029/'+name).replace('"M03"','"'+name+'"')
 (R/('AuditQ2D'+name+'.java')).write_text(audit)
 job={'source':str(source),'macro':str(R/('MeshQ2D'+name+'.java')),'log':str(out/'mesh_build.log'),'np':2,'timeout_s':1800}
 (R/(name+'_mesh_job.json')).write_text(json.dumps(job))
 (out/'design.json').write_text(json.dumps({'id':name,'reference':'M03','first_layer_m':h,'layers':n,'total_prism_m':.01546,'overall_linear_refinement_vs_M03':refine/2,'purpose':'wall resolution' if name.startswith('M04') else 'mesh sensitivity check of M03'},indent=2))
print(json.dumps([v[0] for v in variants]))
