from pathlib import Path
import re,subprocess,hashlib,json,math
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029')
W=Path(r'E:/ntnu/quasi2d_waves_20261029')
case=W/'W01a_W20L4_M10_inlet_wave_r1'
s=(R/'W01ResumeCyclesR2.java').read_text()
def sub(a,b):
 global s
 if s.count(a)!=1:raise RuntimeError('anchor count '+str(s.count(a))+': '+a[:100])
 s=s.replace(a,b)
sub('public class W01ResumeCyclesR2','public class W01aInletWaveR1')
s=s.replace('W01 resumed','W01a inlet wave').replace('W01R2','W01aInletR1')
sub('out=Paths.get("E:/ntnu/quasi2d_waves_20261029/W01_W20L4_M10_FS020_cycles_r2")','out=Paths.get("'+case.as_posix()+'")')
sub('Paths.get("E:/ntnu/quasi2d_waves_20261029/W01_W20L4_M10_FS020_diagnostic_r1/final.sim").toAbsolutePath().normalize()','out.resolve("input.sim").toAbsolutePath().normalize()')
sub('double dt=.001;int steps=16778;','double dt=.001;int steps=20123;')
sub('steps!=16778','steps!=20123')
sub('getPhysicalTime()-.168','getPhysicalTime()-.587')
a=(R/'AuditW01aInletRampR1.java').read_text()
make=a[a.index(' private FifthOrderVofWave makeWave('):a.index(' private SurfaceIntegralReport surface(')]
ramp=a[a.index(' private String rampExpression('):a.index(' private void view(')]
wavefield=a[a.index(' private FieldFunction waveField('):a.index(' private VolumeIntegralReport volume(')]
extra=make+ramp+wavefield+'''
 private static final double ACTIVATION=.587,TARGET_PERIOD=.8472673206891129,RAMP_DURATION=2*TARGET_PERIOD;
 private void waveRuntime(FifthOrderVofWave w,double t,int step)throws Exception{
  double h=w.getWaveHeight().getValue(),period=w.getWavePeriod().getValue();
  if(step>0&&(!Double.isFinite(h)||!Double.isFinite(period)||period<=0||h<.0000009||h>.5000001))throw new IllegalStateException("Invalid runtime wave parameters");
  if(step>0)Files.writeString(out.resolve("wave_runtime.csv"),t+","+step+","+h+","+period+"\\n",StandardOpenOption.APPEND);
  Map<String,Object>d=new LinkedHashMap<>();d.put("case","W01a_W20L4_M10_inlet_wave_r1");d.put("activation_time_s",ACTIVATION);d.put("ramp_duration_s",RAMP_DURATION);d.put("ramp_end_time_s",ACTIVATION+RAMP_DURATION);d.put("time_s",t);d.put("height_m",h);d.put("target_height_m",.5);d.put("wave_period_s",period);d.put("planning_full_height_period_s",TARGET_PERIOD);d.put("stage",t<ACTIVATION+RAMP_DURATION?"inlet_wave_ramp":"inlet_wave_full_amplitude");d.put("first_front",w.getFirstWaveFront());d.put("global_wave_initialization",false);d.put("force_settling_required",false);d.put("analysis_origin_s",null);d.put("cycle_screen","Pending measured wave arrival and full-amplitude cycles; no calm/ramp samples admitted");
  Files.writeString(out.resolve("wave_activation.json"),json(d));
 }
'''
sub(' public void execute(){',extra+' public void execute(){')
sub('FifthOrderVofWave wave=(FifthOrderVofWave)reg.getValues().get(ForcingVofWaveSpecification.class).getForcingVofWave();','''VofWaveModel wm=pc.getModelManager().getModel(VofWaveModel.class);wm.setEnableTheoryComparison(true);
   FifthOrderVofWave wave=makeWave(wm,"W01a inlet generated FifthOrder H050 L20");
   wave.getWaveHeight().setDefinition(rampExpression(ACTIVATION,RAMP_DURATION));
   Boundary inlet=reg.getBoundaryManager().getBoundary("DOMAIN.inlet");
   inlet.getValues().get(VelocityProfile.class).setMethod(FunctionVectorProfileMethod.class);
   inlet.getValues().get(VelocityProfile.class).getMethod(FunctionVectorProfileMethod.class).setFieldFunction(waveField(wave,"Velocity of "));
   VolumeFractionProfile vp=inlet.getValues().get(VolumeFractionProfile.class);vp.setMethod(CompositeNMinus1ArrayProfileMethod.class);
   vp.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).setMethod(FunctionScalarProfileMethod.class);
   vp.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).setFieldFunction(waveField(wave,"Volume Fraction of Heavy Fluid of "));
   reg.getValues().get(ForcingVofWaveSpecification.class).setForcingVofWave(wave);
   ArrayList<Object> bindings=new ArrayList<>();for(Boundary b:reg.getBoundaryManager().getBoundaries()){
    String f=String.valueOf(b.getConditions().get(VofWaveForcingBoundaryOption.class).getSelectedElement()),d=String.valueOf(b.getConditions().get(VofWaveDampingBoundaryOption.class).getSelectedElement());
    bindings.add(Map.of("boundary",b.getPresentationName(),"forcing",f,"damping",d));
   }
   Files.writeString(out.resolve("inlet_wave_binding.json"),json(Map.of("boundary_bindings",bindings,"forcing_wave",wave.getPresentationName(),"wave_height_definition",wave.getWaveHeight().getDefinition(),"initial_conditions_unchanged",true,"global_initialization",false,"source_calm_time_s",ACTIVATION,"require_calm_force_settling",false,"forcing_zone_x_m",List.of(-35,-15),"damping_zone_x_m",List.of(25,45))));
   Files.writeString(out.resolve("wave_runtime.csv"),"time_s,step,evaluated_height_m,actual_period_s\\n");waveRuntime(wave,ACTIVATION,0);''')
