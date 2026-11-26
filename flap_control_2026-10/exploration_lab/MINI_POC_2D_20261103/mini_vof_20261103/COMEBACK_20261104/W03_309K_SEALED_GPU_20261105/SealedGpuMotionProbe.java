package macro;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import star.base.neo.*;
import star.base.report.*;
import star.common.*;
import star.flow.*;
import star.motion.*;

public class SealedGpuMotionProbe extends StarMacro {
 static final double HX=.952, HV=.02128173276777, DT=.0004, Q=.05;
 static final double AMPLITUDE=Math.PI/90;
 Simulation s;
 Region region;
 XyzInternalTable vertices;
 FieldFunctionManager fields;
 Path out;
 boolean w03;
 double start;

 String smooth(String x) {
  String u="min(1,max(0,"+x+"))";
  return "(10*pow("+u+",3)-15*pow("+u+",4)+6*pow("+u+",5))";
 }
 double smooth(double x) {
  double u=Math.max(0,Math.min(1,x));
  return u*u*u*(10+u*(-15+6*u));
 }
 double command(double elapsed) {
  return 2*(-smooth(elapsed/Q)+smooth((elapsed-Q)/Q)+smooth((elapsed-2*Q)/Q)-smooth((elapsed-3*Q)/Q));
 }
 FieldFunction field(String n) {
  FieldFunction f=fields.getFunction(n);
  if(f==null)throw new IllegalStateException("Missing field "+n);
  return f;
 }
 double[] sample(Path file) throws Exception {
  vertices.extract();
  vertices.export(file.toString(),",");
  double radius=0,x=0,v=0,minX=Double.POSITIVE_INFINITY,maxX=Double.NEGATIVE_INFINITY;
  try(BufferedReader reader=Files.newBufferedReader(file)){
   String header=reader.readLine();
   if(header==null||!header.startsWith("\"Position[X]"))throw new IllegalStateException("Unexpected native vertex schema");
   for(String line;(line=reader.readLine())!=null;){
    String[] c=line.split(",");
    double a=Double.parseDouble(c[0]),b=Double.parseDouble(c[1]);
    minX=Math.min(minX,a);maxX=Math.max(maxX,a);
    if(a<1.15)continue;
    double r=Math.hypot(a-HX,b-HV);
    if(r>radius){radius=r;x=a;v=b;}
   }
  }
  if(radius<.23||radius>.25)throw new IllegalStateException("Unexpected foil tip radius "+radius);
  return new double[]{x,v,minX,maxX};
 }
 void status(String phase,int n) throws Exception {
  Files.writeString(out.resolve("STATUS.txt"),phase+"\nsteps="+n+"\ntime_s="+s.getSolution().getPhysicalTime()+"\n");
 }
 public void execute() {
  int n=0;
  try {
   s=getActiveSimulation();
   out=Path.of(System.getenv("FLAP_BENCH_DIR"));
   w03=Boolean.parseBoolean(System.getenv("FLAP_BENCH_W03"));
   int count=Integer.parseInt(System.getenv("FLAP_BENCH_STEPS"));
   if(s.getNumberOfGpgpus()!=1)throw new IllegalStateException("Exactly one GPU required");
   region=s.getRegionManager().getRegion(w03?"fluid":"MINI_water_air");
   List<Boundary> walls=new ArrayList<>();
   for(Boundary b:region.getBoundaryManager().getBoundaries()){
    String name=b.getPresentationName().toLowerCase(Locale.ROOT);
    if(w03?name.equals("hf_012_wall"):(name.contains("main")||name.contains("flap")))walls.add(b);
   }
   if(walls.size()!=(w03?1:2))throw new IllegalStateException("Foil wall groups inconsistent");
   FvRepresentation mesh=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
   long cells=mesh.getCellCount();
   if(cells!=(w03?309441:25617))throw new IllegalStateException("Wrong input mesh: "+cells);
   start=s.getSolution().getPhysicalTime();
   fields=s.getFieldFunctionManager();
   ImplicitUnsteadySolver unsteady=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);
   unsteady.getTimeStep().setValue(DT);
   for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects()){
    if(c instanceof PhysicalTimeStoppingCriterion||c instanceof StepStoppingCriterion)c.setIsUsed(false);
    if(c instanceof InnerIterationStoppingCriterion){
     ((InnerIterationStoppingCriterion)c).setMaximumNumberInnerIterations(12);
     c.setIsUsed(true);
    }
   }
   s.getSimulationIterator().getAutoSave().setEnabled(false);
   UserDefinedVertexMotion motion=s.get(MotionManager.class).createMotion(UserDefinedVertexMotion.class,"Sealed flap x/c 0.80, +/-2 deg");
   region.getValues().get(MotionSpecification.class).setMotion(motion);
   UserDefinedVertexMotionSolver solver=s.getSolverManager().getSolver(UserDefinedVertexMotionSolver.class);
   solver.setIgnoreGridFlux(false);
   solver.setZeroGridFlux(false);
   solver.setUpdateInnerIterations(false);
   field("SavedCoord");
   int vertical=w03?2:1;
   String x="($$SavedCoord[0]-<"+HX+" m>)",v="($$SavedCoord["+vertical+"]-<"+HV+" m>)";
   String t="($Time-<"+start+" s>)",q="/<"+Q+" s>";
   String theta=AMPLITUDE+"*(-"+smooth(t+q)+"+"+smooth("("+t+"-<"+Q+" s>)"+q)+"+"+
    smooth("("+t+"-<"+(2*Q)+" s>)"+q)+"-"+smooth("("+t+"-<"+(3*Q)+" s>)"+q)+")";
   String radius="sqrt(pow("+x+",2)+pow("+v+",2))";
   String angle="("+theta+"*"+smooth(x+"/<.035 m>")+"*"+smooth("(<1.40 m>-"+radius+")/<1.10 m>")+")";
   String dx=x+"*(cos("+angle+")-1)+"+v+"*sin("+angle+")";
   String dv="-"+x+"*sin("+angle+")+"+v+"*(cos("+angle+")-1)";
   UserFieldFunction displacement=fields.createFieldFunction();
   displacement.setFunctionName("BenchSealedFlapDisplacement");
   displacement.getTypeOption().setSelected(FieldFunctionTypeOption.Type.VECTOR);
   Dimensions length=new Dimensions();length.setLength(1);
   displacement.setDimensions(length);
   displacement.setDefinition(w03?"["+dx+",<0 m>,"+dv+"]":"["+dx+","+dv+",<0 m>]");
   region.getConditions().get(MovingVertexOption.class).setSelected(MovingVertexOption.Type.TOTAL_DISPLACEMENT);
   VertexDisplacementProfile profile=region.getValues().get(VertexDisplacementProfile.class);
   profile.setTotalDisplacement(true);
   profile.setMethod(FunctionVectorProfileMethod.class);
   profile.getMethod(FunctionVectorProfileMethod.class).setFieldFunction(displacement);
   FieldFunction pos=field("Position");
   vertices=s.getTableManager().createTable(XyzInternalTable.class);
   vertices.getParts().setObjects(walls);
   vertices.setExtractVertexData(true);
   vertices.setFieldFunctions(List.of(pos.getComponentFunction(0),pos.getComponentFunction(vertical),
                                      pos.getComponentFunction(w03?1:2)));
   double[] tip0=sample(out.resolve("foil_vertices_start.csv"));
   if(Math.abs(tip0[2])>.01||Math.abs(tip0[3]-1.19)>.01)throw new IllegalStateException("Foil chord coordinates mismatch");
   double rx=tip0[0]-HX,rv=tip0[1]-HV;
   MinReport volume=s.getReportManager().createReport(MinReport.class);
   volume.getParts().setObjects(region);volume.setFieldFunction(field("Volume"));
   MinReport quality=s.getReportManager().createReport(MinReport.class);
   quality.getParts().setObjects(region);quality.setFieldFunction(field("CellQuality"));
   ForceReport fx=s.getReportManager().createReport(ForceReport.class);
   fx.getParts().setObjects(walls);fx.getDirection().setComponents(1,0,0);
   ForceReport fv=s.getReportManager().createReport(ForceReport.class);
   fv.getParts().setObjects(walls);fv.getDirection().setComponents(0,w03?0:1,w03?1:0);
   Files.writeString(out.resolve("SETUP.txt"),"cells="+cells+"\ngpu=1\ndt_s="+DT+"\ninner=12\nvertical_axis="+vertical+
                    "\nhinge_x="+HX+"\nhinge_vertical="+HV+"\ninitial_time_s="+start+"\n");
   s.saveState(out.resolve("SEALED_FLAP_CONFIGURED.sim").toString());
   status("FIRST_STEP",0);
   try(BufferedWriter csv=Files.newBufferedWriter(out.resolve("motion_performance.csv"))){
    csv.write("step,time_s,command_deg,measured_deg,fx_N,fvertical_N,min_volume,min_quality,solver_s,full_s\n");
    for(int i=1;i<=count;i++){
     if(Files.exists(out.resolve("STOP_REQUESTED")))break;
     long begin=System.nanoTime();
     s.getSimulationIterator().step(1);
     double sec=(System.nanoTime()-begin)/1e9;
     double t1=s.getSolution().getPhysicalTime();
     n=i;
     if(Math.abs(t1-(start+i*DT))>1e-9)throw new IllegalStateException("Physical time mismatch");
     double[] tip=sample(out.resolve("foil_vertices_latest.csv"));
     double x1=tip[0]-HX,v1=tip[1]-HV;
     double delta=-Math.toDegrees(Math.atan2(rx*v1-rv*x1,rx*x1+rv*v1));
     double target=command(t1-start), minV=volume.getReportMonitorValue(),minQ=quality.getReportMonitorValue();
     double drag=fx.getReportMonitorValue(),lift=fv.getReportMonitorValue();
     if(!Double.isFinite(drag+lift+minV+minQ+delta)||minV<=0||minQ<=0||Math.abs(delta-target)>.04)
      throw new IllegalStateException("Mesh or measured motion gate: command="+target+", measured="+delta+", minV="+minV+", minQ="+minQ);
     csv.write(i+","+t1+","+target+","+delta+","+drag+","+lift+","+minV+","+minQ+","+sec+","+
              ((System.nanoTime()-begin)/1e9)+"\n");
     csv.flush();
     status("RUNNING_GPU",i);
    }
   }
   status(n==count?"COMPLETED":"HOLD_REQUESTED",n);
   s.saveState(out.resolve("FINAL.sim").toString());
  }catch(Exception error){
   try{Files.writeString(out.resolve("ERROR.txt"),error.toString());status("HOLD",n);}catch(Exception ignored){}
   throw new RuntimeException(error);
  }
 }
}
