from pathlib import Path
import json,subprocess,hashlib,datetime,shutil
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029')
W=Path(r'E:/ntnu/quasi2d_waves_20261029')
name='W01a_W20L4_M10_inlet_fullheight_restart_r3'
s=(R/'W01aInletWaveR1.java').read_text()
def one(a,b):
 global s
 if s.count(a)!=1:raise RuntimeError('anchor '+str(s.count(a))+' '+a[:90])
 s=s.replace(a,b)
s=s.replace('W01aInletWaveR1','W01aFullHeightRestartR3').replace('W01a_W20L4_M10_inlet_wave_r1',name).replace('W01aInletR1','W01aFullR3')
one('ACTIVATION=.587,TARGET_PERIOD=.8472673206891129,RAMP_DURATION=2*TARGET_PERIOD','ACTIVATION=0,TARGET_PERIOD=.8472673206891129,RAMP_DURATION=0')
one('wave.getWaveHeight().setDefinition(rampExpression(ACTIVATION,RAMP_DURATION));','wave.getWaveHeight().setValue(.5);liveWave=wave;')
one('h<.0000009||h>.5000001','Math.abs(h-.5)>1e-10')
one('d.put("target_height_m",.5);','d.put("target_height_m",.5);d.put("height_mode","constant_full_height_from_activation");')
one('double dt=.001;int steps=20123;','double dt=.001;int steps=18409;')
one('steps!=20123','steps!=18409')
one('getPhysicalTime()-.587','getPhysicalTime()-0')
one('PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getContinuum("water+air");','''PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getContinuum("water+air");
   if(!(reg.getValues().get(ForcingVofWaveSpecification.class).getForcingVofWave() instanceof FlatVofWave))throw new IllegalStateException("Fresh zero-time calm source required");
   setupForces();double[] sourceForces=forces();''')
oldstart=s.index('   setupForces();setupViews();double[] f0=forces();')
oldend=s.index('\n   ReportMonitor waterInner,airInner;',oldstart)
s=s[:oldstart]+'''   setupViews();double[] f0=forces();
   for(int j=0;j<4;j++)if(Math.abs(f0[j]-sourceForces[j])>1e-8*Math.max(1,Math.abs(sourceForces[j])))throw new IllegalStateException("Initial physical force fingerprint changed during boundary setup");
   Files.writeString(out.resolve("initial_force_fingerprint.json"),json(Map.of("time_s",s.getSolution().getPhysicalTime(),"Fx_N",f0[0],"Fz_N",f0[1],"pressure_drag_N",f0[2],"viscous_drag_N",f0[3],"before_after_setup_equal",true)));
   s.saveState(out.resolve("configured_initial_t0.000.sim").toString());
'''+s[oldend:]
one('if(Math.abs(vofAmg.getConvergeTol()-.1)>1e-12||Math.abs(pressureAmg.getConvergeTol()-.01)>1e-12||vofAmg.getMaxCycles()!=30',
'''if(Math.abs(pressureAmg.getConvergeTol()-.1)>1e-12)throw new IllegalStateException("Prepared calm pressure tolerance differs");
   pressureAmg.setConvergeTol(.01);
   if(Math.abs(vofAmg.getConvergeTol()-.1)>1e-12||Math.abs(pressureAmg.getConvergeTol()-.01)>1e-12||vofAmg.getMaxCycles()!=30''')
one('initialTime=s.getSolution().getPhysicalTime();\n   waterInner=',
'''startupAnalyticInventory=analyticWater;startupActual=actual;startupReferences=analytic;startupInterfaceCFL=icfl;startupMass=mass;startupFlux=flux;
   guardedStartup(us,vmax,cfl,amin,amax,nativeWater,nativeAir);
   Files.writeString(out.resolve("latest_checkpoint.json"),json(Map.of("file",out.resolve("checkpoint_startup_t0.020.sim").toString(),"time_s",.020,"completed_save",true)));
   initialTime=s.getSolution().getPhysicalTime();
   waterInner=''')
# The initial numerical startup still starts the FULL wave at its first step. It is not a calm waiting stage.
one(' private void guardedStartup(',''' private FifthOrderVofWave liveWave;
 private VolumeIntegralReport startupAnalyticInventory,startupMass;
 private MaxReport startupInterfaceCFL;
 private ArrayList<SurfaceIntegralReport> startupActual,startupReferences;
 private ArrayList<MassFlowReport> startupFlux;
 private void guardedStartup(''')
