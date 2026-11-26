from pathlib import Path
import subprocess
h=Path(__file__).resolve().parents[1];s=(h/'macros/C0InnerIterationTest.java').read_text(encoding='utf8')
s=s.replace('class C0InnerIterationTest','class C0DistanceInterpolationTest').replace('c0_inner40_','c0_distance_')
old='captureFields("before_transient");s.saveState'
change='''for(Interface iface:s.getInterfaceManager().getObjects())if(iface instanceof IndirectRegionInterface){IndirectRegionInterface in=(IndirectRegionInterface)iface;OversetMeshInterpolationOption opt=in.getConditions().get(OversetMeshInterpolationOption.class);int previousOption=opt.getSelected();boolean change=previousOption==OversetMeshInterpolationOption.Type.LINEARQUASI2D.getValue();if(change){opt.setSelected(OversetMeshInterpolationOption.Type.DISTANCE);s.getInterfaceManager().initializeInterfaces(List.of(iface));}else if(previousOption!=OversetMeshInterpolationOption.Type.DISTANCE.getValue())throw new IllegalStateException("Only linear-quasi2D control or existing distance-weighted checkpoint supported");Files.writeString(out.resolve("continuation_mode.txt"),change?"Single change: LINEARQUASI2D -> DISTANCE":"Resume existing DISTANCE solution; no numerical changes");Files.writeString(out.resolve("numerical_change.txt"),"See continuation_mode.txt for actual mode. Same mesh, physical models, dt=0.002, 40 inner iterations. No time/history reset. Diagnostic, not approved data.\\\\n");}
captureFields("before_transient");s.saveState'''
assert old in s;s=s.replace(old,change)
s=s.replace('Diagnostic inner iterations 15 to 40 only:', 'C0 distance-weighted diagnostic or checkpoint continuation; actual mode in continuation_mode.txt; preserve inner40 control:')
s=s.replace('void auditFull(String label,long expected)throws Exception{','void auditFull(String label,long expected)throws Exception{')
s=s.replace('if(total!=expected||active<1||acceptor<1||errors!=0||fallback!=0)', 'if(label.equals("after_first_step")&&methods.getOrDefault(2,0L)>0)throw new IllegalStateException("Distance-weighted option not reflected in native full-plane audit");\nif(total!=expected||active<1||acceptor<1||errors!=0||fallback!=0)')
s=s.replace('try(BufferedWriter w=Files.newBufferedWriter(out.resolve("history.csv"))){', '''UserFieldFunction omegaFloor=field("C0_omega_floor_"+runId,"($OversetCellStatus == 0 && $SpecificDissipationRate <= <1.0001e-10 /s>) ? 1 : 0",new Dimensions());
UserFieldFunction kFloor=field("C0_k_floor_"+runId,"($OversetCellStatus == 0 && $TurbulentKineticEnergy <= <1.0001e-10 J/kg>) ? 1 : 0",new Dimensions());
ElementCountReport omegaCount=count("C0 active omega floor "+runId,omegaFloor,.5,1.5,s.getRepresentationManager().getObject("Volume Mesh"));
ElementCountReport kCount=count("C0 active k floor "+runId,kFloor,.5,1.5,s.getRepresentationManager().getObject("Volume Mesh"));
MaxReport viscosityMax=s.getReportManager().createReport(MaxReport.class);viscosityMax.getParts().setObjects(regions);viscosityMax.setFieldFunction(s.getFieldFunctionManager().getFunction("TurbulentViscosityRatio"));
try(BufferedWriter w=Files.newBufferedWriter(out.resolve("history.csv"))){''')
s=s.replace('overset_error_cells,difficult_interpolation_cells");','overset_error_cells,difficult_interpolation_cells,omega_floor_cells,k_floor_cells,max_turbulent_viscosity_ratio");')
s=s.replace('w.write(","+massRel+","+oe+","+of);','w.write(","+massRel+","+oe+","+of+","+omegaCount.getReportMonitorValue()+","+kCount.getReportMonitorValue()+","+viscosityMax.getReportMonitorValue());')
s=s.replace('auditFull("final",cells);','captureFields("final");auditFull("final",cells);')

