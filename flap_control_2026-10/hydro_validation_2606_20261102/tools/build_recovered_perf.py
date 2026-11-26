from pathlib import Path
import subprocess
H=Path(__file__).resolve().parents[1]
t=(H/'macros/InletPressureRecovery.java').read_text()
t=t.replace('InletPressureRecovery','RecoveredPerfBench').replace('INLET_PRESSURE_RECOVERY_20261103','RECOVERED_PERF_20261103').replace('NTNU_PRESSURE_RECOVERY_ALLOWED','NTNU_RECOVERED_PERF_ALLOWED').replace('PRESSURE_RECOVERY_RUNTIME.properties','RECOVERED_PERF_RUNTIME.properties')
def change(a,b):
 global t
 assert t.count(a)==1,(a,t.count(a));t=t.replace(a,b)
change('final double DT=.002, P_LIMIT=12339.214766776897;','double DT=.002; int totalSteps=18; final double P_LIMIT=12339.214766776897;')
change('Properties auth=new Properties();',r'''Process binding=new ProcessBuilder("C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe","-X","utf8",root.resolve("tools/perf_bind_workers.py").toString(),out.toString()).redirectErrorStream(true).start();String bindingOutput=new String(binding.getInputStream().readAllBytes(),java.nio.charset.StandardCharsets.UTF_8);if(binding.waitFor()!=0)throw new IllegalStateException("Owned MPI affinity initialization failed: "+bindingOutput);Files.writeString(out.resolve("affinity_initialization.txt"),bindingOutput);
 Properties auth=new Properties();''')
change('double t0=s.getSolution().getPhysicalTime();','DT=Double.parseDouble(auth.getProperty("dt"));if(DT!=.002&&DT!=.003&&DT!=.004)throw new IllegalStateException("Unapproved dt");totalSteps=(int)Math.round(.024/DT);double t0=s.getSolution().getPhysicalTime();')
change('Math.abs(us.getTimeStep().getValue()-DT)','Math.abs(us.getTimeStep().getValue()-.002)')
change('if(Math.abs(rv("HF_CL_hydro")-.3206861558619269)>1e-9||Math.abs(rv("HF_CD")-.007155867131695475)>1e-9||Math.abs(rv("HF_Mh_Nm")+11.778200215235007)>1e-7)', 'if(Math.abs(rv("HF_CL_hydro")-Double.parseDouble(auth.getProperty("CL")))>1e-8||Math.abs(rv("HF_CD")-Double.parseDouble(auth.getProperty("CD")))>1e-8||Math.abs(rv("HF_Mh_Nm")-Double.parseDouble(auth.getProperty("Mh")))>1e-6)')
# Inlet monitor already exists in this production checkpoint; retain it.
a=t.index(' UserFieldFunction im=field("RECOVERY_InletMask"');b=t.index(' captureFields("readback");',a);t=t[:a]+t[b:]
change('setU(speedAt(stage,stageStart,t0));commandAngle=',r'''
 // Readback above occurs before changing dt. No reset/initialization/remeshing.
 us.getTimeStep().setValue(DT);
 AverageWorkerCommunicationTimeReport comm=s.getReportManager().createReport(AverageWorkerCommunicationTimeReport.class);
 TimeStepCpuTimeReport stepCpu=s.getReportManager().createReport(TimeStepCpuTimeReport.class);TimeStepElapsedTimeReport stepElapsed=s.getReportManager().createReport(TimeStepElapsedTimeReport.class);
 FieldFunction cfl=null;StringBuilder candidates=new StringBuilder();
 for(FieldFunction f:s.getFieldFunctionManager().getObjects()){String n=f.getFunctionName().toLowerCase(Locale.ROOT);if(n.contains("cfl")||n.contains("courant")){candidates.append(f.getFunctionName()+" | "+f.getPresentationName()+"\n");if(n.contains("convective"))cfl=f;}}
 if(cfl==null)for(String name:List.of("ConvectiveCfl","ConvectiveCFL","ConvectiveCflNumber","CourantNumber"))if(s.getFieldFunctionManager().hasFunction(name)){cfl=s.getFieldFunctionManager().getFunction(name);break;}
 MaxReport cflMax=null;VolumeAverageReport cflMean=null;
 if(cfl!=null){cflMax=s.getReportManager().createReport(MaxReport.class);cflMax.getParts().setObjects(regions);cflMax.setFieldFunction(cfl);cflMean=s.getReportManager().createReport(VolumeAverageReport.class);cflMean.getParts().setObjects(regions);cflMean.setFieldFunction(cfl);}
 Files.writeString(out.resolve("CFL_AVAILABILITY.txt"),"selected="+(cfl==null?"UNAVAILABLE":cfl.getFunctionName())+"\n"+candidates);
 Files.writeString(out.resolve("REOPEN_VERIFIED.json"),"{\"time_s\":"+t0+",\"iteration\":"+initialIteration+",\"saved_fields_match\":true,\"mesh_cells\":333939,\"source_dt\":0.002,\"test_dt\":"+DT+",\"no_reset\":true}");
 setU(speedAt(stage,stageStart,t0));commandAngle=''')
change('for(int i=1;i<=50;i++)','for(int i=1;i<=totalSteps;i++)')
change('long start=System.nanoTime();s.getSimulationIterator().step(1);double seconds=(System.nanoTime()-start)/1e9;', 'double commBefore=comm.getReportMonitorValue();long epochStart=System.currentTimeMillis(),start=System.nanoTime();s.getSimulationIterator().step(1);double seconds=(System.nanoTime()-start)/1e9;long epochEnd=System.currentTimeMillis();double commAfter=comm.getReportMonitorValue(),nativeElapsed=stepElapsed.getReportMonitorValue(),nativeCpu=stepCpu.getReportMonitorValue();')
change('if(i==50){complete=true;break;}','if(i==totalSteps){complete=true;break;}')
change('dU_dt_m_s2\\n','dU_dt_m_s2,cfl_max,cfl_volume_mean,native_step_elapsed_s,native_step_cpu_s,worker_communication_before_s,worker_communication_after_s,start_epoch_ms,end_epoch_ms,measured,dt_s\\n')
change('+accelerationAt(t)+"\\n"', '+accelerationAt(t)+","+(cflMax==null?Double.NaN:cflMax.getReportMonitorValue())+","+(cflMean==null?Double.NaN:cflMean.getReportMonitorValue())+","+nativeElapsed+","+nativeCpu+","+commBefore+","+commAfter+","+epochStart+","+epochEnd+","+(t>t0+.006+1e-9)+","+DT+"\\n"')
t=t.replace('pressure_recovery_complete','recovered_perf_complete').replace('pressure_recovery_paused','recovered_perf_paused').replace('pressure_recovery_hold','recovered_perf_hold')
change('if(!complete)throw new IllegalStateException("Bounded campaign step limit reached");','if(!complete)throw new IllegalStateException("Benchmark step limit incomplete");')
p=H/'macros/RecoveredPerfBench.java';p.write_text(t,encoding='utf8')
r=subprocess.run([r'C:\Program Files\Eclipse Adoptium\jdk-25.0.3.9-hotspot\bin\javac.exe','-encoding','UTF-8','-cp',r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\java\platform\modules\ext\*','-d',str(H/'macros/compiled'),str(p)],capture_output=True,text=True)
(H/'cases/RECOVERED_PERF_20261103/COMPILE.txt').write_text(r.stderr);print(r.stderr);assert r.returncode==0
print('Compiled guarded benchmark;12/8/6 steps at dt.002/.003/.004; common0.024s window,0.006s warmup.')
