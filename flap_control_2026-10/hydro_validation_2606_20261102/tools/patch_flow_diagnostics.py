from pathlib import Path
R=Path(__file__).resolve().parents[1]
method='''void captureFields(String label)throws Exception{StringBuilder b=new StringBuilder("time="+s.getSolution().getPhysicalTime()+" initialized="+s.getSolution().isInitialized()+"\\n");for(String n:List.of("Density","Pressure","AbsolutePressure","Velocity","TurbulentKineticEnergy","SpecificDissipationRate")){if(!s.getFieldFunctionManager().hasFunction(n))continue;FieldFunction f=s.getFieldFunctionManager().getFunction(n);if(n.equals("Velocity"))f=f.getMagnitudeFunction();MinReport mi=s.getReportManager().createReport(MinReport.class);MaxReport ma=s.getReportManager().createReport(MaxReport.class);mi.getParts().setObjects(regions);ma.getParts().setObjects(regions);mi.setFieldFunction(f);ma.setFieldFunction(f);b.append(n+" min="+mi.getReportMonitorValue()+" max="+ma.getReportMonitorValue()+"\\n");s.getReportManager().removeObjects(mi,ma);}Files.writeString(out.resolve("fields_"+label+".txt"),b.toString());}
'''
for name in ['InitializeHydroControl.java','SolveHydro.java']:
 p=R/'macros'/name;t=p.read_text()
 if 'void captureFields(' in t:continue
 t=t.replace('public void execute(){',method+'public void execute(){')
 if name=='InitializeHydroControl.java':
  t=t.replace('List<double[]> samples=', 'captureFields("before_steady");List<double[]> samples=')
  t=t.replace('s.saveState(out.resolve("steady_checkpoint.sim")','captureFields("steady_completed");s.saveState(out.resolve("steady_checkpoint.sim")')
  t=t.replace('s.saveState(out.resolve("URANS_ready.sim")','captureFields("converted_URANS");s.saveState(out.resolve("URANS_ready.sim")')
 else:
  t=t.replace('s.saveState(out.resolve("singlephase_initial_verified.sim")','captureFields("before_transient");s.saveState(out.resolve("singlephase_initial_verified.sim")')
  t=t.replace('s.getSimulationIterator().step(1);done=k;', 's.getSimulationIterator().step(1);done=k;if(k<=2)captureFields("after_step_"+k);')
 p.write_text(t,encoding='utf8')
print('Diagnostics added to next macro snapshots only; current job unchanged')
