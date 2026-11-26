from pathlib import Path
import subprocess,hashlib
h=Path(__file__).resolve().parents[1]
src=h/'cases/SP_C_split0_overset/SP_C_mesh_ready.sim'
assert hashlib.file_digest(src.open('rb'),'sha256').hexdigest()=='8d4692832503adba9a8dca8b1583c56ea57a6f5979c2887b3dca1a70bb8f8eb6'
s=(h/'macros/InitializeHydroControl.java').read_text(encoding='utf8')
d=(h/'macros/C0DistanceInterpolationTest.java').read_text(encoding='utf8')
s=s.replace('class InitializeHydroControl','class FreshC0DistanceInit')
s=s.replace('out=base.resolve("steady_init_"+System.getenv("NTNU_HYDRO_RUN_ID"))','out=root.resolve("cases/SP_C_split0_overset/c0_distance_fresh_"+System.getenv("NTNU_HYDRO_RUN_ID"))')
s=s.replace('if(!input.startsWith(root.resolve("cases"))||!List.of("SP_A","SP_B","SP_C").contains(variant))throw new IllegalStateException("Own singlephase case required");',
'''if(!input.equals(root.resolve("cases/SP_C_split0_overset/SP_C_mesh_ready.sim"))||!"SP_C".equals(variant))throw new IllegalStateException("Only protected pre-motion mesh source allowed");
if(Math.abs(s.getSolution().getPhysicalTime())>1e-12)throw new IllegalStateException("Fresh uninitialized mesh required; solved checkpoints protected");
java.security.MessageDigest md=java.security.MessageDigest.getInstance("SHA-256");
try(InputStream stream=Files.newInputStream(input)){byte[] chunk=new byte[1048576];int n;while((n=stream.read(chunk))!=-1)md.update(chunk,0,n);}
if(!java.util.HexFormat.of().formatHex(md.digest()).equals("8d4692832503adba9a8dca8b1583c56ea57a6f5979c2887b3dca1a70bb8f8eb6"))throw new IllegalStateException("Source mesh fingerprint changed");
''')
s=s.replace('s.getSolution().clearSolution(Solution.Clear.History);','')
old='SegregatedFlowSolver flow=s.getSolverManager().getSolver(SegregatedFlowSolver.class);'
new='''for(Interface iface:s.getInterfaceManager().getObjects())if(iface instanceof IndirectRegionInterface){
IndirectRegionInterface in=(IndirectRegionInterface)iface;
if(in.getTreatErrorAsWarning()||!in.getConditions().get(OversetHoleCuttingOptions.class).getBoolean("ZeroDonorCheckOption"))throw new IllegalStateException("Strict Overset guards required");
in.getConditions().get(OversetMeshInterpolationOption.class).setSelected(OversetMeshInterpolationOption.Type.DISTANCE);
s.getInterfaceManager().initializeInterfaces(List.of(iface));}
Files.writeString(out.resolve("numerical_change.txt"),"Fresh initialization on protected pre-motion mesh; static 0 degrees; DISTANCE interpolation and flux correction. Same geometry and physical boundary conditions. Steady initialization only; no time reset of a solved checkpoint; no mesh regeneration. All results diagnostic, not training.");
SegregatedFlowSolver flow=s.getSolverManager().getSolver(SegregatedFlowSolver.class);'''
assert old in s;s=s.replace(old,new)
s=s.replace('if(!s.getSolution().isInitialized())s.getSolution().initializeSolution();',
'''s.getSolution().initializeSolution();
if(((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount()!=361532)throw new IllegalStateException("Source mesh size changed");
auditFull("fresh_initialized",361532);
''')
s=s.replace('captureFields("before_steady");List<double[]> samples=', '''captureFields("before_steady");captureComparison("fresh_initialized");
UserFieldFunction omegaFloor=field("Fresh_C0_omega_floor","($OversetCellStatus == 0 && $SpecificDissipationRate <= <1.0001e-10 /s>) ? 1 : 0",new Dimensions());
UserFieldFunction kFloor=field("Fresh_C0_k_floor","($OversetCellStatus == 0 && $TurbulentKineticEnergy <= <1.0001e-10 J/kg>) ? 1 : 0",new Dimensions());
ElementCountReport omegaCount=count("Fresh C0 omega floor",omegaFloor,.5,1.5,s.getRepresentationManager().getObject("Volume Mesh"));
ElementCountReport kCount=count("Fresh C0 k floor",kFloor,.5,1.5,s.getRepresentationManager().getObject("Volume Mesh"));
ElementCountReport errorCount=count("Fresh C0 errors",namedField("Overset Error Status","OversetErrorStatus"),.5,100,s.getRepresentationManager().getObject("Volume Mesh"));
MaxReport viscosityMax=s.getReportManager().createReport(MaxReport.class);viscosityMax.getParts().setObjects(regions);viscosityMax.setFieldFunction(s.getFieldFunctionManager().getFunction("TurbulentViscosityRatio"));
List<double[]> samples=''')
s=s.replace('rho_min,rho_max\\n','rho_min,rho_max,omega_floor_cells,k_floor_cells,max_turbulent_viscosity_ratio,overset_error_cells\\n')
s=s.replace('if(k==10)checkPose("first_steady_block");','if(k==10){checkPose("first_steady_block");auditFull("after_first_step",361532);}')
s=s.replace('rho0,rho1));w.flush();samples.add(new double[]{cl,cd,p,bal});',
'''rho0,rho1).stripTrailing());double omega=omegaCount.getReportMonitorValue(),kfloor=kCount.getReportMonitorValue(),visc=viscosityMax.getReportMonitorValue(),oe=errorCount.getReportMonitorValue();
w.write(","+omega+","+kfloor+","+visc+","+oe+"\\n");w.flush();samples.add(new double[]{cl,cd,p,bal,mh,omega,kfloor,visc});
if(!Double.isFinite(oe+omega+kfloor+visc)||oe>0)throw new IllegalStateException("Overset or field diagnostic invalid");
''')
s=s.replace('if(k%50==0)note(', 'if(k%250==0){captureComparison("iter_"+k);auditFull("iter_"+k,361532);s.saveState(out.resolve("steady_iter_"+k+".sim").toString());}\\nif(k%50==0)note('.replace('\\n','\n'))
# Stop at force stabilization for Work review, explicitly distinguish suspect fields.
s=s.replace('checkPose("steady_completed");captureFields("steady_completed");',
'''checkPose("steady_completed");captureFields("steady_completed");captureComparison("final");auditFull("final",361532);
double lastOmega=omegaCount.getReportMonitorValue(),lastK=kCount.getReportMonitorValue(),lastVisc=viscosityMax.getReportMonitorValue();
boolean clean=lastOmega==0&&lastK==0&&lastVisc<99999;
''')
s=s.replace('if(k%500==0)s.saveState(out.resolve("steady_iter_"+k+".sim").toString());','')
start=s.index('Files.writeString(out.resolve("initialization_status.json"),')
end=s.index('}catch(Exception e){try{Files.writeString(out.resolve("initialization_error.txt")',start)
s=s[:start]+'''String result=Files.exists(root.getParent().resolve("STOP_OWNED_CFD.json"))?"paused_by_marker":(converged?(clean?"steady_diagnostic_ready":"steady_suspect_fields"):"steady_initialization_incomplete");
String json="{\\"status\\":\\""+result+"\\",\\"iterations\\":"+iterations+",\\"saved_time_s\\":"+s.getSolution().getPhysicalTime()+",\\"steady_initialization_only\\":true,\\"force_windows_stable\\":"+converged+",\\"omega_floor_cells\\":"+lastOmega+",\\"k_floor_cells\\":"+lastK+",\\"max_turbulent_viscosity_ratio\\":"+lastVisc+",\\"scientific_approved\\":false,\\"hydrodynamic_convergence_verified\\":false,\\"training_approved\\":false}";
Files.writeString(out.resolve("initialization_status.json"),json);Files.writeString(out.resolve("status.json"),json);note(result);
''' +s[end:]
# Above Python regular triple string consumes escapes; replace the generated Java JSON line explicitly.
a=s.index('String json=');b=s.index('\nFiles.writeString(out.resolve("initialization_status.json")',a)
s=s[:a]+r'''String json="{\"status\":\""+result+"\",\"iterations\":"+iterations+",\"saved_time_s\":"+s.getSolution().getPhysicalTime()+",\"steady_initialization_only\":true,\"force_windows_stable\":"+converged+",\"omega_floor_cells\":"+lastOmega+",\"k_floor_cells\":"+lastK+",\"max_turbulent_viscosity_ratio\":"+lastVisc+",\"scientific_approved\":false,\"hydrodynamic_convergence_verified\":false,\"training_approved\":false}";'''+s[b:]
# Copy tested field and full-plane diagnostics, without continuation-only saved-solution checks.
helpers=d[d.index('FieldFunction namedField'):d.index('void verifySavedControl')]
helpers+=d[d.index('void captureComparison'):d.index('public void execute()')]
s=s.replace('public void execute(){',helpers+'\npublic void execute(){')
# The fresh initializer deliberately stops in steady mode, preserving its numerical state.
assert 'if(converged){pc.disableModel' not in s
assert 'clearSolution(' not in s
p=h/'macros/FreshC0DistanceInit.java';p.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(p)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
print(r.stderr);assert r.returncode==0
print('Prepared and compiled FreshC0DistanceInit.java; source hash verified; not launched or queued.')
