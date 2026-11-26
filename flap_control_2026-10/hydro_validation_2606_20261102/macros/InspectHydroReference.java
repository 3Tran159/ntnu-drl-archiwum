package macro;
import star.common.*;import star.base.report.*;import star.flow.*;import java.nio.file.*;import java.util.*;
public class InspectHydroReference extends StarMacro {
 String val(Object o,String method){try{return String.valueOf(o.getClass().getMethod(method).invoke(o));}catch(Exception e){return "";}}
 public void execute(){
  Simulation s=getActiveSimulation();Path out=Paths.get("F:/ntnu/flap_control/hydro_validation_2606_20261102/audit");
  if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(Paths.get("F:/ntnu/flap_control/flap_drl_20261102/01_reference/C01_original_copy.sim")))throw new IllegalStateException("Read-only reference copy required");
  try{
   StringBuilder b=new StringBuilder("time_s="+s.getSolution().getPhysicalTime()+"\n");
   PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getObject("water+air");
   for(Model m:pc.getModelManager().getObjects())b.append("model="+m.getClass().getName()+"\n");
   b.append("reference_pressure_Pa="+pc.getReferenceValues().get(ReferencePressure.class).getSIValue()+"\n");
   b.append("gravity="+pc.getReferenceValues().get(Gravity.class).getVector()+"\n");
   for(Object v:pc.getReferenceValues().getObjects())b.append("reference="+v.getClass().getName()+" "+val(v,"getDefinition")+" "+val(v,"getSIValue")+" "+val(v,"getVector")+"\n");
   Region reg=s.getRegionManager().getRegion("fluid");Boundary wall=reg.getBoundaryManager().getBoundary("HF_012_wall");
   for(String name:new String[]{"Pressure","AbsolutePressure"}){
    FieldFunction ff=null;try{ff=s.getFieldFunctionManager().getFunction(name);}catch(Exception ignore){}
    if(ff==null){b.append("field_missing="+name+"\n");continue;}
    b.append("field="+name+" "+ff.getClass().getName()+"\n");
    if(name.contains("Pressure")){
     for(PartGroupableModelPart part:Arrays.asList(reg,wall)){
      b.append("attempt="+name+" part="+part.getPresentationName()+"\n");Files.writeString(out.resolve("C01_reference_pressure_audit.txt"),b.toString());
      MinReport min=s.getReportManager().createReport(MinReport.class);min.setFieldFunction(ff);min.getParts().setObjects(part);min.setSmooth(false);
      List<FieldFunction> coords=Arrays.asList(s.getFieldFunctionManager().getFunction("Position").getComponentFunction(0),s.getFieldFunctionManager().getFunction("Position").getComponentFunction(1),s.getFieldFunctionManager().getFunction("Position").getComponentFunction(2));
      min.setCollocatedFieldFunctions(coords);min.setFieldFunction(ff);double p=min.getReportMonitorValue();
      b.append("min_"+name+" "+part.getPresentationName()+" value="+p+" xyz="+Arrays.asList(min.getCollocatedValue(coords.get(0)),min.getCollocatedValue(coords.get(1)),min.getCollocatedValue(coords.get(2)))+"\n");
     }
    }
   }
   for(Boundary x:reg.getBoundaryManager().getBoundaries()){
    b.append("boundary="+x.getPresentationName()+" "+x.getBoundaryType()+"\n");
    try{StaticPressureProfile p=x.getValues().get(StaticPressureProfile.class);b.append(" pressure_method="+p.getMethod().getClass().getName()+"\n");}catch(Exception ignore){}
   }
   Files.writeString(out.resolve("C01_reference_pressure_audit.txt"),b.toString());s.println("REFERENCE_PRESSURE_AUDIT_COMPLETE_NO_STEPS_NO_SAVE");
  }catch(Exception e){try{Files.writeString(out.resolve("reference_audit_error.txt"),e.toString());}catch(Exception ignore){}throw new RuntimeException(e);}
 }
}
