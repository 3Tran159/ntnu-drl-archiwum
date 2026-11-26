from pathlib import Path
import subprocess,sys
H=Path(__file__).resolve().parents[1]
src=(H/'macros/RampPlus2Run.java').read_text()
prefix=src[:src.index('final boolean SMOKE=')]
body=src[src.index('public void execute()'):]
body=body.replace('ramp_plus2_', 'speed_plus2_')
body=body.replace('int goodWindows=0;', 'int goodWindows=0;int stage=0;double stageStart=0;int holdSteps=0;')
a=body.index('if(SMOKE){');b=body.index('for(Region r:',a)
body=body[:a]+r'''
Properties auth=new Properties();try(Reader reader=Files.newBufferedReader(root.resolve("audit/SPEED_PLUS2_RUNTIME.properties"))){auth.load(reader);}
if(!input.equals(Paths.get(auth.getProperty("input")))||Math.abs(t0-Double.parseDouble(auth.getProperty("time_s")))>1e-9||s.getSimulationIterator().getCurrentIteration()!=Integer.parseInt(auth.getProperty("iteration")))throw new IllegalStateException("Authorized checkpoint mismatch");
if(!SMOKE){stage=Integer.parseInt(auth.getProperty("stage","0"));stageStart=Double.parseDouble(auth.getProperty("stage_start_s","0"));if(stage<0||stage>4)throw new IllegalStateException("Stage out of range");}
''' +body[b:]
a=body.index('if(SMOKE&&!((RotationAngle)');b=body.index('AreaAverageReport[]',a)
body=body[:a]+r'''
if(!((RotationAngle)rot.getRotationSpecification()).getRotationAngle().getDefinition().equals("<2 deg>"))throw new IllegalStateException("Fixed +2deg law required");
Vector3 point=rot.transformInitialCoordinate(new Vector3(xh+.2,.02,zh));double angle=-Math.toDegrees(Math.atan2(point.z-zh,point.x-xh));if(Math.abs(angle-2)>1e-5)throw new IllegalStateException("Starting pose mismatch");
savedFlapBounds=flapBounds();
if(SMOKE){
 setU(10);velocity10(pc.getInitialConditions().get(VelocityProfile.class));
 pc.getInitialConditions().get(KwTurbSpecOption.class).setSelected(KwTurbSpecOption.Type.INTENSITY_VISCOSITY_RATIO);constant(pc.getInitialConditions().get(TurbulenceIntensityProfile.class),.001);constant(pc.getInitialConditions().get(TurbulentViscosityRatioProfile.class),10);
 pressure(pc.getInitialConditions().get(InitialPressureProfile.class),s.getFieldFunctionManager().getFunction("HYDRO_PiezometricZero"));
 fs.setContinuityInitialization(true);fs.setContinuityInitIterations(100);fs.setContinuityInitTolerance(1e-6);
 // Independent experiment only. Clear inherited 18m/s fields/history in memory; never save the source.
 s.getSolution().clearSolution(Solution.Clear.History,Solution.Clear.Fields);
 s.getSolution().initializeSolution();t0=s.getSolution().getPhysicalTime();stageStart=t0;
 checkPose("fresh_initialization");
 if(((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount()!=333939)throw new IllegalStateException("Initialization changed mesh");
 Files.writeString(out.resolve("initialization.txt"),"New independent fixed+2 experiment. Uniform10m/s, hydrostatic absolute pressure through zero piezometric pressure, SST I0.001/viscosityRatio10; native continuity initialization100/tolerance1e-6. Fresh fields/history only, no remesh. SECOND_ORDER space/time, dt0.002, inner40, URF0.8/0.2 unchanged. NOT steady or scientifically accepted. Source preserved. Initial clock="+t0);
}else setU(speedAt(stage,stageStart,t0));
''' +body[b:]
# Use actual inlet flow to normalize mass imbalance at each speed.
body=body.replace('mass.getParts().setObjects(outer);','mass.getParts().setObjects(outer);MassFlowReport incoming=s.getReportManager().createReport(MassFlowReport.class);List<Boundary> inlets=new ArrayList<>();for(Boundary b:outer)if(b.getBoundaryType() instanceof InletBoundary)inlets.add(b);incoming.getParts().setObjects(inlets);')
body=body.replace('/10800.','/Math.max(1e-20,Math.abs(incoming.getReportMonitorValue()))')
body=body.replace('center_error_m\\n','center_error_m,U_m_s,target_U_m_s,stage,phase,Re,qS_N\\n')
body=body.replace('zone,pabs_Pa,x_m,y_m,z_m\\n','zone,pabs_Pa,x_m,y_m,z_m,U_m_s,stage\\n')
body=body.replace('+loc[2]+"\\n"','+loc[2]+","+currentU+","+stage+"\\n"')
body=body.replace('for(int i=1;i<=(SMOKE?5:(int)Math.round((1.25-t0)/.002));i++)','for(int i=1;i<=(SMOKE?5:3000);i++)')
body=body.replace('double cb=comm.getReportMonitorValue();','double nextTime=s.getSolution().getPhysicalTime()+.002;setU(speedAt(stage,stageStart,nextTime));boolean transition=stage>0&&nextTime<stageStart+.2-1e-9;\ndouble cb=comm.getReportMonitorValue();')
a=body.index('point=rot.transformInitialCoordinate',body.index('for(int i=1'));b=body.index('w.write(i+',a)
body=body[:a]+r'''
point=rot.transformInitialCoordinate(new Vector3(xh+.2,.02,zh));double actual=-Math.toDegrees(Math.atan2(point.z-zh,point.x-xh)),cmd=2,rate=0,ce=0;for(int j=0;j<3;j++)ce=Math.max(ce,Math.abs(center[j].getReportMonitorValue()-startCenter[j]));
if(Math.abs(actual-2)>1e-5||ce>1e-7)throw new IllegalStateException("Fixed flap moved");checkPose("latest");
''' +body[b:]
body=body.replace('+ce+"\\n"','+ce+","+currentU+","+(10+2*stage)+","+stage+","+(transition?"U_TRANSITION":"SETTLING")+","+(1190000*currentU)+","+(11.9*currentU*currentU)+"\\n"')
a=body.index('note("Ramp step=');b=body.index('\n}}',a)
body=body[:a]+r'''
note("SpeedSweep step="+i+" time="+t+" U="+currentU+" stage="+stage+" pabs="+p);
writeProgress(stage,stageStart,t,i,transition?"U_TRANSITION":"SETTLING");
if(!transition){holdSteps++;windows.add(new double[]{cl,cd,mh,p,bal,fx,fz});}
if(i%25==0){boolean residualOk=residualGate();boolean forceOk=forceStable(windows);goodWindows=forceOk&&residualOk?goodWindows+1:0;
 Files.writeString(out.resolve("convergence_latest.json"),"{\"time\":"+t+",\"stage\":"+stage+",\"U\":"+currentU+",\"settling_samples\":"+windows.size()+",\"force_gate\":"+forceOk+",\"residual_gate\":"+residualOk+",\"consecutive_passes\":"+goodWindows+"}");
 if(!SMOKE&&holdSteps>=200&&goodWindows>=2){
  String name="stage_U"+(10+2*stage)+"_accepted";captureComparison(name);auditFull(name,333939);saveVerified(name+".sim",stage,stageStart,false);
  int n=windows.size();String line=(10+2*stage)+","+t+","+mean(windows,n-25,n,0)+","+mean(windows,n-25,n,1)+","+mean(windows,n-25,n,2)+","+mean(windows,n-25,n,3)+","+mean(windows,n-25,n,5)+","+mean(windows,n-25,n,6)+","+holdSteps+",NUMERICAL_POC_ACCEPTED_NOT_QUANTITATIVE_VALIDATION\n";Files.writeString(out.resolve("static_results.csv"),line,StandardOpenOption.APPEND);
  if(stage==4){stable=true;break;}
  stage++;stageStart=t;holdSteps=0;goodWindows=0;windows.clear();writeProgress(stage,stageStart,t,i,"U_TRANSITION");
 }
}
if(!SMOKE&&holdSteps>=500)throw new IllegalStateException("No stabilization within500 fixed-U steps; next speed blocked");
if(!SMOKE&&i%100==0)saveVerified("checkpoint_step_"+i+".sim",stage,stageStart,true);
''' +body[b:]
body=body.replace('try(BufferedWriter w=', 'Files.writeString(out.resolve("static_results.csv"),"U_m_s,time_s,CL,CD,Mh_Nm,pabs_mean_min_Pa,Fx_N,Fz_N,settling_samples,acceptance\\n");\ntry(BufferedWriter w=')
body=body.replace('int stage=0;', 'List<double[]> pressureSamples=new ArrayList<>();int zoneIndex=0;int stage=0;')
body=body.replace('for(String zone:List.of("fixed"', 'zoneIndex=0;for(String zone:List.of("fixed"')
body=body.replace('pw.write(i+', 'pressureSamples.add(new double[]{zoneIndex++,pv,loc[0],loc[1],loc[2],t,currentU});pw.write(i+')
body=body.replace('pabs_mean_min_Pa','pabs_min_last25_Pa')
body=body.replace('+mean(windows,n-25,n,3)+', '+minColumn(windows,n-25,n,3)+')
body=body.replace('int n=windows.size();String line=', 'int n=windows.size();exportStaticPressure(pressureSamples,stage);String line=')
body=body.replace('windows.clear();writeProgress', 'windows.clear();pressureSamples.clear();writeProgress')
body=body.replace('try(BufferedWriter w=', '''if(!SMOKE&&Files.exists(input.getParent().resolve("static_results.csv")))Files.copy(input.getParent().resolve("static_results.csv"),out.resolve("static_results.csv"),StandardCopyOption.REPLACE_EXISTING);
Files.writeString(out.resolve("static_pressure_results.csv"),"U_m_s,zone,pabs_min_last25_Pa,x_m,y_m,z_m,time_s\\n");
if(!SMOKE&&Files.exists(input.getParent().resolve("static_pressure_results.csv")))Files.copy(input.getParent().resolve("static_pressure_results.csv"),out.resolve("static_pressure_results.csv"),StandardCopyOption.REPLACE_EXISTING);
try(BufferedWriter w=''')
body=body.replace('double nextTime=', 'if(Files.getFileStore(out).getUsableSpace()<7L*1024*1024*1024)throw new IllegalStateException("Disk reserve below7GiB; next speed blocked");\ndouble nextTime=')
body=body.replace('s.saveState(out.resolve("checkpoint.sim").toString());','saveVerified("checkpoint.sim",stage,stageStart,false);')
body=body.replace('"ramp_smoke_passed"','"speed_smoke_passed"').replace('"ramp_stable_candidate"','"speed_sweep_complete"').replace('"ramp_limit_reached"','"speed_limit_reached"')
body=body.replace('s.saveState(out.resolve(paused?"paused_checkpoint.sim":"error_checkpoint.sim").toString());','saveVerified(paused?"paused_checkpoint.sim":"error_checkpoint.sim",stage,stageStart,false);')
body=body.replace('ramp_paused','speed_paused').replace('ramp_failed','speed_failed')
methods=r'''
double currentU=10;
Deque<Path> rolling=new ArrayDeque<>();
double minColumn(List<double[]> rows,int lo,int hi,int col){double m=Double.POSITIVE_INFINITY;for(int j=lo;j<hi;j++)m=Math.min(m,rows.get(j)[col]);return m;}
void exportStaticPressure(List<double[]> rows,int stage)throws Exception{String[] zones={"fixed","flap","near","gap","liquid_all"};for(int z=0;z<5;z++){double[] best=null;for(int i=Math.max(0,rows.size()-125);i<rows.size();i++){double[] r=rows.get(i);if(r[0]==z&&(best==null||r[1]<best[1]))best=r;}if(best==null)throw new IllegalStateException("Missing static pressure window");Files.writeString(out.resolve("static_pressure_results.csv"),(10+2*stage)+","+zones[z]+","+best[1]+","+best[2]+","+best[3]+","+best[4]+","+best[5]+"\n",StandardOpenOption.APPEND);}}
void velocity10(VectorProfile p){p.setMethod(ConstantVectorProfileMethod.class);p.getMethod(ConstantVectorProfileMethod.class).getQuantity().setComponents(10,0,0);}
double speedAt(int stage,double start,double t){if(stage==0)return 10;double u=Math.max(0,Math.min(1,(t-start)/.2));return 8+2*stage+2*(10*u*u*u-15*Math.pow(u,4)+6*Math.pow(u,5));}
void setU(double u)throws Exception{
 currentU=u;for(Region r:regions)for(Boundary b:r.getBoundaryManager().getBoundaries())if(b.getBoundaryType() instanceof InletBoundary){if(b.getConditions().get(InletVelocityOption.class).getSelected()!=InletVelocityOption.Type.COMPONENTS.getValue())throw new IllegalStateException("Inlet component specification changed");VectorProfile p=b.getValues().get(VelocityProfile.class);p.setMethod(ConstantVectorProfileMethod.class);p.getMethod(ConstantVectorProfileMethod.class).getQuantity().setComponents(u,0,0);turbulence(b);}
 double qs=11.9*u*u;((ExpressionReport)s.getReportManager().getReport("HF_CL_hydro")).setDefinition("(${HF_Fz_NReport} - <22.666963538808645 N>)/<"+qs+" N>");((ExpressionReport)s.getReportManager().getReport("HF_CD")).setDefinition("${HF_Fx_NReport}/<"+qs+" N>");
 Files.writeString(out.resolve("normalization.json"),"{\"rho\":1000,\"mu\":0.001,\"U\":"+u+",\"Re\":"+(1190000*u)+",\"qS_N\":"+qs+",\"reference_area_m2\":0.0238,\"buoyancy_N\":22.666963538808645,\"pabs_threshold_Pa\":12339.214766776897,\"flap_deg\":2}");
}
boolean forceStable(List<double[]> windows){if(windows.size()<50)return false;int n=windows.size();boolean ok=true;for(int col=0;col<3;col++){double a=mean(windows,n-25,n,col),b=mean(windows,n-50,n-25,col),lo=Double.POSITIVE_INFINITY,hi=-lo;for(int i=n-25;i<n;i++){lo=Math.min(lo,windows.get(i)[col]);hi=Math.max(hi,windows.get(i)[col]);}ok&=Double.isFinite(a+b+lo+hi)&&Math.abs(a-b)<.005*Math.max(1e-6,Math.abs(a))&&(hi-lo)<.01*Math.max(1e-6,Math.abs(a));}return ok;}
void writeProgress(int stage,double start,double t,int step,String phase)throws Exception{Files.writeString(out.resolve("sweep_progress.json"),"{\"experiment_id\":\"SPEED_SWEEP_PLUS2_20261103\",\"stage\":"+stage+",\"stage_start_s\":"+start+",\"time_s\":"+t+",\"step\":"+step+",\"U\":"+currentU+",\"target_U\":"+(10+2*stage)+",\"phase\":\""+phase+"\",\"static_results\":\"static_results.csv\",\"training_approved\":false}");}
void saveVerified(String name,int stage,double stageStart,boolean rotate)throws Exception{
 Path cp=out.resolve(name);if(Files.exists(cp))throw new IllegalStateException("Never overwrite checkpoint");s.saveState(cp.toString());if(Files.size(cp)<100000000)throw new IllegalStateException("Checkpoint too small");
 java.security.MessageDigest md=java.security.MessageDigest.getInstance("SHA-256");try(InputStream in=Files.newInputStream(cp)){byte[] buf=new byte[1048576];int n;while((n=in.read(buf))>0)md.update(buf,0,n);}String hash=HexFormat.of().formatHex(md.digest());
 String j="{\"checkpoint\":\""+cp.toString().replace("\\","/")+"\",\"bytes\":"+Files.size(cp)+",\"sha256\":\""+hash+"\",\"time_s\":"+s.getSolution().getPhysicalTime()+",\"iteration\":"+s.getSimulationIterator().getCurrentIteration()+",\"stage\":"+stage+",\"stage_start_s\":"+stageStart+",\"U\":"+currentU+",\"native_save_returned\":true}";
 Files.writeString(out.resolve(name+".json"),j);Files.writeString(out.resolve("checkpoint_latest.json.tmp"),j);Files.move(out.resolve("checkpoint_latest.json.tmp"),out.resolve("checkpoint_latest.json"),StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
 if(rotate){rolling.add(cp);while(rolling.size()>2){Path old=rolling.removeFirst();if(!old.toAbsolutePath().getParent().equals(out.toAbsolutePath())||!old.getFileName().toString().matches("checkpoint_step_[0-9]+.sim"))throw new IllegalStateException("Retention path check");Files.delete(old);}}
}
<T extends Report>T reuseReport(Class<T> c){for(Report r:s.getReportManager().getObjects())if(c.isInstance(r))return c.cast(r);return s.getReportManager().createReport(c);}
'''
residual=src[src.index('boolean residualGate()'):src.index('<T extends Report>')]
for name,smoke in [('SpeedSweepPlus2Smoke',True),('SpeedSweepPlus2Run',False)]:
    if smoke and '--run-only' in sys.argv:continue
    text=prefix.replace('class RampPlus2Run','class '+name)+f'final boolean SMOKE={str(smoke).lower()};\n'+methods+residual+body
    path=H/'macros'/f'{name}.java';path.write_text(text,encoding='utf8')
    r=subprocess.run([r'C:\Program Files\Eclipse Adoptium\jdk-25.0.3.9-hotspot\bin\javac.exe','-encoding','UTF-8','-cp',r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\java\platform\modules\ext\*','-d',str(H/'macros/compiled'),str(path)],capture_output=True,text=True)
    print(name,r.returncode,r.stderr);assert r.returncode==0
