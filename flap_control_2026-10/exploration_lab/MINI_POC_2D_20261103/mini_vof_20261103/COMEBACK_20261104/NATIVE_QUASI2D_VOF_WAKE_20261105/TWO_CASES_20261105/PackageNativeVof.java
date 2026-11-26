import java.nio.file.*;
import java.util.*;
import star.base.neo.*;
import star.base.report.*;
import star.common.*;
import star.meshing.*;
import star.post.*;
import star.sweptmesher.*;
import star.vis.*;
import star.vof.*;

public class PackageNativeVof extends StarMacro {
 public void execute(){
  Simulation s=getActiveSimulation();
  Path out=Paths.get(System.getenv("NATIVE_PACKAGE_DIR"));
  boolean template=out.getFileName().toString().equals("01_REMESH_START");
  try{prepare(s,out,template);}catch(Exception e){throw new RuntimeException(e);}
 }
 void prepare(Simulation s,Path out,boolean template)throws Exception{
  double t=s.getSolution().getPhysicalTime(), expected=template?0:.006;
  long cells=((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount();
  Region r=s.getRegionManager().getRegions().iterator().next();
  if(Math.abs(t-expected)>1e-10||cells!=25617||
     r.getPhysicsContinuum().getModelManager().hasModel(SegregatedVofModel.class)==null||
     !(s.get(MeshOperationManager.class).getObject("01 Native VOF mesh - one span layer") instanceof DirectedMeshOperation))
   throw new IllegalStateException("Unexpected case: t="+t+" cells="+cells);
  SolutionHistoryManager histories=s.get(SolutionHistoryManager.class);
  SolutionViewManager views=s.get(SolutionViewManager.class);
  RecordedSolutionView view=null;
  List<SolutionView> obsoleteViews=new ArrayList<>();
  for(SolutionView candidate:views.getObjects()){
   if(candidate instanceof RecordedSolutionView v){
    if(v.getPresentationName().endsWith("_134919"))view=v;
    else obsoleteViews.add(v);
   }
  }
  if(view==null)throw new IllegalStateException("Current AF view missing");
  SolutionHistory active=view.getSolutionHistory();
  if(template){
   SolutionHistory empty=histories.createForFile(out.resolve("AF_REMESH_START.simh").toString(),false);
   empty.setAutoRecord(false);empty.setAutoRescan(true);
   empty.getRegions().setObjects(r);
   empty.getInputs().setObjects(active.getInputs().getObjects());
   empty.setFunctions(active.getFunctions());
   empty.createSnapshot("AF_initial_0s");
   view.setSolutionHistory(empty);
   active=empty;
  }else{
   if(!Files.isRegularFile(out.resolve(active.getPath().getName())))throw new IllegalStateException("Working history dependency missing");
   active.rescanFile();
  }
  int states=active.getNumberOfStates();
  if(states!=(template?1:3))throw new IllegalStateException("Unexpected frame count "+states);
  active.getStarUpdateStageable().getStarUpdate().setUpdateMode(StarUpdate.TIMESTEP);
  active.getStarUpdateStageable().getStarUpdate().setUpdateFrequency(25);
  active.setAutoRecord(true);active.setAutoRescan(true);
  active.setPresentationName("AF - Solution History");
  view.setPresentationName("AF - Playback");
  view.setStateIndex(active.getMaxStateIndex());
  Representation rep=view.getRepresentation();

  List<Scene> oldScenes=new ArrayList<>();
  Set<String> sceneCodes=new TreeSet<>();
  for(Scene scene:s.getSceneManager().getScenes()){
   String name=scene.getPresentationName();
   if(name.startsWith("Previous mesh")){oldScenes.add(scene);continue;}
   if(name.startsWith("AF FIXED ")){
    sceneCodes.add(name.substring(9,11));
    for(var display:scene.getDisplayerManager().getObjects())
     if(display.getRepresentation() instanceof SolutionRepresentation)display.setRepresentation(rep);
   }
  }
  if(!sceneCodes.containsAll(List.of("01","02","03","04","05","06")))
   throw new IllegalStateException("Missing AF scenes "+sceneCodes);
  s.getSceneManager().removeObjects(oldScenes);
  views.removeSolutionViews(obsoleteViews);
  List<SolutionHistory> old=new ArrayList<>(histories.getSolutionHistories());
  old.remove(active);
  histories.removeSolutionHistories(old);
  if(histories.getSolutionHistories().size()!=1)throw new IllegalStateException("Multiple histories remain");

  long plots=s.getPlotManager().getObjects().stream().filter(plot->plot.getPresentationName().startsWith("AF ")).count();
  ReportMonitor cl=(ReportMonitor)s.getMonitorManager().getObject("AF_CL Monitor");
  ReportMonitor cd=(ReportMonitor)s.getMonitorManager().getObject("AF_CD Monitor");
  if(plots<6||cl.getAllYValues().length!=(template?0:30)||cd.getAllYValues().length!=(template?0:30))
   throw new IllegalStateException("AF plot/monitor state failed: "+plots+" CL="+cl.getAllYValues().length+" CD="+cd.getAllYValues().length);
  Path target=out.resolve(template?"Sharp_Sealed_VOF_REMESH_START.sim":"Sharp_Sealed_VOF_RUN.sim");
  if(Files.exists(target))throw new IllegalStateException("Refuse overwrite "+target);
  s.saveState(target.toString());
  Files.writeString(out.resolve("PACKAGE_RECEIPT.txt"),"physical_time_s="+t+"\ncells="+cells+
    "\nframes="+states+"\nauto_record=true\nrecord_every_steps=25\nhistory="+active.getPath().getName()+
    "\nAF_plots="+plots+"\nAF_scenes="+sceneCodes+"\nAF_CL_samples="+cl.getAllYValues().length+
    "\nAF_CD_samples="+cd.getAllYValues().length+"\nflow_steps_taken=0\n");
 }
}

