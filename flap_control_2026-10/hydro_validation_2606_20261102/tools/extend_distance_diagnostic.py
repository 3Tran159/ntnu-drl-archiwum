from pathlib import Path
import subprocess
h=Path(__file__).resolve().parents[1]
p=h/'tools/prepare_distance_diagnostic.py'
s=p.read_text(encoding='utf8')
assert 'void captureComparison' not in s
extra=r'''
s=s.replace('boolean wasInitialized=s.getSolution().isInitialized();if(!wasInitialized){note("Activating saved field storage or initializing fresh singlephase case; retain existing physical time");s.getSolution().initializeSolution();initializedHere=true;t0=s.getSolution().getPhysicalTime();}', 'if(!s.getSolution().isInitialized())throw new IllegalStateException("Saved control solution must be initialized; no reset allowed");')
s=s.replace('for(Interface iface:s.getInterfaceManager().getObjects())if(iface instanceof IndirectRegionInterface){IndirectRegionInterface in=(IndirectRegionInterface)iface;OversetMeshInterpolationOption opt=', 'captureComparison("control_source");for(Interface iface:s.getInterfaceManager().getObjects())if(iface instanceof IndirectRegionInterface){IndirectRegionInterface in=(IndirectRegionInterface)iface;OversetMeshInterpolationOption opt=',1)
s=s.replace('captureFields("final");auditFull("final",cells);','captureFields("final");captureComparison("final");auditFull("final",cells);')
s=s.replace('if(k%window==0){','if(k%window==0){\n captureComparison("step_"+k);')
method=r"""
void captureComparison(String label)throws Exception{
Representation rep=s.getRepresentationManager().getObject("Volume Mesh");
List<FieldFunction> fields=new ArrayList<>();for(String name:List.of("Pressure","AbsolutePressure","Volume","CellQuality","WallDistance","TurbulentKineticEnergy","SpecificDissipationRate","TurbulentViscosityRatio","OversetCellStatus","OversetCellType","OversetErrorStatus","OversetInterpolationType","Overset Interpolation Cell Size Ratio"))if(s.getFieldFunctionManager().hasFunction(name))fields.add(s.getFieldFunctionManager().getFunction(name));
for(int axis=0;axis<3;axis++)fields.add(s.getFieldFunctionManager().getFunction("Velocity").getComponentFunction(axis));
for(Region r:regions){XyzInternalTable tab=s.getTableManager().createTable(XyzInternalTable.class);tab.getParts().setObjects(r);tab.setRepresentation(rep);tab.setExtractVertexData(false);tab.setFieldFunctions(fields);tab.extract();tab.export(out.resolve(r.getPresentationName()+"_"+label+"_volume.csv").toString());s.getTableManager().removeObjects(tab);}
StringBuilder force=new StringBuilder("time="+s.getSolution().getPhysicalTime()+"\n");int j=0;
for(List<Boundary> walls:List.of(fixed,flap)){String group=j++==0?"main":"flap";ForceReport f=s.getReportManager().createReport(ForceReport.class);f.setPressureOption(FluidLoadsReportPressureOption.SP_UC);f.getDirection().setComponents(0,0,1);f.getParts().setObjects(walls);f.getReportMonitorValue();force.append(group+"_pressure_force="+f.getPressureValue()+"\n"+group+"_shear_force="+f.getShearValue()+"\n"+group+"_total_force="+f.getValue()+"\n");s.getReportManager().removeObjects(f);
XyzInternalTable tab=s.getTableManager().createTable(XyzInternalTable.class);tab.getParts().setObjects(walls);tab.setRepresentation(rep);tab.setExtractVertexData(false);tab.setFieldFunctions(List.of(s.getFieldFunctionManager().getFunction("Pressure"),s.getFieldFunctionManager().getFunction("AbsolutePressure"),s.getFieldFunctionManager().getFunction("WallYplus")));tab.extract();tab.export(out.resolve(group+"_"+label+"_wall.csv").toString());s.getTableManager().removeObjects(tab);}
Files.writeString(out.resolve("forces_"+label+".txt"),force.toString());
}
"""
s=s.replace('public void execute(){',method+'\npublic void execute(){',1)
'''
needle="target=h/'macros/C0DistanceInterpolationTest.java'"
assert needle in s
p.write_text(s.replace(needle,extra+'\n'+needle),encoding='utf8')
run=subprocess.run([r'C:\Users\ThinkPad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',str(p)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
print(run.stdout)
assert run.returncode==0,run.stderr
print('Export added at source, each 25 steps and final. No execution authorized or started by this script.')
