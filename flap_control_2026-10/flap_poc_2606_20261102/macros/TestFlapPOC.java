package macro;
import star.common.*;import star.base.neo.*;import star.base.report.*;import star.flow.*;import star.segregatedflow.*;import star.motion.*;import star.vis.*;import java.nio.file.*;import java.io.*;import java.util.*;
public class TestFlapPOC extends StarMacro {
 Simulation s;Path out=Paths.get("F:/ntnu/flap_control/flap_poc_2606_20261102");Region bg,ov;double xh,zh,x0,z0;
 double number(String txt,String key){java.util.regex.Matcher m=java.util.regex.Pattern.compile("\""+key+"\"\\s*:\\s*([-+0-9.eE]+)").matcher(txt);if(!m.find())throw new IllegalStateException(key);return Double.parseDouble(m.group(1));}
 MinReport min(String name,String... keys){
  FieldFunction f=null;for(String k:keys){try{f=s.getFieldFunctionManager().getFunction(k);}catch(Exception e){}if(f!=null)break;}if(f==null)throw new IllegalStateException(Arrays.toString(keys));
  MinReport r=s.getReportManager().createReport(MinReport.class);r.setPresentationName(name);r.setFieldFunction(f);r.getParts().setObjects(bg,ov);return r;
 }
 AreaAverageReport centroid(String name,int j,List<Boundary> walls){
  AreaAverageReport r=s.getReportManager().createReport(AreaAverageReport.class);r.setPresentationName(name);r.setFieldFunction(s.getFieldFunctionManager().getFunction("Position").getComponentFunction(j));r.getParts().setObjects(walls);return r;
 }
 void frame(Scene scene,int index){scene.printAndWait(out.resolve(String.format(Locale.ROOT,"visualization/frame_%03d.png",index)).toString(),1,1000,600);}
 PartDisplayer dis(Scene scene,String name,Part p,boolean mesh,double[] color){
  PartDisplayer d=scene.getDisplayerManager().createPartDisplayer(name,-1,1);d.getInputParts().setObjects(p);d.setMesh(mesh);d.setSurface(!mesh);d.setOutline(false);d.setDisplayerColor(new DoubleVector(color));return d;
 }
 public void execute(){
  s=getActiveSimulation();
  try{
   if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(out.resolve("FlapPOC_2606_mesh_ready.sim").toAbsolutePath().normalize()))throw new IllegalStateException("Owned POC mesh required");
   if(s.getNumberOfGpgpus()!=0)throw new IllegalStateException("CPU-only POC");
   String cfg=Files.readString(out.resolve("geometry/geometry.json"));xh=number(cfg,"hinge_x_m");zh=number(cfg,"hinge_z_m");
   bg=s.getRegionManager().getRegion("Background");ov=s.getRegionManager().getRegion("FlapOverset");
   List<Boundary> flapwalls=new ArrayList<>(),allwalls=new ArrayList<>();
   for(Region r:Arrays.asList(bg,ov))for(Boundary b:r.getBoundaryManager().getBoundaries())if(b.getBoundaryType() instanceof WallBoundary){allwalls.add(b);if(r==ov)flapwalls.add(b);}
   Motion actualMotion=ov.getValues().get(MotionSpecification.class).getMotion();
   MinReport volume=min("POC minimum volume","Volume","CellVolume"),quality=min("POC minimum quality","CellQuality"),validity=min("POC minimum face validity","FaceValidity");
   SegregatedFlowSolver flow=s.getSolverManager().getSolver(SegregatedFlowSolver.class);
   s.getSolution().initializeSolution();flow.setFrozen(true);

   PlaneSection background=s.getPartManager().createImplicitPart(Arrays.asList(bg),Arrays.asList(0.,1.,0.),Arrays.asList(0.,0.,0.),0,1,new DoubleVector(new double[]{0}));
   background.setPresentationName("Background midspan mesh");
   PlaneSection overset=s.getPartManager().createImplicitPart(Arrays.asList(ov),Arrays.asList(0.,1.,0.),Arrays.asList(0.,0.,0.),0,1,new DoubleVector(new double[]{0}));
   overset.setPresentationName("Moving overset midspan mesh");
   Scene scene=s.getSceneManager().createScene("Flap POC mesh motion");scene.initializeAndWait();
   dis(scene,"Background grid",background,true,new double[]{.35,.4,.45});
   dis(scene,"Moving overset grid",overset,true,new double[]{.95,.35,.1});
   PartDisplayer body=scene.getDisplayerManager().createPartDisplayer("Native foil and flap",-1,1);body.getInputParts().setObjects(allwalls);body.setSurface(true);body.setMesh(false);body.setOutline(true);body.setDisplayerColor(new DoubleVector(new double[]{.1,.4,.75}));
   scene.getCurrentView().setInput(new DoubleVector(new double[]{.67,0,zh}),new DoubleVector(new double[]{.67,-3,zh}),new DoubleVector(new double[]{0,0,1}),.65,1,s.getCoordinateSystemManager().getLabCoordinateSystem(),false);
   double err=0,minV=Double.POSITIVE_INFINITY,minQ=Double.POSITIVE_INFINITY,minF=Double.POSITIVE_INFINITY;
   frame(scene,0);int frames=1;
   try(BufferedWriter w=Files.newBufferedWriter(out.resolve("runs/motion_check.csv"))){
    w.write("step,time_s,command_deg,measured_deg,error_deg,min_volume_m3,min_cell_quality,min_face_validity\n");
    for(int k=1;k<=100;k++){
     s.getSimulationIterator().step(1);double t=s.getSolution().getPhysicalTime();
     Vector3 moved=actualMotion.transformInitialCoordinate(new Vector3(xh+.2,0,zh));
     double command=5*Math.sin(2*Math.PI*t/.2),measured=-Math.toDegrees(Math.atan2(moved.z-zh,moved.x-xh));
     double v=volume.getReportMonitorValue(),q=quality.getReportMonitorValue(),f=validity.getReportMonitorValue();
     err=Math.max(err,Math.abs(measured-command));minV=Math.min(minV,v);minQ=Math.min(minQ,q);minF=Math.min(minF,f);
     w.write(String.format(Locale.ROOT,"%d,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g\n",k,t,command,measured,measured-command,v,q,f));w.flush();
     if(!Double.isFinite(measured)||v<=0||q<=0||Math.abs(measured-command)>.25)throw new IllegalStateException("Motion/mesh check failed at "+t);
     if(k%5==0)frame(scene,frames++);
     if(k%25==0)Files.writeString(out.resolve("audit/test_progress.txt"),"mesh motion "+k+"/100 steps\n");
    }
   }
   flow.setFrozen(false);s.saveState(out.resolve("FlapPOC_2606_motion_passed.sim").toString());
   Files.writeString(out.resolve("audit/motion_pass.json"),String.format(Locale.ROOT,"{\"passed\":true,\"steps\":100,\"frames\":%d,\"max_angle_error_deg\":%.12g,\"min_volume_m3\":%.12g,\"min_quality\":%.12g,\"min_face_validity\":%.12g}",frames,err,minV,minQ,minF));
   Report fx=s.getReportManager().getReport("POC Fx total N"),fz=s.getReportManager().getReport("POC Fz total N"),mh=s.getReportManager().getReport("POC Mh flap Nm");
   try(BufferedWriter w=Files.newBufferedWriter(out.resolve("runs/transient.csv"))){
    w.write("step,time_s,delta_deg,Fx_N,Fz_N,Mh_Nm,min_volume_m3,min_quality\n");
    for(int k=1;k<=30;k++){
     s.getSimulationIterator().step(1);double t=s.getSolution().getPhysicalTime();
     double x=fx.getReportMonitorValue(),z=fz.getReportMonitorValue(),m=mh.getReportMonitorValue(),v=volume.getReportMonitorValue(),q=quality.getReportMonitorValue();
     w.write(String.format(Locale.ROOT,"%d,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g\n",k,t,5*Math.sin(2*Math.PI*t/.2),x,z,m,v,q));w.flush();
     if(!Double.isFinite(x+z+m)||v<=0||q<=0)throw new IllegalStateException("Transient check failed at "+t);
     Files.writeString(out.resolve("audit/test_progress.txt"),"calm transient "+k+"/30 steps\n");
    }
   }
   frame(scene,frames);for(SolverStoppingCriterion stop:s.getSolverStoppingCriterionManager().getObjects())if(stop instanceof PhysicalTimeStoppingCriterion){((PhysicalTimeStoppingCriterion)stop).getMaximumTime().setValue(.4);stop.setIsUsed(true);}s.saveState(out.resolve("FlapPOC_2606_working.sim").toString());
   Files.writeString(out.resolve("audit/transient_pass.json"),"{\"passed\":true,\"steps\":30,\"duration_s\":0.06,\"U_m_s\":1,\"cpu_processes\":4,\"gpu_compute\":false,\"hydrodynamic_validation\":false}");
   s.println("POC_MOTION_AND_TRANSIENT_COMPLETE");
  }catch(Exception e){try{Files.writeString(out.resolve("audit/test_error.txt"),e.toString());s.saveState(out.resolve("FlapPOC_2606_test_error.sim").toString());}catch(Exception ignore){}throw new RuntimeException(e);}
 }
}
