"""Prepare only. Does not register, queue, launch, mesh, or solve."""
from pathlib import Path
import subprocess
h=Path(__file__).resolve().parents[1];s=(h/'macros/RepairOversetExtrusion.java').read_text(encoding='utf8')
s=s.replace('class RepairOversetExtrusion','class PrepareC0OverlapRefinement')
old='out=root.resolve("cases/SP_C_split0_overset");String id=System.getenv("NTNU_HYDRO_RUN_ID");'
new='String id=System.getenv("NTNU_HYDRO_RUN_ID");out=root.resolve("cases/SP_C_split0_overset/c0_overlap1mm_"+id);'
assert old in s;s=s.replace(old,new)
old='if(!input.startsWith(out)||!input.getFileName().toString().startsWith("SP_C_build_error_"))throw new IllegalStateException("Own mesh source only");guard();'
new='if(!input.equals(root.resolve("cases/SP_C_split0_overset/SP_C_build_error_20261102_191807.sim").toAbsolutePath().normalize()))throw new IllegalStateException("Exact preserved uninitialized source mesh required");if(Files.exists(out))throw new IllegalStateException("Unique output required");Files.createDirectories(out);guard();if(Math.abs(s.getSolution().getPhysicalTime())>1e-12)throw new IllegalStateException("Fresh uninitialized mesh source required; never clear existing flow checkpoint");'
assert old in s;s=s.replace(old,new)
old='bg=exactExtrude(bgp,bg,"Background",false);ov=exactExtrude(ovp,ov,"FlapOverset",true);'
new=r'''DirectedMeshOperation dm=(DirectedMeshOperation)s.get(MeshOperationManager.class).getObject("Overset directed mesh");
dm.editDirectedMeshOperation();DirectedAutoSourceMesh sourceMesh=(DirectedAutoSourceMesh)dm.getDirectedSurfaceMeshBaseManager().getObject("Overset directed mesh_polygon_prisms");
double base=sourceMesh.getDefaultValues().get(BaseSize.class).getValue();if(Math.abs(base-.009)>1e-10)throw new IllegalStateException("Unexpected source Overset base size");
volume(sourceMesh,"C0 overlap resolution 1mm",new double[]{.70,-.1,-.10},new double[]{.955,.1,.15},.001,base);
note("Refining only Overset source mesh in fixed-main overlap: 1mm target; physical foil/cage unchanged");sourceMesh.updateAutoSourceMesh();dm.stopEditingDirectedMeshOperation();dm.execute();
Files.writeString(out.resolve("numerical_change.txt"),"Only spatial-resolution change: Overset source mesh volume target1mm for x[.70,.955],z[-.10,.15] m. Existing hinge.35mm finer control retained. Same imported geometry, same cage, same background source mesh/prism settings. Interface uses DISTANCE, matching current distance diagnostic. Fresh uninitialized source t0; no flow checkpoint reset.\n");
bg=exactExtrude(bgp,bg,"Background",false);ov=exactExtrude(ovp,ov,"FlapOverset",true);'''
assert old in s;s=s.replace(old,new)
s=s.replace('OversetMeshInterpolationOption.Type.LINEARQUASI2D','OversetMeshInterpolationOption.Type.DISTANCE').replace('linear_quasi2D_set=','distance_weighted_set=')
base=(h/'macros/C0InnerIterationTest.java').read_text(encoding='utf8');start=base.index('FieldFunction namedField(');end=base.index('public void execute(){',start);methods=base[start:end]
s=s.replace('public void execute(){',methods+'\npublic void execute(){',1)
old='reports((.10619978819242386+.009330092384759108)*.02*1000*9.8100004196167);meshAudit();scene();s.saveState(out.resolve("SP_C_mesh_ready.sim").toString());note("MESH_PREPARED_NO_FLOW_STEPS");'
new='''reports((.10619978819242386+.009330092384759108)*.02*1000*9.8100004196167);meshAudit();long total=((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount();if(total>750000)throw new IllegalStateException("Refined mesh exceeds diagnostic resource cap");for(Interface iface:s.getInterfaceManager().getObjects())if(iface instanceof IndirectRegionInterface)s.getInterfaceManager().initializeInterfaces(List.of(iface));auditFull("mesh",total);scene();if(Math.abs(s.getSolution().getPhysicalTime())>1e-12)throw new IllegalStateException("Mesh preparation unexpectedly advanced time");s.saveState(out.resolve("SP_C_mesh_ready.sim").toString());Files.writeString(out.resolve("status.json"),"{\\\"status\\\":\\\"mesh_connectivity_prepared\\\",\\\"solver_steps\\\":0,\\\"physical_time_s\\\":0,\\\"cells\\\":"+total+",\\\"background_identity_pending\\\":true,\\\"scientific_approved\\\":false,\\\"training_approved\\\":false}");note("MESH_PREPARED_NO_FLOW_STEPS");'''
assert old in s;s=s.replace(old,new)
target=h/'macros/PrepareC0OverlapRefinement.java';target.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(target)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert r.returncode==0,r.stderr
print('Compiled mesh-only candidate; NOT REGISTERED OR QUEUED. Needs current distance-test review before execution. Background identity and cross-body connectivity must be verified before any solve.')