one('try(var h=Files.newBufferedWriter(out.resolve("startup_history.csv"))){','''double prevMass=startupMass.getReportMonitorValue(),olderMass=Double.NaN;
  long startupClock=System.nanoTime();
  try(var h=Files.newBufferedWriter(out.resolve("startup_history.csv"))){''')
one('h.write("time_s,step,max_speed_m_s,max_CFL,alpha_min,alpha_max,Fx_N,Fz_N,native_water_kg_s,native_air_kg_s\\n");',
'''h.write("time_s,step,wall_s,max_speed_m_s,max_CFL,interface_CFL,alpha_min,alpha_max,Fx_slice_N,Fz_slice_N,CD,CL_total,native_water_kg_s,native_air_kg_s,native_abs_pct_inward_mass,bdf2_plus_flux_pct_inward_mass,full_inlet_height_m,analytic_period_s\\n");''')
one('h.write(t+","+i+","+v+","+c+","+mi+","+ma+","+f[0]+","+f[1]+","+nw.getReportMonitorValue()/.0005+","+na.getReportMonitorValue()/.0005+"\\n");h.flush();',
'''waveRuntime(liveWave,t,i);
    double analyticV=startupAnalyticInventory.getReportMonitorValue(),nwV=nw.getReportMonitorValue()/.0005,naV=na.getReportMonitorValue()/.0005,ci=startupInterfaceCFL.getReportMonitorValue();
    if(!Double.isFinite(analyticV)||!Double.isFinite(nwV)||!Double.isFinite(naV)||!Double.isFinite(ci))throw new IllegalStateException("First/full-height startup analytic or native diagnostic invalid");
    for(int j=0;j<startupReferences.size();j++){double a=startupActual.get(j).getReportMonitorValue()/.02-24,b=startupReferences.get(j).getReportMonitorValue()/.02-24;if(!Double.isFinite(a)||!Double.isFinite(b)||Math.abs(a)>1.5)throw new IllegalStateException("Startup gauge invalid");}
    double cm=startupMass.getReportMonitorValue(),net=0,in=0;for(MassFlowReport r:startupFlux){double q=r.getReportMonitorValue();if(!Double.isFinite(q))throw new IllegalStateException("Startup flux invalid");net+=q;if(q<0)in-=q;}
    double budget=i>=2?((1.5*cm-2*prevMass+.5*olderMass)/.0005+net)/in*100:Double.NaN;
    olderMass=prevMass;prevMass=cm;
    h.write(t+","+i+","+(System.nanoTime()-startupClock)*1e-9+","+v+","+c+","+ci+","+mi+","+ma+","+f[0]+","+f[1]+","+f[0]/3855.6+","+f[1]/3855.6+","+nwV+","+naV+","+100*(Math.abs(nwV)+Math.abs(naV))/in+","+budget+","+liveWave.getWaveHeight().getValue()+","+liveWave.getWavePeriod().getValue()+"\\n");h.flush();''')
