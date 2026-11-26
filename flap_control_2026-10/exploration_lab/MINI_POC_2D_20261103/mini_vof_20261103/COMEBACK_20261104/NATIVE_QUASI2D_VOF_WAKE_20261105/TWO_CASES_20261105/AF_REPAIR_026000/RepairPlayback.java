import java.nio.file.*;
import java.util.*;
import star.base.neo.*;
import star.common.*;
import star.post.*;
import star.vis.*;

public class RepairPlayback extends StarMacro {
 final String prefix="AF FIXED ";
 public void execute(){
  Simulation s=getActiveSimulation();
  Path d=Paths.get(System.getenv("AF_REPAIR_DIR"));
  try { repair(s,d); } catch(Exception e){throw new RuntimeException(e);}
 }
 void repair(Simulation s,Path d)throws Exception{
  double time=s.getSolution().getPhysicalTime();
  FvRepresentation fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
  if(Math.abs(time-.026)>1e-9||fv.getCellCount()!=25617)throw new IllegalStateException("Wrong checkpoint");
  Region region=s.getRegionManager().getRegions().iterator().next();
  SolutionHistory h=s.get(SolutionHistoryManager.class).getSolutionHistory("AF - Solution History");
  h.setAutoRecord(false);
  h.setAutoRescan(false);
  h.rescanFile();
  if(h.getNumberOfStates()<2)throw new IllegalStateException("Expected recorded frames");
  PlaneSection section=null;
  List<Boundary> walls=new ArrayList<>();
  for(NamedObject o:h.getInputs().getObjects()){
   if(o instanceof PlaneSection p)section=p;
   else if(o instanceof Boundary b)walls.add(b);
  }
  if(section==null||walls.size()!=2)throw new IllegalStateException("Expected recorded section and two foil walls");
  final PlaneSection plane=section;
  int state=h.getMinStateIndex()+1;
  RecordedSolutionView old=null;
  for(var v:s.get(SolutionViewManager.class).getObjects())
    if(v instanceof RecordedSolutionView q&&q.getPresentationName().equals("AF - Playback"))old=q;
  if(old!=null){
   old.setStateIndex(state);
   for(Scene scene:s.getSceneManager().getScenes())
    if(scene.getPresentationName().startsWith(prefix+"01"))print(scene,d.resolve("BEFORE_GEOMETRY.png"));
   old.setPresentationName("AF - Previous view");
  }
  RecordedSolutionView view=h.createRecordedSolutionView();
  view.setPresentationName("AF - Repaired Playback");
  view.setStateIndex(state);
  Representation rep=view.getRepresentation();
  print(geometry(s,"QA - Live volume mesh walls",walls,fv,false),d.resolve("QA_LIVE_GEOMETRY.png"));
  print(geometry(s,"QA - Fresh recorded walls",walls,rep,false),d.resolve("QA_FRESH_WALLS.png"));
  print(geometry(s,"AF REPAIRED 01 - Foil geometry",List.of(plane),rep,false),d.resolve("AF_GEOMETRY.png"));
  print(scalar(s,"AF REPAIRED 02 - Absolute pressure",plane,rep,ff(s,"AbsolutePressure")),d.resolve("AF_PRESSURE.png"));
  print(scalar(s,"AF REPAIRED 03 - Velocity magnitude",plane,rep,ff(s,"Velocity").getMagnitudeFunction()),d.resolve("AF_SPEED.png"));
  Scene streams=geometry(s,"AF REPAIRED 04 - Streamlines",List.of(plane),rep,false);
  streams.getCurrentView().setInput(v(.6,.02,.01),v(.6,.02,3),v(0,1,0),.54,1,s.getCoordinateSystemManager().getLabCoordinateSystem(),false);
  StreamPart flow=s.getPartManager().createStreamPart();flow.setPresentationName("AF Repaired - Streamlines");
  flow.getInputParts().setObjects(region);flow.setFieldFunction(ff(s,"Velocity"));flow.setMode(SeedMode.LINE);
  flow.getLineSeed().setPoint1(v(-.38,-.38,.01));flow.getLineSeed().setPoint2(v(-.38,.42,.01));flow.getLineSeed().setResolution(51);
  StreamDisplayer sd=streams.getDisplayerManager().createStreamDisplayer("Speed on streamlines");
  sd.getInputParts().setObjects(flow);sd.setRepresentation(rep);sd.setMode(StreamDisplayerMode.LINES);
  sd.setColorMode(StreamColorMode.SCALAR);sd.getScalarDisplayQuantity().setFieldFunction(ff(s,"Velocity").getMagnitudeFunction());
  print(streams,d.resolve("AF_STREAMLINES.png"));
  print(geometry(s,"AF REPAIRED 06 - Mesh",List.of(plane),rep,true),d.resolve("AF_MESH.png"));
  List<Scene> oldScenes=new ArrayList<>();
  for(Scene sc:s.getSceneManager().getScenes())if(sc.getPresentationName().startsWith(prefix)||sc.getPresentationName().startsWith("QA - "))oldScenes.add(sc);
  s.getSceneManager().removeObjects(oldScenes);
  scalar(s,"AF REPAIRED 05 - Water volume fraction",plane,rep,ff(s,"VolumeFractionwater"));
  if(s.getSolution().getPhysicalTime()!=time)throw new IllegalStateException("Flow time changed");
  s.saveState(d.resolve("Sharp_Sealed_VOF_AF_REPAIRED_REVIEW.sim").toString());
  Files.writeString(d.resolve("REPAIRED.txt"),"source_time_s="+time+"\nrecorded_state="+view.getStateName()+"\nframes="+h.getNumberOfStates()+"\n");
 }
 FieldFunction ff(Simulation s,String name){return s.getFieldFunctionManager().getFunction(name);}
 DoubleVector v(double a,double b,double c){return new DoubleVector(new double[]{a,b,c});}
 Scene scene(Simulation s,String name){
  Scene sc=s.getSceneManager().createScene(name);sc.setPresentationName(name);sc.initializeAndWait();
  sc.getCurrentView().setInput(v(.60,.025,.01),v(.60,.025,3),v(0,1,0),.44,1,s.getCoordinateSystemManager().getLabCoordinateSystem(),false);
  return sc;
 }
 Scene geometry(Simulation s,String name,List<? extends NamedObject> parts,Representation rep,boolean mesh){
  Scene sc=scene(s,name);
  PartDisplayer pd=sc.getDisplayerManager().createPartDisplayer("Section outline");
  pd.getInputParts().setObjects(parts);pd.setRepresentation(rep);
  pd.setSurface(false);pd.setOutline(true);pd.setMesh(mesh);
  return sc;
 }
 Scene scalar(Simulation s,String name,PlaneSection plane,Representation rep,FieldFunction f){
  Scene sc=geometry(s,name,List.of(plane),rep,false);
  ScalarDisplayer sd=sc.getDisplayerManager().createScalarDisplayer(f.getPresentationName());
  sd.getInputParts().setObjects(plane);sd.setRepresentation(rep);sd.getScalarDisplayQuantity().setFieldFunction(f);
  return sc;
 }
 void print(Scene sc,Path file){sc.printAndWait(file.toString(),1,1200,680);}
}

