from pathlib import Path
h=Path(__file__).resolve().parents[1];p=h/'macros/InitializeHydroControl.java';t=p.read_text(encoding='utf8')
t=t.replace('String variant;','String variant;Map<Region,Motion> savedMotions=new LinkedHashMap<>();double[] savedFlapBounds;')
helper='''
double[] flapBounds(){double[] values=new double[6];for(int j=0;j<3;j++){FieldFunction pos=s.getFieldFunctionManager().getFunction("Position").getComponentFunction(j);MinReport lo=s.getReportManager().createReport(MinReport.class);MaxReport hi=s.getReportManager().createReport(MaxReport.class);lo.getParts().setObjects(flap);hi.getParts().setObjects(flap);lo.setFieldFunction(pos);hi.setFieldFunction(pos);values[2*j]=lo.getReportMonitorValue();values[2*j+1]=hi.getReportMonitorValue();s.getReportManager().removeObjects(lo,hi);}return values;}
void checkPose(String stage)throws Exception{if(savedFlapBounds==null)return;double[] current=flapBounds();Files.writeString(out.resolve("pose_bounds_"+stage+".txt"),Arrays.toString(current));for(int k=0;k<6;k++)if(Math.abs(current[k]-savedFlapBounds[k])>1e-8)throw new IllegalStateException("Static mesh pose changed at "+stage+": "+Arrays.toString(current));}
void suspendMotionForSteady()throws Exception{
if(!variant.equals("SP_C"))return;StationaryMotion stationary=null;for(Motion motion:s.get(MotionManager.class).getObjects())if(motion instanceof StationaryMotion)stationary=(StationaryMotion)motion;if(stationary==null)throw new IllegalStateException("Native stationary motion absent");
savedFlapBounds=flapBounds();Files.writeString(out.resolve("pose_bounds_before_suspend.txt"),Arrays.toString(savedFlapBounds));
for(Region r:regions){MotionSpecification spec=r.getValues().get(MotionSpecification.class);Motion motion=spec.getMotion();if(motion instanceof RotatingMotion){String law=((RotationAngle)((RotatingMotion)motion).getRotationSpecification()).getRotationAngle().getDefinition();if(!law.matches("<[+-]?[0-9.]+ deg>"))throw new IllegalStateException("Steady initializer requires constant prescribed angle");savedMotions.put(r,motion);spec.setMotion(stationary);}}
if(savedMotions.isEmpty())throw new IllegalStateException("SP_C prescribed motion not found");note("Temporarily stationary at existing pose for steady initialization; source unchanged");checkPose("after_suspend");
}
void restoreMotionForUnsteady()throws Exception{
if(savedMotions.isEmpty())return;for(Map.Entry<Region,Motion> entry:savedMotions.entrySet())entry.getKey().getValues().get(MotionSpecification.class).setMotion(entry.getValue());
List<Solver> frozen=new ArrayList<>();try{for(Solver solver:s.getSolverManager().getObjects())if(solver instanceof SegregatedFlowSolver||solver.getClass().getName().toLowerCase(Locale.ROOT).contains("turb"))if(!solver.getFrozen()){solver.setFrozen(true);frozen.add(solver);}for(SolverStoppingCriterion criterion:s.getSolverStoppingCriterionManager().getObjects())if(criterion instanceof InnerIterationStoppingCriterion)((InnerIterationStoppingCriterion)criterion).setMaximumNumberInnerIterations(1);s.getSimulationIterator().step(1);checkPose("after_restore_and_frozen_step");}
finally{for(Solver solver:frozen)solver.setFrozen(false);for(SolverStoppingCriterion criterion:s.getSolverStoppingCriterionManager().getObjects())if(criterion instanceof InnerIterationStoppingCriterion)((InnerIterationStoppingCriterion)criterion).setMaximumNumberInnerIterations(15);}
Files.writeString(out.resolve("motion_restored.json"),"{\\"motion_suspended_for_steady\\":true,\\"motion_restored\\":true,\\"mesh_pose_preserved_tolerance_m\\":1e-8,\\"frozen_motion_settle_steps\\":1,\\"training_approved\\":false}");
}
'''
t=t.replace('public void execute()',helper+'public void execute()')
t=t.replace('pc.disableModel(pc.getModelManager().getModel(ImplicitUnsteadyModel.class));','suspendMotionForSteady();pc.disableModel(pc.getModelManager().getModel(ImplicitUnsteadyModel.class));',1)
t=t.replace('s.getSimulationIterator().step(10);iterations=k;','s.getSimulationIterator().step(10);iterations=k;if(k==10)checkPose("first_steady_block");')
t=t.replace('captureFields("steady_completed");','checkPose("steady_completed");captureFields("steady_completed");')
t=t.replace('captureFields("converted_URANS");','restoreMotionForUnsteady();captureFields("converted_URANS");')
p.write_text(t,encoding='utf8');print('Static pose verified before/after temporary motion suspension and restoration')