one('if(i%5==0)Files.writeString(out.resolve("progress.json"),json(Map.of("stage","guarded foil startup","time_s",t,"steps",i,"max_speed_m_s",v,"dt_s",.0005,"inner",50)));',
'''if(i==1||i%5==0)Files.writeString(out.resolve("progress.json"),json(Map.of("stage","full-height wave active during numerical startup","time_s",t,"steps",i,"max_speed_m_s",v,"dt_s",.0005,"inner",50,"CD",f[0]/3855.6,"CL_total",f[1]/3855.6,"interface_CFL",ci)));''')
s=s.replace('W01a immediate inlet-wave activation from computed calm t.587 without force-settling wait; boundary/upstream forcing ramp only, initial physical fields retained.','W01a fresh t0 restart: CONSTANT full H0.5 inlet/upstream forcing from first step; no height ramp or calm waiting; no global wave initialization. Numerical guarded startup .5ms50inner40steps, thenSO1ms10inner.')
s=s.replace('"target_time_s",initialTime+steps*dt','"target_time_s",.020+steps*dt')
s=s.replace('"initial_conditions_unchanged",true','"initial_conditions_unchanged",true')
# No initialization calls are allowed. Newly-created full-height analytic coefficients must become finite after first guarded step.
assert 'initializeSolution(' not in s and 'clearSolution(' not in s
p=R/'W01aFullHeightRestartR3.java';p.write_text(s,encoding='utf8')
lib=Path(r'E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/star/lib/java')
cp=';'.join(str(lib/x) for x in ['platform/modules/ext/*','platform/modules/*','platform/core/*'])
out=R/'compiled_w01a_fullheight_r3';out.mkdir(exist_ok=True)
q=subprocess.run([r'C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','--release','17','-cp',cp,'-d',str(out),str(p)],capture_output=True,text=True)
(R/'w01a_fullheight_r3_compile.log').write_text(q.stdout+q.stderr)
receipt={'status':'javac_passed' if q.returncode==0 else 'javac_failed','macro_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'returncode':q.returncode}
(R/'w01a_fullheight_r3_macro_build_receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt));print((q.stdout+q.stderr)[-2000:])
if q.returncode:raise SystemExit(q.returncode)
# Adapt the proven exclusive controller to fresh zero-time source and a new unique attempt.
c=(R/'run_w01a_inlet_wave_r1.py').read_text()
c=c.replace('W01a_W20L4_M10_inlet_wave_r1',name).replace("W01a_W20L4_M10_calm_start_r1/final.sim","C01_W20L4_M10_FS020_env_setup_r1/prepared.sim").replace('W01aInletWaveR1.java','W01aFullHeightRestartR3.java').replace('w01a_inlet_wave_r1.lock','w01a_fullheight_restart_r3.lock').replace('w01a_inlet_macro_build_receipt.json','w01a_fullheight_r3_macro_build_receipt.json')
a=c.index(" audit=e.read(R/'w01a_inlet_ramp_step_audit_result.json'");b=c.index(" if CASE.exists()",a)
c=c[:a]+""" audit=e.read(SOURCE.parent/'initial_audit.json',{})
 if audit.get('status')!='prepared_zero_steps' or audit.get('time_s')!=0 or audit.get('flow_steps')!=0 or audit.get('cells')!=317277 or audit.get('wave')!=False:raise RuntimeError('Verified zero-time calm input required')
 source_sha=e.digest(SOURCE)
 if source_sha!='8cab371c1f4bd000283877b4e28811c978814cc30a57c9fb7701cce85fc235ce':raise RuntimeError('Prepared source identity differs')
 prior=e.read(W/'W01a_W20L4_M10_inlet_wave_r1/controller_result.json',{})
 if prior.get('returncode')!=0 or prior.get('source_unchanged')!=True or prior.get('completed',{}).get('status')!='stopped_by_marker':raise RuntimeError('Previous ramp attempt not saved normally')
"""+c[b:]
c=c.replace("computed .587s","fresh t0 full-height H0.5").replace("source_time_s=.587","source_time_s=0").replace("'time_s':.587","'time_s':0").replace("last_pt=.587","last_pt=0").replace("pt=progress.get('time_s',.587)","pt=progress.get('time_s',0)").replace("pt<=.587","pt<=0").replace("pt>.587","pt>0")
c=c.replace("no calm-force wait or global initialization","constant H0.5 from t0, no height ramp, no calm-force wait or global initialization")
c=c.replace("Start inlet wave without waiting for forces to settle; use computed calm fields","Restart W01a from t0 with inlet H0.5 from first step, no height ramp or force settling wait; clear old live dashboard history")
c=c.replace("target_s=20.710","target_s=18.429")
c=c.replace("W01a computed calm .587s restart, then wave generated at inlet and upstream forcing zone only. Smooth height ramp begins immediately.","W01a fresh t0 restart. Full H0.5 wave at inlet/upstream forcing from first .5ms guarded step; NO height ramp or calm waiting. Initial interior fields remain calm. First40steps .5ms50inner, thenSO1ms10inner.")
c=c.replace("input.sim is pre-wave computed calm","input.sim is zero-step initialized calm template; computed results are separate completed checkpoints")
(R/'run_w01a_fullheight_restart_r3.py').write_text(c,encoding='utf8')
compile(c,str(R/'run_w01a_fullheight_restart_r3.py'),'exec')
print(json.dumps({'controller':'compiled','case':name,'source_time_s':0,'height_m':.5,'height_ramp':False}))
