from pathlib import Path
h=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102')
t=(h/'macros/RepairExtrudedMesh.java').read_text(encoding='utf8')
t=t[:t.index('public void execute()')].replace('class RepairExtrudedMesh','class FixMeshOrientation')
t+='''public void execute(){s=getActiveSimulation();variant="SP_B";out=root.resolve("cases/SP_B_split0_fixed");String id=System.getenv("NTNU_HYDRO_RUN_ID");try{
Path input=Paths.get(s.getSessionPath()).toAbsolutePath().normalize();if(!input.startsWith(out)||!input.getFileName().toString().startsWith("SP_B_extrusion_error_"))throw new IllegalStateException("Owned extruded diagnostic only");guard();if(Files.exists(out.resolve("SP_B_mesh_ready.sim")))throw new IllegalStateException("Preserve working mesh");
Region r=s.getRegionManager().getRegion("Background");regions.add(r);for(Boundary b:r.getBoundaryManager().getBoundaries()){if(b.getPresentationName().contains("Hydro_Main"))fixed.add(b);if(b.getPresentationName().contains("Hydro_Flap"))flap.add(b);}rebindReports();
MeshManager mm=s.get(MeshManager.class);int before=mm.checkFaceOrientation(regions);note("Native face orientation check="+before);mm.repairFaceOrientation(regions);int after=mm.checkFaceOrientation(regions);Files.writeString(out.resolve("face_orientation_"+id+".txt"),"Before="+before+" After="+after+"\\n");
meshAudit();scene();s.saveState(out.resolve("SP_B_mesh_ready.sim").toString());Files.writeString(out.resolve("extrusion_verified.json"),"{\\"method\\":\\"native outward extrusion plus native orientation repair\\",\\"span_min_m\\":0.01,\\"span_max_m\\":0.03,\\"flow_steps\\":0,\\"training_approved\\":false}");note("EXACT_QUASI2D_MESH_READY_NO_FLOW_STEPS");
}catch(Exception e){try{Files.writeString(out.resolve("orientation_error_"+id+".txt"),e.toString());s.saveState(out.resolve("SP_B_orientation_error_"+id+".sim").toString());}catch(Exception ignored){}throw new RuntimeException(e);}}}'''
(h/'macros/FixMeshOrientation.java').write_text(t,encoding='utf8')
p=h/'tools/native_launch.py';l=p.read_text(encoding='utf8')
l=l.replace("'BuildExtrudedHydroMesh.java'}","'BuildExtrudedHydroMesh.java','FixMeshOrientation.java'}")
l=l.replace("macro.name=='RepairExtrudedMesh.java'","macro.name in {'RepairExtrudedMesh.java','FixMeshOrientation.java'}")
p.write_text(l,encoding='utf8')
print('Bounded native orientation repair compiled by launch; no deletion of cells')
