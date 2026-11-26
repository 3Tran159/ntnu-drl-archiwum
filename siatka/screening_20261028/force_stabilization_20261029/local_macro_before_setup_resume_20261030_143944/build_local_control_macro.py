"""Compile local workflow macros. Does not launch a solver."""
from pathlib import Path
import json,subprocess,hashlib
R=Path(__file__).resolve().parent
s=(R/'CampaignFoilWave.java').read_text()
def rep(a,b):
 global s
 if s.count(a)!=1:raise RuntimeError('Unexpected macro anchor: '+a[:80])
 s=s.replace(a,b)
rep('public class CampaignFoilWave','public class LocalCalmWave')
rep(' private double domainXmin,domainXmax,requestedLambda;',' private double domainXmin,domainXmax,requestedLambda,requestedHeight,sourceTime,activationTime,requestedDt,startupDt,startupDuration,checkpointInterval; private double lastGuardTime=Double.NaN,lastGuardSpeed,lastGuardAlphaMin,lastGuardAlphaMax; private FifthOrderVofWave activeWave; private String mode; private boolean resumeWave;')
rep('   if(s.getNumberOfGpgpus()!=1)throw new IllegalStateException("Exactly one GPU required");','   mode=Objects.requireNonNull(System.getenv("NTNU_MODE"));if(!List.of("calm","wave","wave_setup").contains(mode))throw new IllegalStateException("Unknown local mode");sourceTime=Double.parseDouble(System.getenv("NTNU_SOURCE_TIME"));if(!Double.isFinite(sourceTime)||sourceTime<0||!Double.isFinite(s.getSolution().getPhysicalTime()))throw new IllegalStateException("Invalid source physical time");if(s.getNumberOfGpgpus()!=(mode.equals("wave_setup")?0:1))throw new IllegalStateException("Wrong compute mode");')
rep('Math.abs(s.getSolution().getPhysicalTime())>1e-8','Math.abs(s.getSolution().getPhysicalTime()-sourceTime)>1e-8')
a=s.index('   double requestedHeight=');b=s.index('   Files.writeString(out.resolve("requested_wave_audit.json")',a)
s=s[:a]+'''   requestedHeight=Double.parseDouble(System.getenv("NTNU_WAVE_HEIGHT"));double wavePeriod=0;boolean reinitialized=false;
   String resume=System.getenv().getOrDefault("NTNU_RESUME_WAVE","false");
   if(!resume.equals("true")&&!resume.equals("false"))throw new IllegalStateException("Invalid NTNU_RESUME_WAVE");
   resumeWave=resume.equals("true");activationTime=sourceTime;
   if(resumeWave){
    if(!mode.equals("wave")||sourceTime<=0||!(selectedWave instanceof FifthOrderVofWave))throw new IllegalStateException("Wave resume requires saved active FifthOrder wave");
    activationTime=Double.parseDouble(Objects.requireNonNull(System.getenv("NTNU_WAVE_ACTIVATION_TIME"),"Original activation time required"));
    if(!Double.isFinite(activationTime)||activationTime<0||activationTime>sourceTime)throw new IllegalStateException("Invalid original wave activation time");
    activeWave=(FifthOrderVofWave)selectedWave;
    verifyWaveAndBindings(activeWave);
   }else{
    if(!(selectedWave instanceof FlatVofWave))throw new IllegalStateException("Each new job must start from matching CALM");
    if(mode.equals("calm")){if(requestedHeight!=0)throw new IllegalStateException("C01 height must be zero");}
    else{
     if(sourceTime<=0||!List.of(.25,.5,.75).contains(requestedHeight))throw new IllegalStateException("Settled computed C01 and supported height required");
     VofWaveModel wm=pc.getModelManager().getModel(VofWaveModel.class);wm.setEnableTheoryComparison(true);
     activeWave=wm.getVofWaveManager().createVofWave(FifthOrderVofWave.class,"LocalFullHeightInlet_"+out.getFileName());
     activeWave.getSpecificationOption().setSelected(VofWaveSpecificationOption.Type.WAVE_LENGTH_SPECIFIED);
     activeWave.getVofWaveSpecification().getWaveLength().setValue(requestedLambda);activeWave.getWaterDepth().setValue(24);activeWave.getWaveHeight().setValue(requestedHeight);
     activeWave.getPointOnLevel().setComponents(0,0,2);activeWave.getVerticalDirection().setComponents(0,0,1);activeWave.getAdvancingDirection().setComponents(1,0,0);activeWave.getCurrent().setComponents(18,0,0);activeWave.getWind().setComponents(18,0,0);activeWave.setFirstWaveFront(false);
     Boundary inlet=reg.getBoundaryManager().getBoundary("DOMAIN.inlet");
     inlet.getValues().get(VelocityProfile.class).setMethod(FunctionVectorProfileMethod.class);
     inlet.getValues().get(VelocityProfile.class).getMethod(FunctionVectorProfileMethod.class).setFieldFunction(waveField(activeWave,"Velocity of "));
     VolumeFractionProfile vp=inlet.getValues().get(VolumeFractionProfile.class);vp.setMethod(CompositeNMinus1ArrayProfileMethod.class);
     vp.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).setMethod(FunctionScalarProfileMethod.class);
     vp.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).setFieldFunction(waveField(activeWave,"Volume Fraction of Heavy Fluid of "));
     reg.getValues().get(ForcingVofWaveSpecification.class).setForcingVofWave(activeWave);selectedWave=activeWave;
     verifyWaveAndBindings(activeWave);
    }
   }
   if(activeWave!=null){
    Files.writeString(out.resolve("wave_runtime.csv"),"time_s,step,evaluated_height_m,actual_period_s\\n");waveRuntime(sourceTime,0);
   }
''' + s[b:]
rep('"target_time_s",.020+steps*dt','"target_time_s",sourceTime+startupDuration+steps*dt')
rep('FieldFunction theory=pc.getInitialConditions().get(VolumeFractionProfile.class).getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).getFieldFunction();','FieldFunction theory=activeWave==null?pc.getInitialConditions().get(VolumeFractionProfile.class).getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).getFieldFunction():waveField(activeWave,"Volume Fraction of Heavy Fluid of ");')
rep('   for(AMGLinearSolver amg:List.of(vofAmg,pressureAmg))if(Math.abs(amg.getConvergeTol()-.1)>1e-12||amg.getMaxCycles()!=30||amg.getEpsilon()!=0)throw new IllegalStateException("BaselineAMGsettingsdiffer");',
'   for(AMGLinearSolver amg:List.of(vofAmg,pressureAmg))if(amg.getMaxCycles()!=30||amg.getEpsilon()!=0)throw new IllegalStateException("AMG settings differ");if(Math.abs(vofAmg.getConvergeTol()-.1)>1e-12||Math.abs(pressureAmg.getConvergeTol()-(sourceTime==0?.1:.01))>1e-12)throw new IllegalStateException("AMG tolerance mismatch");')
rep('   guardedStartup(us,vmax,cfl,amin,amax,nativeWater,nativeAir);initialTime=s.getSolution().getPhysicalTime();',
'''   if(mode.equals("wave_setup")){s.saveState(out.resolve("prepared_wave.sim").toString());Files.writeString(out.resolve("prepared_wave_audit.json"),json(Map.of("mode",mode,"time_s",sourceTime,"flow_steps",0,"height_m",requestedHeight,"wavelength_m",requestedLambda,"cells",fv.getCellCount(),"global_reinitialization",false,"height_ramp_s",0)));return;}
   if(sourceTime==0){if(activeWave!=null)throw new IllegalStateException("No wave from zero-time input");guardedStartup(us,vmax,cfl,amin,amax,nativeWater,nativeAir);}initialTime=s.getSolution().getPhysicalTime();''')
