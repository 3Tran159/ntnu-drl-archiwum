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
rep(' private double domainXmin,domainXmax,requestedLambda;',' private double domainXmin,domainXmax,requestedLambda,requestedHeight,sourceTime; private FifthOrderVofWave activeWave; private String mode;')
rep('   if(s.getNumberOfGpgpus()!=1)throw new IllegalStateException("Exactly one GPU required");','   mode=Objects.requireNonNull(System.getenv("NTNU_MODE"));if(!List.of("calm","wave","wave_setup").contains(mode))throw new IllegalStateException("Unknown local mode");sourceTime=Double.parseDouble(System.getenv("NTNU_SOURCE_TIME"));if(!Double.isFinite(sourceTime)||sourceTime<0||!Double.isFinite(s.getSolution().getPhysicalTime()))throw new IllegalStateException("Invalid source physical time");if(s.getNumberOfGpgpus()!=(mode.equals("wave_setup")?0:1))throw new IllegalStateException("Wrong compute mode");')
rep('Math.abs(s.getSolution().getPhysicalTime())>1e-8','Math.abs(s.getSolution().getPhysicalTime()-sourceTime)>1e-8')
a=s.index('   double requestedHeight=');b=s.index('   Files.writeString(out.resolve("requested_wave_audit.json")',a)
s=s[:a]+'''   requestedHeight=Double.parseDouble(System.getenv("NTNU_WAVE_HEIGHT"));double wavePeriod=0;boolean reinitialized=false;
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
    Files.writeString(out.resolve("wave_runtime.csv"),"time_s,step,evaluated_height_m,actual_period_s\\n");waveRuntime(sourceTime,0);
   }
''' + s[b:]
rep('"target_time_s",.020+steps*dt','"target_time_s",(sourceTime==0?.020:sourceTime)+steps*dt')
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
method=''' private FieldFunction waveField(VofWave w,String prefix){String name=prefix+w.getPresentationName();for(FieldFunction f:s.getFieldFunctionManager().getObjects())if(f.getPresentationName().equals(name))return f;throw new IllegalStateException("Missing wave field "+name);}
 private void waveRuntime(double t,int step)throws Exception{
  double h=activeWave.getWaveHeight().getValue(),period=activeWave.getWavePeriod().getValue();
  if(!Double.isFinite(h)||Math.abs(h-requestedHeight)>1e-9||activeWave.getFirstWaveFront()||(step>0&&(!Double.isFinite(period)||period<=0)))throw new IllegalStateException("Full-height wave runtime mismatch");
  if(step>0)Files.writeString(out.resolve("wave_runtime.csv"),t+","+step+","+h+","+period+"\\n",StandardOpenOption.APPEND);
  Map<String,Object>d=new LinkedHashMap<>();d.put("case",out.getFileName().toString());d.put("activation_time_s",sourceTime);d.put("ramp_duration_s",0);d.put("ramp_end_time_s",sourceTime);d.put("time_s",t);d.put("height_m",h);d.put("target_height_m",requestedHeight);d.put("wavelength_m",requestedLambda);d.put("wave_period_s",period);d.put("height_mode","constant_full_height_from_activation");d.put("stage","inlet_wave_full_amplitude");d.put("first_front",false);d.put("global_wave_initialization",false);d.put("force_settling_required",true);d.put("analysis_origin_s",null);
  Files.writeString(out.resolve("wave_activation.json"),json(d));
 }
'''
s=s.replace(' public void execute(){',method+'\n public void execute(){')
assert 'initializeSolution(' not in s and 'clearSolution(' not in s
(R/'LocalCalmWave.java').write_text(s,encoding='utf-8')
base='E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/star/lib/java'
cp=';'.join(base+'/'+x for x in ['platform/modules/ext/*','platform/modules/*','platform/core/*'])
folder=R/'local_control_macro_classes';folder.mkdir(exist_ok=True)
p=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','--release','17','-cp',cp,'-d',str(folder),str(R/'LocalCalmWave.java')],capture_output=True,text=True)
(R/'local_control_macro_compile.log').write_text(p.stdout+p.stderr)
receipt=dict(status='javac_passed' if p.returncode==0 else 'failed',macro_sha256=hashlib.sha256((R/'LocalCalmWave.java').read_bytes()).hexdigest(),modes=['calm','wave_setup','wave'],wave_initialization=False,height_ramp=False)
(R/'local_control_macro_receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt));print(p.stderr if p.returncode else 'Compile complete; no flow launched')
raise SystemExit(p.returncode)
