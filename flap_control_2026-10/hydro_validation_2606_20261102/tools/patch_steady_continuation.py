from pathlib import Path
import json,shutil,datetime
h=Path(__file__).resolve().parents[1];m=h/'macros/InitializeHydroControl.java'
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');shutil.copy2(m,h/'audit'/('InitializeHydroControl_before_steady_resume_'+stamp+'.java'))
s=m.read_text(encoding='utf8')
s=s.replace('String variant;Map<Region,Motion>', 'String variant;boolean steadyResume=false;Map<Region,Motion>')
s=s.replace('if(savedMotions.isEmpty())throw new IllegalStateException("SP_C prescribed motion not found");', '''if(savedMotions.isEmpty()&&steadyResume){
RotatingMotion found=null;for(Motion m:s.get(MotionManager.class).getObjects())if(m instanceof RotatingMotion){if(found!=null)throw new IllegalStateException("Ambiguous stored rotation");found=(RotatingMotion)m;}
if(found==null)throw new IllegalStateException("Stored rotation missing from steady checkpoint");
String law=((RotationAngle)found.getRotationSpecification()).getRotationAngle().getDefinition();if(!law.matches("<[+-]?[0-9.]+ deg>"))throw new IllegalStateException("Constant pose required");
savedMotions.put(s.getRegionManager().getRegion("FlapOverset"),found);
}
if(savedMotions.isEmpty())throw new IllegalStateException("SP_C prescribed motion not found");''')
old='suspendMotionForSteady();pc.disableModel(pc.getModelManager().getModel(ImplicitUnsteadyModel.class));pc.enable(SteadyModel.class);s.getSolution().clearSolution(Solution.Clear.History);'
new='''steadyResume=input.getFileName().toString().equals("steady_checkpoint.sim");
if(steadyResume){if(!Files.readString(base.resolve("initialization_status.json")).contains("steady_initialization_incomplete"))throw new IllegalStateException("Only incomplete steady initializer may be continued");if(pc.getModelManager().getModel(SteadyModel.class)==null)throw new IllegalStateException("Steady checkpoint expected");}
suspendMotionForSteady();if(!steadyResume){pc.disableModel(pc.getModelManager().getModel(ImplicitUnsteadyModel.class));pc.enable(SteadyModel.class);s.getSolution().clearSolution(Solution.Clear.History);}
Files.writeString(out.resolve("resume_mode.json"),"{\\"continuing_steady_fields_and_history\\":"+steadyResume+",\\"input\\":\\""+input.toString().replace("\\\\","/")+"\\",\\"training_approved\\":false}");'''
assert old in s;s=s.replace(old,new)
# true external mass; overset interface boundary flux is not external domain mass
s=s.replace('for(Region r:regions)boundary.addAll(r.getBoundaryManager().getBoundaries());','for(Region r:regions)for(Boundary b:r.getBoundaryManager().getBoundaries())if(b.getBoundaryType() instanceof InletBoundary||b.getBoundaryType() instanceof PressureBoundary)boundary.add(b);')
s=s.replace('String norm=Files.readString(base.resolve("normalization.json"));','Path normPath=base.resolve("normalization.json");if(!Files.exists(normPath)&&steadyResume)normPath=base.getParent().resolve("normalization.json");String norm=Files.readString(normPath);Files.copy(normPath,out.resolve("normalization.json"));')
s=s.replace('Files.copy(base.resolve("normalization.json"),out.resolve("normalization.json"));note(', 'note(')
# make monitor record unambiguous remaining steps vs already existing steady history
s=s.replace('Numerical steady initialization; no physical timestep; preserve source and mesh','Numerical steady initialization/continuation; CSV iterations are additional iterations; preserve source and mesh')
# audit wall pressure and all boundaries, mass and area-independent report selections; export at end
old='checkPose("steady_completed");captureFields("steady_completed");s.saveState'
new='''checkPose("steady_completed");captureFields("steady_completed");
StringBuilder audit=new StringBuilder();for(Region r:regions){audit.append(r.getPresentationName()+" motion="+r.getValues().get(MotionSpecification.class).getMotion()+"\\n");for(Boundary b:r.getBoundaryManager().getBoundaries())audit.append("  "+b.getPresentationName()+" type="+b.getBoundaryType()+"\\n");}
for(Report report:s.getReportManager().getObjects())if(report.getPresentationName().startsWith("HF_")&&report instanceof AnalysisReport)audit.append(report.getPresentationName()+" parts="+((AnalysisReport)report).getParts().getObjects()+" representation="+report.getRepresentation()+"\\n");
Files.writeString(out.resolve("boundary_report_audit.txt"),audit.toString());
for(String group:List.of("fixed","flap")){List<Boundary> parts=group.equals("fixed")?fixed:flap;if(!parts.isEmpty()){XyzInternalTable tab=s.getTableManager().createTable(XyzInternalTable.class);tab.getParts().setObjects(parts);tab.setExtractVertexData(false);tab.setFieldFunctions(List.of(s.getFieldFunctionManager().getFunction("AbsolutePressure"),s.getFieldFunctionManager().getFunction("Pressure"),s.getFieldFunctionManager().getFunction("WallYplus")));tab.extract();tab.export(out.resolve("wall_"+group+".csv").toString());}}
s.saveState'''
assert old in s;s=s.replace(old,new)
m.write_text(s,encoding='utf8')
launcher=h/'tools/native_launch.py';t=launcher.read_text(encoding='utf8')
# RunHydroStatic allows verified incomplete steady initializer in its own working tree; no restart from initial.
p=h/'macros/RunHydroStatic.java';u=p.read_text(encoding='utf8');print(u)
print('initializer patched',str(m))