start=s.index('   Files.writeString(out.resolve("continuation_identity.json")')
end=s.index('   FieldFunction alpha=',start)
s=s[:start]+'''   Files.writeString(out.resolve("continuation_identity.json"),json(Map.of("initial_time_s",initialTime,"target_time_s",initialTime+steps*dt,"reinitialized",false,"outlet_backflow","ENVIRONMENTAL","bottom","SLIP","scope","W01a immediate inlet-wave activation from computed calm t.587 without force-settling wait; boundary/upstream forcing ramp only, initial physical fields retained. Four complete repeated arrived full-amplitude cycles may stop; ten indicative, twenty review cap. Mass criterion .01% remains diagnostic; 50m/s stability guard unchanged.")));
'''+s[end:]
sub('FieldFunction theory=pc.getInitialConditions().get(VolumeFractionProfile.class).getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).getFieldFunction();','FieldFunction theory=waveField(wave,"Volume Fraction of Heavy Fluid of ");')
sub('double[] xs={-10,-5,2.5,5,10,15,20};','double[] xs={-34,-25,-16,-10,-5,2.5,5,10,15,20};')
sub('(40.76465590181842)','(32.58684386451413)')
sub('(802.7692557120714)','(1123.6326563462453)')
s=s.replace('restart_state_t0.168.sim','restart_state_t0.587.sim')
sub('"time_s",.168,"completed_save"','"time_s",.587,"completed_save"')
sub('long vc=vofAmg.getTotalNumberCycles()','waveRuntime(wave,t,step);\n     long vc=vofAmg.getTotalNumberCycles()')
# Native signed vorticity fields in both regular spatial and final CSV exports.
sub('fields.add(v.getMagnitudeFunction());tab.setFieldFunctions(fields);','fields.add(v.getMagnitudeFunction());fields.add(ff("VorticityVector").getComponentFunction(1));tab.setFieldFunctions(fields);')
sub('s.getFieldFunctionManager().getFunction("Density")));fieldTable.extract();','s.getFieldFunctionManager().getFunction("Density"),ff("VorticityVector").getComponentFunction(1)));fieldTable.extract();')
sub('  ArrayList<String> names=new ArrayList<>();for(Scene sc:inspectionScenes)', '''  scalarScene("13 Foil signed vorticity omega y per s",mid,ff("VorticityVector").getComponentFunction(1),.6,0,1.2,false,-500,500);
  scalarScene("14 Upstream and wake signed vorticity omega y per s",mid,ff("VorticityVector").getComponentFunction(1),2,0,4,false,-50,50);
  ArrayList<String> names=new ArrayList<>();for(Scene sc:inspectionScenes)''')
# Export full spatial state every quarter second for current preview/checkpoints, plus sampled mass events.
s=s.replace('step%500==0','step%250==0')
sub('if(step>0 && (step%50==0 || step<=3))exportOutlet(t);','if(step>0 && (step%250==0 || step<=3))exportOutlet(t);')
# Stop condition always user-controlled or guarded; post-arrival cycle screen external, never treat startup as full cycles.
p=R/'W01aInletWaveR1.java';p.write_text(s,encoding='utf8')
jdk=Path(r'C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe')
lib=Path(r'E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/star/lib/java')
cp=';'.join(str(lib/x) for x in ['platform/modules/ext/*','platform/modules/*','platform/core/*'])
out=R/'compiled_w01a_inlet_r1';out.mkdir(exist_ok=True)
r=subprocess.run([str(jdk),'--release','17','-cp',cp,'-d',str(out),str(p)],capture_output=True,text=True)
(R/'w01a_inlet_compile.log').write_text(r.stdout+r.stderr)
receipt={'status':'javac_passed' if r.returncode==0 else 'javac_failed','macro_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'returncode':r.returncode}
(R/'w01a_inlet_macro_build_receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt));print((r.stdout+r.stderr)[-2000:])
if r.returncode:raise SystemExit(r.returncode)
