from pathlib import Path
import subprocess,shutil,datetime
h=Path(__file__).resolve().parents[1];p=h/'macros/InspectHydroComparison.java';s=p.read_text(encoding='utf8')
assert 'void setupAudit(' not in s
backup=h/'runs/macro_source_archive'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S')/p.name;backup.parent.mkdir(parents=True);shutil.copy2(p,backup)
s=s.replace('import star.common.*;','import star.common.*;import star.motion.*;')
method=r"""
void setupAudit(List<Region> regions,List<Boundary> fixed,List<Boundary> flap)throws Exception{
StringBuilder b=new StringBuilder("time="+s.getSolution().getPhysicalTime()+" initialized_flag="+s.getSolution().isInitialized()+"\n");
for(Solver solver:s.getSolverManager().getObjects())b.append("solver="+solver.getPresentationName()+" class="+solver.getClass().getName()+" frozen="+solver.getFrozen()+"\n");
for(SolverStoppingCriterion crit:s.getSolverStoppingCriterionManager().getObjects())if(crit instanceof InnerIterationStoppingCriterion)b.append("inner_iterations="+((InnerIterationStoppingCriterion)crit).getMaximumNumberInnerIterations()+" used="+crit.getIsUsed()+"\n");
ImplicitUnsteadySolver time=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);b.append("dt="+time.getTimeStep().getValue()+" time_discretization="+time.getTimeDiscretizationOption().getSelected()+"\n");
Set<PhysicsContinuum> pcs=new HashSet<>();for(Region r:regions){pcs.add(r.getPhysicsContinuum());b.append("region="+r.getPresentationName()+" motion="+r.getValues().get(MotionSpecification.class).getMotion()+"\n");for(Boundary wall:r.getBoundaryManager().getBoundaries()){b.append("boundary="+wall.getPresentationName()+" type="+wall.getBoundaryType()+"\n");for(Object condition:wall.getConditions().getObjects())if(condition instanceof EnumeratedOption)b.append("  option="+condition.getClass().getSimpleName()+" selected="+((EnumeratedOption)condition).getSelected()+"\n");}}
for(PhysicsContinuum pc:pcs)for(Object model:pc.getModelManager().getObjects())b.append("model="+model.getClass().getName()+"\n");
for(Motion motion:s.get(MotionManager.class).getObjects())if(motion instanceof RotatingMotion){RotatingMotion rot=(RotatingMotion)motion;b.append("rotation="+rot.getPresentationName()+" specification="+rot.getRotationSpecification()+"\n");if(rot.getRotationSpecification() instanceof RotationAngle)b.append("angle_definition="+((RotationAngle)rot.getRotationSpecification()).getRotationAngle().getDefinition()+"\n");b.append("hinge_transformed="+rot.transformInitialCoordinate(new Vector3(.952,.02,.02128173276776986))+"\n");}
List<String> names=new ArrayList<>();for(FieldFunction f:s.getFieldFunctionManager().getObjects()){String n=f.getFunctionName(),low=n.toLowerCase(Locale.ROOT);if(low.contains("velocity")&&(low.contains("mesh")||low.contains("grid")||low.contains("wall")||low.contains("boundary")))names.add(n);}
b.append("motion_velocity_fields="+names+"\n");
for(String name:names){FieldFunction f=ff(name);try{if(f.getTypeOption().getSelected()!=FieldFunctionTypeOption.Type.VECTOR.getValue())continue;MaxReport max=s.getReportManager().createReport(MaxReport.class);max.getParts().setObjects(regions);max.setFieldFunction(f.getMagnitudeFunction());b.append(name+"_max_magnitude="+max.getReportMonitorValue()+"\n");s.getReportManager().removeObjects(max);}catch(Exception e){b.append("OPTIONAL_VELOCITY_FIELD_UNAVAILABLE "+name+" "+e+"\n");}}
Files.writeString(out.resolve("native_setup.txt"),b.toString());
List<FieldFunction> wallFields=new ArrayList<>();for(String n:List.of("Pressure","AbsolutePressure","WallYplus","OversetCellStatus","OversetErrorStatus"))if(s.getFieldFunctionManager().hasFunction(n))wallFields.add(ff(n));
int j=0;for(List<Boundary> parts:List.of(fixed,flap))if(!parts.isEmpty())table((j++==0?"main":"flap")+"_wall_status",parts,s.getRepresentationManager().getObject("Volume Mesh"),wallFields);
}
"""
needle='public void execute(){';assert s.count(needle)==1;s=s.replace(needle,method+'\n'+needle)
needle='Representation volume=s.getRepresentationManager().getObject("Volume Mesh");';assert s.count(needle)==1;s=s.replace(needle,'setupAudit(regions,fixed,flap);\n'+needle)
p.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(p)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert r.returncode==0,r.stderr
print('Compiled read-only audit: solver frozen flags, models, boundary options, actual mesh/wall velocity fields, and wall Overset status. No solver steps, no .sim write.')