s=s.replace('boolean wasInitialized=s.getSolution().isInitialized();if(!wasInitialized){note("Activating saved field storage or initializing fresh singlephase case; retain existing physical time");s.getSolution().initializeSolution();initializedHere=true;t0=s.getSolution().getPhysicalTime();}', 'verifySavedControl(caseDir);')
s=s.replace('for(Interface iface:s.getInterfaceManager().getObjects())if(iface instanceof IndirectRegionInterface){IndirectRegionInterface in=(IndirectRegionInterface)iface;OversetMeshInterpolationOption opt=', 'captureComparison("control_source");for(Interface iface:s.getInterfaceManager().getObjects())if(iface instanceof IndirectRegionInterface){IndirectRegionInterface in=(IndirectRegionInterface)iface;OversetMeshInterpolationOption opt=',1)
s=s.replace('captureFields("final");auditFull("final",cells);','captureFields("final");captureComparison("final");auditFull("final",cells);')
s=s.replace('if(k%window==0){','if(k%window==0){\n captureComparison("step_"+k);')
method=r"""

void verifySavedControl(Path source)throws Exception{
double time=s.getSolution().getPhysicalTime();boolean flag0=s.getSolution().isInitialized();
List<String> lines=Files.readAllLines(source.resolve("history.csv"));String[] header=lines.get(0).split(",");Map<String,Integer> idx=new HashMap<>();for(int k=0;k<header.length;k++)idx.put(header[k],k);
String[] matched=null;for(int i=1;i<lines.size();i++){String[] row=lines.get(i).split(",");if(Math.abs(Double.parseDouble(row[idx.get("time_s")])-time)<1e-9)matched=row;}if(matched==null)throw new IllegalStateException("Saved physical time absent from source history");
StringBuilder result=new StringBuilder("time="+time+" initialized_before_field_access="+flag0+"\n");
for(String[] pair:new String[][]{{"Fx_N","HF_Fx_N"},{"Fz_N","HF_Fz_N"},{"Mh_Nm","HF_Mh_Nm"},{"CL_hydro","HF_CL_hydro"},{"CD","HF_CD"}}){double expected=Double.parseDouble(matched[idx.get(pair[0])]),actual=rv(pair[1]);result.append(pair[0]+" expected="+expected+" loaded="+actual+"\n");if(!Double.isFinite(actual)||Math.abs(actual-expected)>1e-7*Math.max(1,Math.abs(expected)))throw new IllegalStateException("Saved field verification failed for "+pair[0]);}
result.append("initialized_after_field_access="+s.getSolution().isInitialized()+"\ninitializeSolution_called=false\n");Files.writeString(out.resolve("saved_solution_readback.txt"),result.toString());
captureFields("loaded_control");if(Math.abs(s.getSolution().getPhysicalTime()-time)>1e-12)throw new IllegalStateException("Readback advanced physical time");
}

void captureComparison(String label)throws Exception{
Representation rep=s.getRepresentationManager().getObject("Volume Mesh");
List<FieldFunction> fields=new ArrayList<>();for(String name:List.of("Pressure","AbsolutePressure","Volume","CellQuality","WallDistance","TurbulentKineticEnergy","SpecificDissipationRate","TurbulentViscosityRatio","OversetCellStatus","OversetCellType","OversetErrorStatus","OversetInterpolationType","Overset Interpolation Cell Size Ratio"))if(s.getFieldFunctionManager().hasFunction(name))fields.add(s.getFieldFunctionManager().getFunction(name));
for(int axis=0;axis<3;axis++)fields.add(s.getFieldFunctionManager().getFunction("Velocity").getComponentFunction(axis));
for(Region r:regions){XyzInternalTable tab=s.getTableManager().createTable(XyzInternalTable.class);tab.getParts().setObjects(r);tab.setRepresentation(rep);tab.setExtractVertexData(false);tab.setFieldFunctions(fields);tab.extract();tab.export(out.resolve(r.getPresentationName()+"_"+label+"_volume.csv").toString());s.getTableManager().removeObjects(tab);}
StringBuilder force=new StringBuilder("time="+s.getSolution().getPhysicalTime()+"\n");int j=0;
for(List<Boundary> walls:List.of(fixed,flap)){String group=j++==0?"main":"flap";ForceReport f=s.getReportManager().createReport(ForceReport.class);f.setPressureOption(FluidLoadsReportPressureOption.SP_UC);f.getDirection().setComponents(0,0,1);f.getParts().setObjects(walls);f.getReportMonitorValue();force.append(group+"_pressure_force="+f.getPressureValue()+"\n"+group+"_shear_force="+f.getShearValue()+"\n"+group+"_total_force="+f.getValue()+"\n");s.getReportManager().removeObjects(f);
XyzInternalTable tab=s.getTableManager().createTable(XyzInternalTable.class);tab.getParts().setObjects(walls);tab.setRepresentation(rep);tab.setExtractVertexData(false);tab.setFieldFunctions(List.of(s.getFieldFunctionManager().getFunction("Pressure"),s.getFieldFunctionManager().getFunction("AbsolutePressure"),s.getFieldFunctionManager().getFunction("WallYplus")));tab.extract();tab.export(out.resolve(group+"_"+label+"_wall.csv").toString());s.getTableManager().removeObjects(tab);}
Files.writeString(out.resolve("forces_"+label+".txt"),force.toString());
StringBuilder res=new StringBuilder("time="+s.getSolution().getPhysicalTime()+"\n");
for(Monitor mon:s.getMonitorManager().getObjects())if(mon instanceof ResidualMonitor){ResidualMonitor rm=(ResidualMonitor)mon;try{res.append(rm.getPresentationName()+" enabled="+rm.getEnabled()+" normalized="+rm.isNormalized()+" normalization="+rm.getNormalizationType().getClass().getSimpleName()+" factor="+rm.getNormalizationType().getNormalizationFactor()+"\n");}catch(Exception metadataError){res.append("OPTIONAL_METADATA_ERROR "+rm.getPresentationName()+" "+metadataError+"\n");}try{rm.export(out.resolve("residual_"+label+"_"+rm.getPresentationName().replaceAll("[^A-Za-z0-9_-]","_")+".csv").toString());}catch(Exception exportError){res.append("RESIDUAL_EXPORT_INCOMPLETE "+rm.getPresentationName()+" "+exportError+"\n");}}
Files.writeString(out.resolve("residual_normalization_"+label+".txt"),res.toString());
}
"""
s=s.replace('public void execute(){',method+'\npublic void execute(){',1)

s=s.replace('s.getSolution().clearSolutionWithoutMeshReset();initializedHere=true;','throw new IllegalStateException("Original-profile branch prohibited in C0 diagnostic");')
target=h/'macros/C0DistanceInterpolationTest.java';target.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(target)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,r.stderr
print('Prepared and compiled only. Not registered with launcher or queued. Requires review of inner40 control before any execution.')
