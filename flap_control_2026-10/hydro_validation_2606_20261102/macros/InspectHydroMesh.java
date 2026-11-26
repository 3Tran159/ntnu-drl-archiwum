package macro;
import star.common.*;import star.base.report.*;import star.flow.*;import java.nio.file.*;import java.util.*;
public class InspectHydroMesh extends StarMacro {
String val(Object o,String m){try{return String.valueOf(o.getClass().getMethod(m).invoke(o));}catch(Exception e){return "";}}
String describe(Object o){String a=o.getClass().getName()+" "+o;for(String m:List.of("getSelectedElement","getValue","getSIValue","getDefinition","getVector")){String v=val(o,m);if(!v.isEmpty())a+=" "+m+"="+v;}
 if(o instanceof ScalarProfile){ScalarProfile p=(ScalarProfile)o;try{a+=" method="+p.getMethod().getClass().getName()+" value="+p.getMethod(ConstantScalarProfileMethod.class).getQuantity().getSIValue();}catch(Exception e){a+=" function="+val(p.getMethod(),"getFieldFunction");}}
 if(o instanceof VectorProfile){a+=" method="+((VectorProfile)o).getMethod().getClass().getName();}return a;
}
public void execute(){Simulation s=getActiveSimulation();Path r=Paths.get("F:/ntnu/flap_control/hydro_validation_2606_20261102");
try{if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().startsWith(r.resolve("cases")))throw new IllegalStateException("Own case only");
s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
StringBuilder b=new StringBuilder("time="+s.getSolution().getPhysicalTime()+"\n");
b.append("cells="+((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount()+"\n");
for(Continuum c:s.getContinuumManager().getObjects())if(c instanceof PhysicsContinuum){PhysicsContinuum pc=(PhysicsContinuum)c;b.append("CONTINUUM "+pc.getPresentationName()+"\n");for(Object v:pc.getInitialConditions().getObjects())b.append("initial "+describe(v)+"\n");}
for(Region reg:s.getRegionManager().getRegions()){b.append("REGION "+reg.getPresentationName()+"\n");
for(Boundary x:reg.getBoundaryManager().getBoundaries()){
b.append("BOUNDARY "+x.getPresentationName()+" type="+x.getBoundaryType()+"\n");
for(Object v:x.getConditions().getObjects())b.append("condition "+describe(v)+"\n");
for(Object v:x.getValues().getObjects())b.append("value "+describe(v)+"\n");
for(int j=0;j<3;j++){MinReport mi=s.getReportManager().createReport(MinReport.class);MaxReport ma=s.getReportManager().createReport(MaxReport.class);mi.getParts().setObjects(x);ma.getParts().setObjects(x);mi.setFieldFunction(s.getFieldFunctionManager().getFunction("Position").getComponentFunction(j));ma.setFieldFunction(mi.getFieldFunction());b.append("bounds "+j+" "+mi.getReportMonitorValue()+" "+ma.getReportMonitorValue()+"\n");s.getReportManager().removeObjects(mi,ma);}
}}
Files.writeString(r.resolve("audit/source_case_detailed.txt"),b.toString());s.println("SOURCE_AUDIT_COMPLETE_NO_STEPS_NO_SAVE");
}catch(Exception e){throw new RuntimeException(e);}}}
