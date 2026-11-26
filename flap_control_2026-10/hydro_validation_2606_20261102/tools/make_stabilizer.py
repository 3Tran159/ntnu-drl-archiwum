from pathlib import Path
h=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102')
t=(h/'macros/SolveHydro.java').read_text(encoding='utf-8').replace('class SolveHydro','class StabilizeHydro')
t=t.replace('caseDir.resolve("smoke_"+runId)','caseDir.resolve("stabilize_"+runId)')
t=t.replace('int done=0,violations=0;','int done=0,violations=0,stableWindows=0;boolean converged=false;List<double[]> windows=new ArrayList<>();')
t=t.replace('Static smoke requires zero angle: ','Stabilization currently requires zero angle: ')
t=t.replace('double dt=s.getSolverManager()', 'Files.copy(caseDir.resolve("normalization.json"),out.resolve("normalization.json"));\nMassFlowReport mass=s.getReportManager().createReport(MassFlowReport.class);mass.setPresentationName("HF_stabilize_mass_"+runId);List<Boundary> open=new ArrayList<>();for(Region r:regions)for(Boundary b:r.getBoundaryManager().getBoundaries())if(b.getBoundaryType() instanceof InletBoundary||b.getBoundaryType() instanceof PressureBoundary)open.add(b);mass.getParts().setObjects(open);\ns.getSimulationIterator().setVerbosity(0);\ndouble dt=s.getSolverManager()')
t=t.replace('bounded 20-step solver and pressure-monitor smoke; not convergence validation','URANS force stabilization: minimum 500 steps, maximum 2000; 100-step windows; no mesh/time reset')
t=t.replace('Starting bounded static smoke, 20 physical steps','URANS stabilization; minimum 500 and maximum 2000 physical steps')
t=t.replace('virtual_h_clear_over_c");','virtual_h_clear_over_c,mass_imbalance_relative");')
t=t.replace('k<=20','k<=2000')
t=t.replace('for(Double a:values)w.write', 'double massRel=Math.abs(mass.getReportMonitorValue())/10800.;w.write(","+massRel);for(Double a:values)w.write')
old='note("Static smoke "+k+"/20 t="+t+" CL="+(fz-buoyancy)/3855.6+" CD="+fx/3855.6+" pabs_min="+pmin);\nif(!safe){status="pressure_screen_failed";break;}status=k==20?"smoke_passed_not_converged":"running";'
new='''windows.add(new double[]{(fz-buoyancy)/3855.6,fx/3855.6,massRel,pmin});
if(k%25==0)note("URANS "+k+"/2000 t="+t+" CL="+(fz-buoyancy)/3855.6+" CD="+fx/3855.6+" pabs_min="+pmin+" stable_windows="+stableWindows);
if(!safe){status="pressure_screen_failed";break;}
status="running";
if(k%100==0){
 s.saveState(out.resolve("checkpoint_step_"+k+".sim").toString());
 if(k>=500){
 int n=windows.size();double cl1=mean(windows,n-100,n,0),cl0=mean(windows,n-200,n-100,0),cd1=mean(windows,n-100,n,1),cd0=mean(windows,n-200,n-100,1);
 double clSpread=spread(windows,n-100,n,0),cdSpread=spread(windows,n-100,n,1);boolean massOk=true;for(int j=n-100;j<n;j++)massOk&=windows.get(j)[2]<1e-4;
 boolean stable=massOk&&Math.abs(cl1-cl0)<.005*Math.max(.01,Math.abs(cl1))&&Math.abs(cd1-cd0)<.01*Math.max(.001,Math.abs(cd1))&&clSpread<.01*Math.max(.01,Math.abs(cl1))&&cdSpread<.02*Math.max(.001,Math.abs(cd1));
 stableWindows=stable?stableWindows+1:0;
 Files.writeString(out.resolve("force_windows.csv"),k+","+cl1+","+cd1+","+clSpread+","+cdSpread+","+massOk+","+stableWindows+"\\n",StandardOpenOption.CREATE,StandardOpenOption.APPEND);
 if(stableWindows>=3){converged=true;status="force_stabilization_passed";break;}
 }
}
if(k==2000)status="not_stabilized_at_step_cap";'''
assert old in t
t=t.replace(old,new)
t=t.replace('"hydrodynamic_convergence_verified\\\":false','"hydrodynamic_convergence_verified\\\":"+converged+"')
t=t.replace('double rv(String n)', 'double mean(List<double[]> a,int lo,int hi,int j){double v=0;for(int k=lo;k<hi;k++)v+=a.get(k)[j];return v/(hi-lo);}\ndouble spread(List<double[]> a,int lo,int hi,int j){double low=Double.POSITIVE_INFINITY,high=Double.NEGATIVE_INFINITY;for(int k=lo;k<hi;k++){low=Math.min(low,a.get(k)[j]);high=Math.max(high,a.get(k)[j]);}return high-low;}\ndouble rv(String n)')
(h/'macros/StabilizeHydro.java').write_text(t,encoding='utf-8')
p=h/'tools/native_launch.py';l=p.read_text(encoding='utf-8')
l=l.replace("'RepairExtrudedMesh.java'}","'RepairExtrudedMesh.java','StabilizeHydro.java'}")
l=l.replace("macro.name=='InitializeHydroControl.java' else 4","macro.name in {'InitializeHydroControl.java','StabilizeHydro.java'} else 4")
p.write_text(l,encoding='utf-8')
print('Stabilizer and bounded launch registration prepared')