rep('     double t=s.getSolution().getPhysicalTime(),v=', '     if(activeWave!=null)waveRuntime(s.getSolution().getPhysicalTime(),step);\n     double t=s.getSolution().getPhysicalTime(),v=')
# Explicit wave flags/zone checks for each prepared geometry.
anchor='   Files.writeString(out.resolve("continuation_identity.json"),'
pos=s.index(anchor)
s=s[:pos]+'''   double zone=Double.parseDouble(System.getenv("NTNU_ZONE"));
   ArrayList<Object> boundaryBindings=new ArrayList<>();
   for(Boundary b:reg.getBoundaryManager().getBoundaries()){
    String f=String.valueOf(b.getConditions().get(VofWaveForcingBoundaryOption.class).getSelectedElement()),d=String.valueOf(b.getConditions().get(VofWaveDampingBoundaryOption.class).getSelectedElement());
    boolean inlet=b.getPresentationName().equals("DOMAIN.inlet"),outletFlag=b.getPresentationName().equals("DOMAIN.outlet");
    if(!f.equals(inlet?"YES":"NO")||!d.equals(outletFlag?"YES":"NO"))throw new IllegalStateException("Forcing/damping flags mismatch");
    boundaryBindings.add(Map.of("boundary",b.getPresentationName(),"forcing",f,"damping",d));
   }
   Files.writeString(out.resolve("inlet_wave_binding.json"),json(Map.of("boundary_bindings",boundaryBindings,"source_calm_time_s",sourceTime,"require_calm_force_settling",true,"global_initialization",false,"forcing_zone_x_m",List.of(domainXmin,domainXmin+zone),"damping_zone_x_m",List.of(domainXmax-zone,domainXmax))));
''' + s[pos:]
# Add actual native vorticity views and field export.
scene='  scalarScene("12 Free-surface close-up - water fraction",mid,ff("VolumeFractionwater"),-5,2,1.2,false,0,1);'
rep(scene,scene+'\n  scalarScene("13 Signed vorticity - foil",mid,ff("VorticityVector").getComponentFunction(1),.6,0,1.2,false,-500,500);scalarScene("14 Signed vorticity - wake",mid,ff("VorticityVector").getComponentFunction(1),2,0,4,false,-50,50);')
rep('fields.add(v.getMagnitudeFunction());tab.setFieldFunctions(fields);','fields.add(v.getMagnitudeFunction());fields.add(ff("VorticityVector").getComponentFunction(1));tab.setFieldFunctions(fields);')
s=s.replace('step%1000==0','step%250==0')
s=s.replace('step==1||step%10==0','step==1||step%5==0')
s=s.replace('boolean trace=upcoming>=.605-1e-9&&upcoming<=.635+1e-9;','boolean trace=false;')
method=''' private void requireClose(double actual,double expected,double tolerance,String name){if(!Double.isFinite(actual)||Math.abs(actual-expected)>tolerance)throw new IllegalStateException("Saved wave mismatch: "+name);}
 private void requireVector(VectorPhysicalQuantity q,double x,double y,double z,String name){DoubleVector v=q.getSIVector();double[] expected={x,y,z};for(int i=0;i<3;i++)requireClose(v.get(i),expected[i],1e-9,name+"["+i+"]");}
 private void verifyWaveAndBindings(FifthOrderVofWave wave){
  if(!List.of(.25,.5,.75).contains(requestedHeight)||wave.getFirstWaveFront()||!String.valueOf(wave.getSpecificationOption().getSelectedElement()).equals("WAVE_LENGTH_SPECIFIED"))throw new IllegalStateException("Unsupported saved wave definition");
  requireClose(wave.getWaveHeight().getValue(),requestedHeight,1e-9,"height");requireClose(wave.getVofWaveSpecification().getWaveLength().getValue(),requestedLambda,1e-9,"wavelength");requireClose(wave.getWaterDepth().getValue(),24,1e-9,"depth");
  requireVector(wave.getPointOnLevel(),0,0,2,"waterline");requireVector(wave.getVerticalDirection(),0,0,1,"vertical");requireVector(wave.getAdvancingDirection(),1,0,0,"direction");requireVector(wave.getCurrent(),18,0,0,"current");requireVector(wave.getWind(),18,0,0,"wind");
  if(!reg.getValues().get(ForcingVofWaveSpecification.class).getForcingVofWave().equals(wave))throw new IllegalStateException("Region forcing wave identity mismatch");
  Boundary inlet=reg.getBoundaryManager().getBoundary("DOMAIN.inlet");VelocityProfile vel=inlet.getValues().get(VelocityProfile.class);VolumeFractionProfile vf=inlet.getValues().get(VolumeFractionProfile.class);
  if(!(vel.getMethod() instanceof FunctionVectorProfileMethod)||!(vf.getMethod() instanceof CompositeNMinus1ArrayProfileMethod))throw new IllegalStateException("Saved inlet profile methods mismatch");
  ScalarProfile water=vf.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0);
  if(!(water.getMethod() instanceof FunctionScalarProfileMethod)||!vel.getMethod(FunctionVectorProfileMethod.class).getFieldFunction().equals(waveField(wave,"Velocity of "))||!water.getMethod(FunctionScalarProfileMethod.class).getFieldFunction().equals(waveField(wave,"Volume Fraction of Heavy Fluid of ")))throw new IllegalStateException("Saved inlet wave field bindings mismatch");
 }
 private double nextCadence(double next,double t,double interval){while(next<=t+1e-10)next+=interval;return next;}
 private void recordGuard(double t,double speed,double amin,double amax){
  if(!Double.isFinite(t)||!Double.isFinite(speed)||!Double.isFinite(amin)||!Double.isFinite(amax)||speed>50||amin< -1e-8||amax>1.00000001)throw new IllegalStateException("Cannot mark invalid field guard checked");
  lastGuardTime=t;lastGuardSpeed=speed;lastGuardAlphaMin=amin;lastGuardAlphaMax=amax;
 }
 private boolean guardIsCurrent(){return Double.isFinite(lastGuardTime)&&Math.abs(s.getSolution().getPhysicalTime()-lastGuardTime)<1e-9;}
 private void saveGuardedCheckpoint(String filename,String kind)throws Exception{
  if(!guardIsCurrent())throw new IllegalStateException("Refusing checkpoint without current physical guard");
  Path file=out.resolve(filename);if(Files.exists(file))throw new IllegalStateException("Checkpoint already exists; preserve previous save");
  if(Files.getFileStore(out).getUsableSpace()<8L*1024*1024*1024)throw new IllegalStateException("Checkpoint free-space guard");
  s.saveState(file.toString());if(!Files.isRegularFile(file)||Files.size(file)==0)throw new IllegalStateException("Checkpoint save not complete");
  Map<String,Object>d=new LinkedHashMap<>();d.put("file",file.toString());d.put("case",out.getFileName().toString());d.put("time_s",lastGuardTime);d.put("saved_time_s",lastGuardTime);d.put("saved_at",java.time.Instant.now().toString());d.put("completed_save",true);d.put("guard_checked",true);d.put("max_speed_m_s",lastGuardSpeed);d.put("alpha_min",lastGuardAlphaMin);d.put("alpha_max",lastGuardAlphaMax);d.put("kind",kind);d.put("mode",mode);d.put("dt_s",s.getSolverManager().getSolver(ImplicitUnsteadySolver.class).getTimeStep().getValue());d.put("resume_wave",resumeWave);d.put("activation_time_s",activeWave==null?null:activationTime);
  Path pending=out.resolve("latest_checkpoint.pending.json");Files.writeString(pending,json(d));
  try{Files.move(pending,out.resolve("latest_checkpoint.json"),StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);}catch(AtomicMoveNotSupportedException ex){Files.move(pending,out.resolve("latest_checkpoint.json"),StandardCopyOption.REPLACE_EXISTING);}
 }
 private FieldFunction waveField(VofWave w,String prefix){String name=prefix+w.getPresentationName();for(FieldFunction f:s.getFieldFunctionManager().getObjects())if(f.getPresentationName().equals(name))return f;throw new IllegalStateException("Missing wave field "+name);}
 private void waveRuntime(double t,int step)throws Exception{
  double h=activeWave.getWaveHeight().getValue(),period=activeWave.getWavePeriod().getValue();
  if(!Double.isFinite(h)||Math.abs(h-requestedHeight)>1e-9||activeWave.getFirstWaveFront()||(step>0&&(!Double.isFinite(period)||period<=0)))throw new IllegalStateException("Full-height wave runtime mismatch");
  if(step>0)Files.writeString(out.resolve("wave_runtime.csv"),t+","+step+","+h+","+period+"\\n",StandardOpenOption.APPEND);
  Map<String,Object>d=new LinkedHashMap<>();d.put("case",out.getFileName().toString());d.put("activation_time_s",activationTime);d.put("resume_wave",resumeWave);d.put("source_checkpoint_time_s",sourceTime);d.put("ramp_duration_s",0);d.put("ramp_end_time_s",activationTime);d.put("time_s",t);d.put("height_m",h);d.put("target_height_m",requestedHeight);d.put("wavelength_m",requestedLambda);d.put("wave_period_s",period);d.put("height_mode","constant_full_height_from_activation");d.put("stage","inlet_wave_full_amplitude");d.put("first_front",false);d.put("global_wave_initialization",false);d.put("force_settling_required",true);d.put("analysis_origin_s",null);
  Files.writeString(out.resolve("wave_activation.json"),json(d));
 }
'''
s=s.replace(' public void execute(){',method+'\n public void execute(){')
# Guarded saved-wave continuation and physical-time output cadence.
rep('   double dt=Double.parseDouble(System.getenv("NTNU_WAVE_DT"));int steps=Integer.parseInt(System.getenv("NTNU_WAVE_STEPS"));',
'''   double dt=Double.parseDouble(System.getenv("NTNU_WAVE_DT"));int steps=Integer.parseInt(System.getenv("NTNU_WAVE_STEPS"));
   requestedDt=dt;if(!Double.isFinite(dt)||dt<.0001-1e-12||dt>.001+1e-12)throw new IllegalStateException("Unsupported source timestep");
   startupDt=Math.min(dt,.0005);startupDuration=sourceTime==0?40*startupDt:0;
   checkpointInterval=Double.parseDouble(System.getenv().getOrDefault("NTNU_CHECKPOINT_INTERVAL_S",".05"));
   if(!Double.isFinite(checkpointInterval)||checkpointInterval<.05-1e-12||checkpointInterval>1+1e-12||Math.abs(checkpointInterval/dt-Math.rint(checkpointInterval/dt))>1e-7)throw new IllegalStateException("Checkpoint interval must be0.05..1s and integer multiple of dt");
''')
rep('if(Math.abs(dt-.001)>1e-12||steps<30||steps>50000)throw new IllegalStateException("Manual run requires 1 ms and a bounded target");',
'if(steps<30||steps>400000||steps*dt>40+1e-9)throw new IllegalStateException("Manual run requires bounded physical duration at most40s");')
rep('if(!List.of(10.,20.,30.,40.).contains(requestedLambda)||domainXmin>=-2||domainXmax<=3)', 'if(!List.of(10.,20.,30.,40.).contains(requestedLambda)||!Double.isFinite(domainXmin)||!Double.isFinite(domainXmax)||domainXmin>=-2||domainXmax<=3)')
rep('Inspect must retain checkpoint SO 1 ms settings','Inspect must retain exact checkpoint timestep and SECOND_ORDER settings')
# Validate saved inner count before retaining it; never silently change a saved profile.
rep('if(x instanceof InnerIterationStoppingCriterion){((InnerIterationStoppingCriterion)x).setMaximumNumberInnerIterations(10);',
'if(x instanceof InnerIterationStoppingCriterion){if(((InnerIterationStoppingCriterion)x).getMaximumNumberInnerIterations()!=10)throw new IllegalStateException("Saved inner count differs from10");((InnerIterationStoppingCriterion)x).setMaximumNumberInnerIterations(10);')
rep('   double zone=Double.parseDouble(System.getenv("NTNU_ZONE"));',
'''   double zone=Double.parseDouble(System.getenv("NTNU_ZONE"));
   if(!Double.isFinite(zone)||Math.abs(zone-requestedLambda)>1e-9||domainXmin+zone> -2||domainXmax-zone<5)throw new IllegalStateException("Invalid forcing/damping zone");
   if(reg.getConditions().get(VofWaveZoneOption.class).getSelected()!=VofWaveZoneOptionEnum.FORCING_DAMPING||reg.getConditions().get(ForcingLengthSpecificationOption.class).getSelected()!=LengthSpecificationOptionEnum.BOUNDARY||reg.getConditions().get(DampingLengthSpecificationOption.class).getSelected()!=LengthSpecificationOptionEnum.BOUNDARY)throw new IllegalStateException("Wave zone binding mismatch");
   VofWaveForcingLength forcingLength=reg.getBoundaryManager().getBoundary("DOMAIN.inlet").getValues().get(VofWaveForcingLength.class);
   VofWaveDampingLength dampingLength=outlet.getValues().get(VofWaveDampingLength.class);
   if(!(forcingLength.getMethod() instanceof ConstantScalarProfileMethod)||!(dampingLength.getMethod() instanceof ConstantScalarProfileMethod))throw new IllegalStateException("Wave zone length method mismatch");
   requireClose(forcingLength.getMethod(ConstantScalarProfileMethod.class).getQuantity().getValue(),zone,1e-9,"forcing length");
   requireClose(dampingLength.getMethod(ConstantScalarProfileMethod.class).getQuantity().getValue(),zone,1e-9,"damping length");
''')
rep('"source_calm_time_s",sourceTime','"source_checkpoint_time_s",sourceTime')
# Startup is never coarser than the requested profile, and restores that exact dt.
rep('us.getTimeStep().setValue(.0005);','us.getTimeStep().setValue(startupDt);')
rep('Math.abs(t-i*.0005)>1e-8','Math.abs(t-i*startupDt)>1e-8')
s=s.replace('nw.getReportMonitorValue()/.0005','nw.getReportMonitorValue()/startupDt').replace('na.getReportMonitorValue()/.0005','na.getReportMonitorValue()/startupDt')
rep('"max_speed_m_s",v,"dt_s",.0005,"inner",50','"max_speed_m_s",v,"dt_s",startupDt,"inner",50')
rep('    h.write(t+","+i+','    recordGuard(t,v,mi,ma);h.write(t+","+i+')
rep('  s.saveState(out.resolve("checkpoint_startup_t0.020.sim").toString());','')
rep('  Files.writeString(out.resolve("startup_acceptance.json"),','  saveGuardedCheckpoint(String.format(Locale.ROOT,"checkpoint_startup_t%.6f.sim",s.getSolution().getPhysicalTime()),"startup");Files.writeString(out.resolve("startup_acceptance.json"),')
rep('us.getTimeStep().setValue(.001);','us.getTimeStep().setValue(requestedDt);')
rep('"steps",40,"dt_s",.0005,"inner",50,"next_dt_s",.001,"next_inner",10','"steps",40,"dt_s",startupDt,"duration_s",40*startupDt,"inner",50,"next_dt_s",requestedDt,"next_inner",10')
rep('   long start=System.nanoTime();String status="target_reached";int done=0;',
'   double nextGaugeTime=initialTime+.005,nextFieldTime=initialTime+.25,nextOutletTime=initialTime+.025,nextCheckpointTime=initialTime+checkpointInterval;long start=System.nanoTime();String status="target_reached";int done=0;')
rep('if(step>0 && (step%250==0 || ((100*(Math.abs(nw)+Math.abs(na))/dt/in)>.01 && eventExports<6))){localSnapshot',
'if(step>0 && (t+1e-10>=nextFieldTime || ((100*(Math.abs(nw)+Math.abs(na))/dt/in)>.01 && eventExports<6))){nextFieldTime=nextCadence(nextFieldTime,t,.25);localSnapshot')
rep('if(step>0 && (step%25==0 || step<=3))exportOutlet(t);',
'if(step>0 && (t+1e-10>=nextOutletTime || step<=3)){exportOutlet(t);nextOutletTime=nextCadence(nextOutletTime,t,.025);}')
rep('if(step==1||step%5==0){for(int k=0;',
'if(step<=1||t+1e-10>=nextGaugeTime){nextGaugeTime=nextCadence(nextGaugeTime,t,.005);for(int k=0;')
rep('if(step>0&&step%250==0){String cp=String.format(Locale.ROOT,"checkpoint_t%.3f.sim",t);s.saveState(out.resolve(cp).toString());Files.writeString(out.resolve("latest_checkpoint.json"),json(Map.of("file",out.resolve(cp).toString(),"time_s",t,"completed_save",true)));',
'recordGuard(t,v,mn,mx);if(step>0&&t+1e-10>=nextCheckpointTime){saveGuardedCheckpoint(String.format(Locale.ROOT,"checkpoint_t%.6f.sim",t),"periodic");nextCheckpointTime=nextCadence(nextCheckpointTime,t,checkpointInterval);')
rep('s.saveState(out.resolve("final.sim").toString());Files.writeString(out.resolve("completed.json"),json(Map.of("status",status,',
'if(!status.equals("stability_guard")&&guardIsCurrent())saveGuardedCheckpoint("final.sim","final");else s.saveState(out.resolve("final.sim").toString());Files.writeString(out.resolve("completed.json"),json(Map.of("status",status,')
rep('if("User stop during guarded startup".equals(e.getMessage())){s.saveState(out.resolve("final.sim").toString());',
'if("User stop during guarded startup".equals(e.getMessage())){if(guardIsCurrent())saveGuardedCheckpoint("final.sim","startup_user_stop");else s.saveState(out.resolve("final.sim").toString());')
# Manifest distinguishes cache at load from runtime verification; original phase/clock is retained.
rep('d.put("analysis_origin_s",null);','d.put("analysis_origin_s",null);d.put("checkpoint_interval_s",checkpointInterval);d.put("period_verified_after_step",step>0);')
rep('local_balance_t%.3f','local_balance_t%.6f')
rep('+"_t%.3f.csv"','+"_t%.6f.csv"')
rep('Guarded startup0.5ms50inner40steps then SO1ms10inner; pressuretol0.01.','Fresh startup40steps at min(requested dt,0.5ms) with50inner; saved continuations skip startup. Exact selected timestep, SECOND_ORDER,10inner,pressuretol0.01.')
rep('Only numericalchange pressure relativeAMGtolerance0.1to0.01; VOFtol0.1, allothercontrols unchanged; everyinnernative and LOWtrace retained','VOFtol0.1 and pressuretol0.01; exact selected timestep; every-inner native reports retained. LOW trace disabled.')
assert 'initializeSolution(' not in s and 'clearSolution(' not in s
(R/'LocalCalmWave.java').write_text(s,encoding='utf-8')
base='E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/star/lib/java'
cp=';'.join(base+'/'+x for x in ['platform/modules/ext/*','platform/modules/*','platform/core/*'])
folder=R/'local_control_macro_classes';folder.mkdir(exist_ok=True)
p=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','--release','17','-cp',cp,'-d',str(folder),str(R/'LocalCalmWave.java')],capture_output=True,text=True)
(R/'local_control_macro_compile.log').write_text(p.stdout+p.stderr)
receipt=dict(status='javac_passed' if p.returncode==0 else 'failed',macro_sha256=hashlib.sha256((R/'LocalCalmWave.java').read_bytes()).hexdigest(),modes=['calm','wave_setup','wave'],wave_initialization=False,height_ramp=False,resume_wave_supported=True,checkpoint_interval_default_s=.05,dt_range_s=[.0001,.001],runtime_validation='pending; javac and static/mock contracts only')
(R/'local_control_macro_receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt));print(p.stderr if p.returncode else 'Compile complete; no flow launched')
raise SystemExit(p.returncode)