from pathlib import Path
R=Path(__file__).resolve().parent;out=R/'WaveLinearTraceR12.java'
if out.exists():raise RuntimeError('Macroexists')
m=(R/'WavePhaseBudgetProbeR10.java').read_text().replace('WavePhaseBudgetProbeR10','WaveLinearTraceR12').replace('R10','R12')
m=m.replace('steps!=250','steps!=150').replace('1 ms and 250 steps','1 ms and150steps').replace('"target_time_s",.75','"target_time_s",.65').replace('step%250==0','step%150==0')
m=m.replace('Reporter-only matched diagnostic of phase transport mass errors; same SO 1 ms and 10 inner iterations as R4, no initialization or physics changes; not propagation acceptance','Reporter-only nativephase andAMG per-inner trace0.500to0.650s; sameSO1ms10inner asR4, no initialization/numericalchanges; notpropagationacceptance')
helper=""" private ReportMonitor everyInner(MassConservationErrorReport r){
  ReportMonitor mon=r.createMonitor();mon.setEnabled(true);StarUpdate u=mon.getStarUpdate();u.setEnabled(true);u.getUpdateModeOption().setSelected(StarUpdateModeOption.Type.ITERATION);
  u.getIterationUpdateFrequency().setIterationFrequencyDefinition("1");u.getIterationUpdateFrequency().setStartIterationDefinition("0");u.getIterationUpdateFrequency().setStopEnabled(false);
  if(!String.valueOf(u.getUpdateModeOption().getSelectedElement()).equals("ITERATION"))throw new IllegalStateException("Native monitor notperiteration");
  return mon;
 }
"""
m=m.replace(' public void execute(){',helper+' public void execute(){')
anchor='   double previousMass=Double.NaN,secondPreviousMass=Double.NaN;'
addition="""   ReportMonitor waterInner=everyInner(nativeWater),airInner=everyInner(nativeAir);
   AMGLinearSolver vofAmg=s.getSolverManager().getSolver(SegregatedVofSolver.class).getAMGLinearSolver();
   AMGLinearSolver pressureAmg=s.getSolverManager().getSolver(star.segregatedflow.SegregatedFlowSolver.class).getPressureSolver().getAMGLinearSolver();
   for(AMGLinearSolver amg:List.of(vofAmg,pressureAmg))if(Math.abs(amg.getConvergeTol()-.1)>1e-12||amg.getMaxCycles()!=30||amg.getEpsilon()!=0)throw new IllegalStateException("BaselineAMGsettingsdiffer");
   Files.writeString(out.resolve("linear_trace_setup.json"),json(Map.of("VOF_tolerance",vofAmg.getConvergeTol(),"pressure_tolerance",pressureAmg.getConvergeTol(),"max_cycles",30,"epsilon",0,"trace_start_s",.605,"trace_end_s",.635,"native_monitor_update_mode",String.valueOf(waterInner.getStarUpdate().getUpdateModeOption().getSelectedElement()),"native_monitor_frequency",getter(waterInner.getStarUpdate().getIterationUpdateFrequency(),"getIterationFrequencyDefinition"),"scope","Only reporting/verbositychanges; nativephase monitors everyinner, VOF/pressureAMGLOW onlyaroundspikes")));
   long previousVofCycles=vofAmg.getTotalNumberCycles(),previousPressureCycles=pressureAmg.getTotalNumberCycles();
   Files.writeString(out.resolve("amg_cycle_counts.csv"),"time_s,step,vof_total_cycles,pressure_total_cycles,vof_cycles_this_step,pressure_cycles_this_step\\n");
"""
if m.count(anchor)!=1:raise RuntimeError('Massanchor')
m=m.replace(anchor,addition+anchor)
anchor='s.getSimulationIterator().step(1);done=step;'
if m.count(anchor)!=1:raise RuntimeError('Stepanchor')
m=m.replace(anchor,'double upcoming=initialTime+step*dt;boolean trace=upcoming>=.605-1e-9&&upcoming<=.635+1e-9;vofAmg.setVerbosity(trace?AMGVerbosity.LOW:AMGVerbosity.NONE);pressureAmg.setVerbosity(trace?AMGVerbosity.LOW:AMGVerbosity.NONE);'+anchor)
anchor='     double phaseNet=0;'
m=m.replace(anchor,'     long vc=vofAmg.getTotalNumberCycles(),pcCycles=pressureAmg.getTotalNumberCycles();if(step>0)Files.writeString(out.resolve("amg_cycle_counts.csv"),t+","+step+","+vc+","+pcCycles+","+(vc-previousVofCycles)+","+(pcCycles-previousPressureCycles)+"\\n",StandardOpenOption.APPEND);previousVofCycles=vc;previousPressureCycles=pcCycles;\n'+anchor)
anchor='   XyzInternalTable fieldTable='
exports="""   waterInner.export(out.resolve("native_water_per_inner.csv").toString());airInner.export(out.resolve("native_air_per_inner.csv").toString());
   long waterSamples,airSamples;
   try(var lines=Files.lines(out.resolve("native_water_per_inner.csv"))){waterSamples=lines.filter(x->x.trim().matches("\\\"?[-+]?[0-9].*")).count();}
   try(var lines=Files.lines(out.resolve("native_air_per_inner.csv"))){airSamples=lines.filter(x->x.trim().matches("\\\"?[-+]?[0-9].*")).count();}
   Files.writeString(out.resolve("native_inner_sampling_audit.json"),json(Map.of("expected_inner_samples",done*10,"water_samples",waterSamples,"air_samples",airSamples,"completed_physical_steps",done,"expected_per_step",10)));
   if(waterSamples<done*10||airSamples<done*10||waterSamples>done*10+10||airSamples>done*10+10)throw new IllegalStateException("Nativeperinner samplecount mismatch");
"""
if m.count(anchor)!=1:raise RuntimeError('Exportanchor')
m=m.replace(anchor,exports+anchor)
out.write_text(m);print('R12nativeperinnerandAMGtrace prepared;reportingonly')
