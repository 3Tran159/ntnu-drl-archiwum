from pathlib import Path
h=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102')
b=(h/'macros/BuildExtrudedHydroMesh.java').read_text(encoding='utf8')
t=b[:b.index('public void execute()')].replace('class BuildExtrudedHydroMesh','class RepairOversetExtrusion')
t=t.replace('RegionManager.CreateInterfaceMode.BOUNDARY','RegionManager.CreateInterfaceMode.NONE')
start=b.index('if(over){IndirectRegionInterface')
end=b.index('reports((.106199788',start)
interface=b[start:end].replace('if(over){IndirectRegionInterface','{IndirectRegionInterface')
t+='''public void execute(){s=getActiveSimulation();variant="SP_C";out=root.resolve("cases/SP_C_split0_overset");String id=System.getenv("NTNU_HYDRO_RUN_ID");try{
Path input=Paths.get(s.getSessionPath()).toAbsolutePath().normalize();if(!input.startsWith(out)||!input.getFileName().toString().startsWith("SP_C_build_error_"))throw new IllegalStateException("Own mesh source only");guard();if(Files.exists(out.resolve("SP_C_mesh_ready.sim")))throw new IllegalStateException("Preserve checkpoint");
for(Interface in:new ArrayList<>(s.getInterfaceManager().getInterfaces()))s.getInterfaceManager().deleteInterface(in);
for(Region r:new ArrayList<>(s.getRegionManager().getRegions()))if(!List.of("Background","FlapOverset").contains(r.getPresentationName()))s.getRegionManager().removeRegions(List.of(r));
Region bg=s.getRegionManager().getRegion("Background"),ov=s.getRegionManager().getRegion("FlapOverset");regions.add(bg);regions.add(ov);
for(Region r:regions)for(Boundary w:r.getBoundaryManager().getBoundaries()){if(w.getPresentationName().contains("Hydro_Main"))fixed.add(w);if(w.getPresentationName().contains("Hydro_Flap"))flap.add(w);}
MeshOperationPart bgp=(MeshOperationPart)s.getGeometryPartManager().getPart("Hydro_Background_fluid"),ovp=(MeshOperationPart)s.getGeometryPartManager().getPart("Hydro_Overset_fluid");
bg=exactExtrude(bgp,bg,"Background",false);ov=exactExtrude(ovp,ov,"FlapOverset",true);
int before=s.get(MeshManager.class).checkFaceOrientation(regions);s.get(MeshManager.class).repairFaceOrientation(regions);int after=s.get(MeshManager.class).checkFaceOrientation(regions);Files.writeString(out.resolve("face_orientation_fixed.txt"),"Before="+before+" After="+after+"\\n");if(after!=0)throw new IllegalStateException("Orientation repair incomplete");
'''+interface+'''
reports((.10619978819242386+.009330092384759108)*.02*1000*9.8100004196167);meshAudit();scene();s.saveState(out.resolve("SP_C_mesh_ready.sim").toString());note("MESH_PREPARED_NO_FLOW_STEPS");
}catch(Exception e){try{Files.writeString(out.resolve("repair_error_"+id+".txt"),e.toString());s.saveState(out.resolve("SP_C_repair_error_"+id+".sim").toString());}catch(Exception ignored){}throw new RuntimeException(e);}}}
'''
(h/'macros/RepairOversetExtrusion.java').write_text(t,encoding='utf8')
p=h/'macros/BuildExtrudedHydroMesh.java';p.write_text(b.replace('RegionManager.CreateInterfaceMode.BOUNDARY','RegionManager.CreateInterfaceMode.NONE'),encoding='utf8')
p=h/'tools/native_launch.py';l=p.read_text(encoding='utf8')
l=l.replace("'BuildExtrudedHydroMesh.java','FixMeshOrientation.java'}","'BuildExtrudedHydroMesh.java','FixMeshOrientation.java','RepairOversetExtrusion.java'}")
l=l.replace("'FixMeshOrientation.java','BuildExtrudedHydroMesh.java'}","'FixMeshOrientation.java','BuildExtrudedHydroMesh.java','RepairOversetExtrusion.java'}")
p.write_text(l,encoding='utf8')
print('Repair from saved directed meshes; no remeshing; no automatic conformal interfaces')
