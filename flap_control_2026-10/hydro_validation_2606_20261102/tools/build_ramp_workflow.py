from pathlib import Path
import subprocess,json,math,datetime
H=Path(__file__).resolve().parents[1]
source=(H/'macros/BenchmarkStaticPlus2.java').read_text();prefix=source[:source.index('public void execute()')]
kin=(H/'macros/KinematicPoc333939.java').read_text();audit=kin[kin.index('void auditFull('):kin.index('void scene(')]
# Reuse the full native Overset audit with temporary native objects removed after export.
a=prefix.index('void auditFull(');b=prefix.index('void captureComparison(',a);prefix=prefix[:a]+audit+'\n'+prefix[b:]
body=source[source.index('public void execute()'):]
def rep(a,b):
 global body
 assert body.count(a)==1,(a,body.count(a));body=body.replace(a,b)
rep('int done=0;double t0=', 'int done=0;boolean stable=false;List<double[]> windows=new ArrayList<>();int goodWindows=0;double t0=')
rep('plus2_benchmark_', 'ramp_plus2_')
a=body.index('if(!input.equals(');b=body.index('for(Region r:',a)
body=body[:a]+r'''
if(SMOKE){
 if(!input.equals(root.resolve("cases/SP_C_split0_overset/relocation_reopen_20261103_082325/C0_recovered_t065.sim"))||Math.abs(t0-.65)>1e-9||s.getSimulationIterator().getCurrentIteration()!=11560)throw new IllegalStateException("C0 t0.650 source required");
}else{
 Properties auth=new Properties();try(Reader reader=Files.newBufferedReader(root.resolve("audit/RAMP_PLUS2_RUNTIME.properties"))){auth.load(reader);}
 if(!input.equals(Paths.get(auth.getProperty("input")))||Math.abs(t0-Double.parseDouble(auth.getProperty("time_s")))>1e-9||s.getSimulationIterator().getCurrentIteration()!=Integer.parseInt(auth.getProperty("iteration")))throw new IllegalStateException("Approved continuation checkpoint mismatch");
 if(t0<.65||t0>=1.25)throw new IllegalStateException("Resume clock outside bounded experiment");
}
''' +body[b:]
a=body.index('RotatingMotion rot=');b=body.index('List<Boundary> outer=',a)
body=body[:a]+r'''
RotatingMotion rot=(RotatingMotion)s.getRegionManager().getRegion("FlapOverset").getValues().get(MotionSpecification.class).getMotion();
if(SMOKE&&!((RotationAngle)rot.getRotationSpecification()).getRotationAngle().getDefinition().equals("<0 deg>"))throw new IllegalStateException("C0 zero angle required");
if(!SMOKE&&!((RotationAngle)rot.getRotationSpecification()).getRotationAngle().getDefinition().equals(LAW))throw new IllegalStateException("Ramp law changed");
((RotationAngle)rot.getRotationSpecification()).getRotationAngle().setDefinition(LAW);
Vector3 point=rot.transformInitialCoordinate(new Vector3(xh+.2,.02,zh));double angle=-Math.toDegrees(Math.atan2(point.z-zh,point.x-xh));if(Math.abs(angle-ramp(t0))>1e-5)throw new IllegalStateException("Starting pose mismatch");
AreaAverageReport[] center=new AreaAverageReport[3];double[] startCenter=new double[3];for(int j=0;j<3;j++){center[j]=s.getReportManager().createReport(AreaAverageReport.class);center[j].getParts().setObjects(flap);center[j].setFieldFunction(s.getFieldFunctionManager().getFunction("Position").getComponentFunction(j));startCenter[j]=center[j].getReportMonitorValue();}
''' +body[b:]
a=body.index('Files.writeString(out.resolve("preflight.json")');b=body.index('try(BufferedWriter',a)
body=body[:a]+r'''Files.writeString(out.resolve("preflight.json"),"{\"time\":"+t0+",\"iteration\":"+s.getSimulationIterator().getCurrentIteration()+",\"actual_angle_deg\":"+angle+",\"flow_frozen\":false,\"dt\":0.002,\"inner\":40,\"mesh\":333939,\"initial_CL\":"+rv("HF_CL_hydro")+",\"initial_CD\":"+rv("HF_CD")+",\"initial_Mh\":"+rv("HF_Mh_Nm")+"}");
'''+body[b:]
rep('measured,flap_angle_deg,flap_angular_velocity_deg_s\\n','measured,flap_angle_deg,flap_angular_velocity_deg_s,measured_angle_deg,center_error_m\\n')
rep('for(int i=1;i<=10;i++)','for(int i=1;i<=(SMOKE?5:(int)Math.round((1.25-t0)/.002));i++)')
rep('\nw.write(i+","+t+',r'''
point=rot.transformInitialCoordinate(new Vector3(xh+.2,.02,zh));double actual=-Math.toDegrees(Math.atan2(point.z-zh,point.x-xh)),cmd=ramp(t),rate=rampRate(t),a=Math.toRadians(cmd-ramp(t0));double dx=startCenter[0]-xh,dz=startCenter[2]-zh,ce=0;double[] expected={xh+dx*Math.cos(a)+dz*Math.sin(a),startCenter[1],zh-dx*Math.sin(a)+dz*Math.cos(a)};for(int j=0;j<3;j++)ce=Math.max(ce,Math.abs(center[j].getReportMonitorValue()-expected[j]));
if(Math.abs(actual-cmd)>1e-5||ce>1e-7)throw new IllegalStateException("Rigid body motion mismatch");
w.write(i+","+t+''')
rep('+(i>3)+",2,0\\n"','+false+","+cmd+","+rate+","+actual+","+ce+"\\n"')
rep('checkPose("step_"+i);note("Benchmark step="+i+" time="+t+" solver_seconds="+seconds);',r'''
auditFull("latest",333939);
note("Ramp step="+i+" time="+t+" delta_deg="+cmd+" angular_rate="+rate+" pabs="+p);
if(t>=.85-1e-9)windows.add(new double[]{cl,cd,mh,p,bal});
int globalStep=(int)Math.round((t-.65)/.002);
if(globalStep%25==0){boolean residualOk=residualGate();Files.writeString(out.resolve("convergence_latest.json"),"{\"time\":"+t+",\"post_ramp_samples\":"+windows.size()+",\"residual_gate\":"+residualOk+"}");
 if(windows.size()>=50){boolean forceOk=true;int n=windows.size();for(int col=0;col<3;col++){double aa=mean(windows,n-25,n,col),bb=mean(windows,n-50,n-25,col),lo=Double.POSITIVE_INFINITY,hi=-lo;for(int wi=n-25;wi<n;wi++){lo=Math.min(lo,windows.get(wi)[col]);hi=Math.max(hi,windows.get(wi)[col]);}forceOk&=Math.abs(aa-bb)<.005*Math.max(1e-6,Math.abs(aa))&&(hi-lo)<.01*Math.max(1e-6,Math.abs(aa));}goodWindows=forceOk&&residualOk?goodWindows+1:0;if(goodWindows>=2&&windows.size()>=75){stable=true;break;}}
}
if(globalStep%50==0){captureComparison("checkpoint_"+globalStep);s.saveState(out.resolve("checkpoint_step_"+i+".sim").toString());}
''')
a=body.index('captureFields("final")');b=body.index('}catch(Exception e)',a)
body=body[:a]+r'''
captureFields("final");captureComparison("final");auditFull("final",333939);scene();s.saveState(out.resolve("checkpoint.sim").toString());
String status=SMOKE?"ramp_smoke_passed":stable?"ramp_stable_candidate":"ramp_limit_reached";
Files.writeString(out.resolve("status.json"),"{\"status\":\""+status+"\",\"steps\":"+done+",\"saved_time_s\":"+s.getSolution().getPhysicalTime()+",\"iteration\":"+s.getSimulationIterator().getCurrentIteration()+",\"force_windows_stable\":"+stable+",\"scientific_approved\":false,\"training_approved\":false}");
'''+body[b:]
rep('"benchmark_failed"','"ramp_failed"') if '"benchmark_failed"' in body else None
body=body.replace('benchmark_failed','ramp_failed')
# Pauses save a recoverable state and have a distinct outcome; physics failures stay failed.
body=body.replace('s.saveState(out.resolve("error_checkpoint.sim").toString());', 'boolean paused=e.getMessage()!=null&&e.getMessage().equals("Pause requested");s.saveState(out.resolve(paused?"paused_checkpoint.sim":"error_checkpoint.sim").toString());')
body=body.replace('\\\"status\\\":\\\"ramp_failed\\\"','\\\"status\\\":\\\""+(paused?"ramp_paused":"ramp_failed")+"\\\"')
body=body.replace('}catch(Exception ex){s.println(ex);}', 'if(paused)return;}catch(Exception ex){s.println(ex);}')
u='(($Time - <0.65 s>)/<0.2 s>)'
law=f'($Time <= <0.65 s>) ? <0 deg> : (($Time >= <0.85 s>) ? <2 deg> : <2 deg>*(10*pow({u},3)-15*pow({u},4)+6*pow({u},5)))'
methods=r'''
double ramp(double t){double u=Math.max(0,Math.min(1,(t-.65)/.2));return 2*(10*u*u*u-15*Math.pow(u,4)+6*Math.pow(u,5));}
double rampRate(double t){double u=Math.max(0,Math.min(1,(t-.65)/.2));return 10*(30*u*u-60*u*u*u+30*Math.pow(u,4));}
boolean residualGate()throws Exception{boolean ok=true;for(Monitor m:s.getMonitorManager().getObjects())if(m instanceof ResidualMonitor&&!m.getPresentationName().equals("Y-momentum")){Path p=out.resolve("residual_latest_"+m.getPresentationName()+".csv");((ResidualMonitor)m).export(p.toString());List<Double> v=new ArrayList<>();for(String line:Files.readAllLines(p)){String[] a=line.replace("\"","").split(",");try{if(a.length>=2)v.add(Double.parseDouble(a[1]));}catch(NumberFormatException ignored){}}if(v.size()<40)throw new IllegalStateException("Missing residual history");double first=v.get(v.size()-40),last=v.get(v.size()-1);ok&=Double.isFinite(first+last)&&last<=.01*Math.max(Math.abs(first),1e-30);}return ok;}
'''
for name,smoke in [('RampPlus2Smoke',True),('RampPlus2Run',False)]:
 text=prefix.replace('class BenchmarkStaticPlus2','class '+name)+f'final boolean SMOKE={str(smoke).lower()};\nfinal String LAW={json.dumps(law)};\n'+methods+body
 if not smoke:
  old='Files.writeString(out.resolve("error.txt"),e.toString());captureFields("failure");captureComparison("failure");auditFull("failure",333939);boolean paused='
  new='Files.writeString(out.resolve("error.txt"),e.toString());try{captureFields("failure");captureComparison("failure");auditFull("failure",333939);}catch(Exception diagnostic){Files.writeString(out.resolve("failure_export_error.txt"),diagnostic.toString());}boolean paused='
  assert text.count(old)==1;text=text.replace(old,new)
  text=text.replace('UserFieldFunction f=s.getFieldFunctionManager().createFieldFunction();','if(s.getFieldFunctionManager().hasFunction(name)){UserFieldFunction existing=(UserFieldFunction)s.getFieldFunctionManager().getFunction(name);if(!existing.getDefinition().equals(definition))throw new IllegalStateException("Existing diagnostic field changed");return existing;}UserFieldFunction f=s.getFieldFunctionManager().createFieldFunction();',1)
  helper='\n<T extends Report> T reuseReport(Class<T> cls){for(Report r:s.getReportManager().getObjects())if(cls.isInstance(r))return cls.cast(r);return s.getReportManager().createReport(cls);}\n'
  text=text.replace('public void execute()',helper+'public void execute()',1)
  for cls in ['AverageWorkerCommunicationTimeReport','TimeStepCpuTimeReport','TimeStepElapsedTimeReport']:
   text=text.replace('s.getReportManager().createReport('+cls+'.class)','reuseReport('+cls+'.class)')
 p=H/'macros'/f'{name}.java';p.write_text(text,encoding='utf8')
 r=subprocess.run([r'C:\Program Files\Eclipse Adoptium\jdk-25.0.3.9-hotspot\bin\javac.exe','-encoding','UTF-8','-cp',r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\java\platform\modules\ext\*','-d',str(H/'macros/compiled'),str(p)],capture_output=True,text=True);print(name,r.stderr);assert r.returncode==0
def angle(u):return 2*(10*u**3-15*u**4+6*u**5)
def rate(u):return 10*(30*u**2-60*u**3+30*u**4)
def accel(u):return 50*(60*u-180*u**2+120*u**3)
assert [angle(0),angle(1),rate(0),rate(1),accel(0),accel(1)]==[0,2,0,0,0,0]
vals=[angle(i/10000) for i in range(10001)];assert all(b>=a for a,b in zip(vals,vals[1:]));assert max(rate(i/10000) for i in range(10001))==18.75
(H/'audit/RAMP_KINEMATIC_UNIT_TEST.json').write_text(json.dumps(dict(passed=True,law=law,duration_s=.2,delta_deg=[0,2],endpoint_rates=[0,0],endpoint_accelerations=[0,0],maximum_deg_s=18.75,monotone=True,native_smoke_pending=True),indent=2))

