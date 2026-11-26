import java.nio.file.*;
import java.util.*;
import star.base.neo.*;
import star.base.report.*;
import star.common.*;
import star.vis.*;

public class VerifyNativeVof extends StarMacro {
 public void execute(){
  Simulation s=getActiveSimulation();
  Path out=Paths.get(System.getenv("NATIVE_VOF_DIR"));
  try{
   Region r=s.getRegionManager().getRegions().iterator().next();
   FvRepresentation fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
   long count=fv.getCellCount();
   if(count!=24515||s.getSolution().getPhysicalTime()!=0)throw new IllegalStateException("Native mesh checkpoint identity failed");
   Map<String,Boundary> bounds=new LinkedHashMap<>();
   for(Boundary b:r.getBoundaryManager().getBoundaries())bounds.put(b.getPresentationName(),b);
   List<Boundary> caps=List.of(bounds.get("span_front"),bounds.get("span_back"));
   NeoProperty valid=fv.generateMeshReport(List.of(r));
   if(!valid.getBoolean("success")||s.get(MeshManager.class).checkFaceOrientation(List.of(r))!=0)throw new IllegalStateException("Mesh validity");
   FieldFunctionManager ff=s.getFieldFunctionManager();
   XyzInternalTable t=table(s,fv,"Native mesh cell diagnostics",List.of(r),List.of(ff.getFunction("Volume"),ff.getFunction("CellQuality"),ff.getFunction("FaceValidity")));
   Path cells=out.resolve("MESH_CELLS.csv");
   t.export(cells.toString(),",");
   if(lineCount(cells)!=count)throw new IllegalStateException("Cell table count");
   StringBuilder audit=new StringBuilder("cells="+count+"\n");
   for(int i=0;i<2;i++){
    Boundary b=caps.get(i);
    XyzInternalTable f=table(s,fv,"Native "+b.getPresentationName()+" faces",List.of(b),List.of(ff.getFunction("Position").getComponentFunction(2)));
    Path csv=out.resolve(b.getPresentationName()+".csv");
    f.export(csv.toString(),",");
    long n=lineCount(csv);
    if(n!=count)throw new IllegalStateException("Span face count "+b.getPresentationName()+" "+n);
    String[] expected=Files.readAllLines(csv).get(1).split(",");
    audit.append(b.getPresentationName()+"_faces="+n+"\n"+b.getPresentationName()+"_z_m="+expected[0]+"\n");
   }
   Files.writeString(out.resolve("SPAN_VERIFIED.txt"),audit.toString());
   Path target=out.resolve("Sharp_Sealed_VOF_Native_Quasi2D.sim");
   s.saveState(target.toString());
   try{
    XyzInternalTable edge=table(s,fv,"Native outer boundary faces",List.of(bounds.get("inlet"),bounds.get("outlet"),bounds.get("top"),bounds.get("bottom")),
       List.of(ff.getFunction("Area").getMagnitudeFunction()));
    edge.export(out.resolve("OUTER_FACES.csv").toString(),",");
   }catch(Exception e){s.println("OPTIONAL OUTER TABLE "+e);}
   try{
    scene(s,out,"Mesh 01 - Full domain and free-surface band",caps.get(0),fv,8,-3,10);
    scene(s,out,"Mesh 02 - Hydrofoil and wake refinement",caps.get(0),fv,1.05,.12,1.42);
    s.saveState(target.toString());
   }catch(Exception e){s.println("OPTIONAL SCENE "+e);}
  }catch(Exception e){throw new RuntimeException(e);}
 }
 XyzInternalTable table(Simulation s,FvRepresentation fv,String name,List<? extends NamedObject> parts,List<FieldFunction> fields){
  XyzInternalTable t=s.getTableManager().createTable(XyzInternalTable.class);t.setPresentationName(name);
  t.getParts().setObjects(parts);t.setRepresentation(fv);t.setFieldFunctions(fields);t.setExtractVertexData(false);t.extract();return t;
 }
 long lineCount(Path p)throws Exception{try(var lines=Files.lines(p)){return lines.count()-1;}}
 DoubleVector v(double x,double y,double z){return new DoubleVector(new double[]{x,y,z});}
 void scene(Simulation s,Path out,String name,Boundary cap,FvRepresentation fv,double x,double y,double scale){
  Scene sc=s.getSceneManager().createScene(name);sc.setPresentationName(name);sc.initializeAndWait();
  PartDisplayer p=sc.getDisplayerManager().createPartDisplayer("Span face and mesh");
  p.getInputParts().setObjects(cap);p.setRepresentation(fv);p.setMesh(true);p.setOutline(true);
  sc.getCurrentView().setInput(v(x,y,0),v(x,y,5),v(0,1,0),scale,1,s.getCoordinateSystemManager().getLabCoordinateSystem(),false);
  sc.printAndWait(out.resolve(name.startsWith("Mesh 01")?"NATIVE_VOF_DOMAIN.png":"NATIVE_VOF_FOIL_WAKE.png").toString(),1,1440,810);
 }
}

