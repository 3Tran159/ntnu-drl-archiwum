"""One controlled deceleration repair, derived from the existing guarded macro."""
from pathlib import Path
import subprocess,json,sys
H=Path(__file__).resolve().parents[1]
E='INLET_PRESSURE_RECOVERY_20261103'
t=(H/'macros/BoundedFixedFlapSweep.java').read_text()
def change(a,b):
 global t
 assert t.count(a)==1,(a,t.count(a))
 t=t.replace(a,b)
t=t.replace('BoundedFixedFlapSweep','InletPressureRecovery').replace('BOUNDED_FIXED_PLUS2_SWEEP_20261103',E).replace('NTNU_BOUNDED_SWEEP_ALLOWED','NTNU_PRESSURE_RECOVERY_ALLOWED').replace('BOUNDED_SWEEP_RUNTIME.properties','PRESSURE_RECOVERY_RUNTIME.properties')
change('double speedAt(int k,double start,double t){return k==0?18-8*smooth((t-.65)/.4):k<4?10:targetU(k)-2+2*smooth((t-start)/.2);}',r'''
// C2 time reparameterization: preserve U, dU/dt and d2U/dt2 at t=.690.
// Quintic phase rate 2.5/s -> .25/s over .020 s; no field/mesh reset.
double phaseX(double t){double s=t-.690;if(s<=0)return .1+2.5*s;if(s<.020){double v=s/.020;return .1+2.5*s+(.25-2.5)*.020*(2.5*Math.pow(v,4)-3*Math.pow(v,5)+Math.pow(v,6));}return .1275+.25*(s-.020);}
double phaseRate(double t){double v=(t-.690)/.020;return v<=0?2.5:v>=1?.25:2.5+(.25-2.5)*smooth(v);}
double speedAt(int k,double start,double t){return 18-8*smooth(phaseX(t));}
double accelerationAt(double t){double x=Math.max(0,Math.min(1,phaseX(t)));return -8*30*x*x*(1-x)*(1-x)*phaseRate(t);}
''')
change('String phase(double t){return stage==0?"DECEL_DIAGNOSTIC":stage==1?"C0_SETTLE_10":stage==2?"FLAP_RAMP_10":stage>=4&&t<stageStart+.2-1e-9?"U_TRANSITION":"FIXED_PLUS2_SETTLE";}','String phase(double t){return "INLET_PRESSURE_REPAIR_DIAGNOSTIC";}')
change('if(stage<0||stage>7)','if(stage!=0)')
# Remove all autonomous stage-advance logic from this single verification.
a=t.index('void acceptedPoint()');b=t.index('public void execute()',a);t=t[:a]+t[b:]
a=t.index('  if(stage==0&&t>=1.05-1e-9)');b=t.index('\n }\n }\n if(!complete)',a)
t=t[:a]+'  if(i==50){complete=true;break;}'+t[b:]
change('for(int i=1;i<=6000;i++)','for(int i=1;i<=50;i++)')
t=t.replace('bounded_sweep_complete','pressure_recovery_complete').replace('bounded_sweep_paused','pressure_recovery_paused').replace('bounded_sweep_hold','pressure_recovery_hold')
change('\\\"numerical_points_complete\\\":true','\\\"numerical_points_complete\\\":false,\\\"physical_safety_pass\\\":true,\\\"requires_scientific_review\\\":true')
# Inlet subdomain is ADDITIONAL monitoring. Global and original wall/gap guards stay.
marker='captureFields("readback");auditFull("readback",333939);'
change(marker,r'''
 readNative("initial");
 if(Math.abs(rv("HF_CL_hydro")-.3206861558619269)>1e-9||Math.abs(rv("HF_CD")-.007155867131695475)>1e-9||Math.abs(rv("HF_Mh_Nm")+11.778200215235007)>1e-7)throw new IllegalStateException("Saved force fields differ from approved t069 checkpoint");
 UserFieldFunction im=field("RECOVERY_InletMask","($$Position[0] < <-30 m>) ? 1 : 0",new Dimensions());ThresholdPart ip=s.getPartManager().createThresholdPart();ip.setPresentationName("Recovery inlet diagnostic only");ip.getInputParts().setObjects(regions);ip.setFieldFunction(im);ip.setRange(new DoubleVector(new double[]{.5,1.5}));ip.setMode(ThresholdMode.BETWEEN_TAG);minimum("HF_pabs_inlet","AbsolutePressure",List.of(ip),true);
 captureFields("readback");auditFull("readback",333939);''')
change('for(String zone:List.of("fixed","flap","near","gap","liquid_all"))','for(String zone:List.of("fixed","flap","near","gap","liquid_all","inlet"))')
change('residual_gate,measurement_eligible\\n','residual_gate,measurement_eligible,dU_dt_m_s2\\n')
change('+residualOk+",false\\n"', '+residualOk+",false,"+accelerationAt(t)+"\\n"')
change('captureFields("final");captureComparison("final");','readNative("final");captureFields("final");captureComparison("final");')
# Reuse the already compiled readback implementation to record actual BCs/reference.
n=(H/'macros/RelocationNativeAudit.java').read_text()
helpers=n[n.index('String val('):n.index('FieldFunction namedField(')]
body=n[n.index(' StringBuilder b=new StringBuilder("input='):n.index('captureComparison("reopened");')]
body=body.replace('out.resolve("native_state.txt")','out.resolve("native_state_"+label+".txt")')
method='void readNative(String label)throws Exception{Path input=Paths.get(s.getSessionPath());double t=s.getSolution().getPhysicalTime();int it=s.getSimulationIterator().getCurrentIteration();\n'+body+'\n}\n'
change('final String EXPERIMENT=',helpers+method+'final String EXPERIMENT=')
p=H/'macros/InletPressureRecovery.java';assert not p.exists();p.write_text(t,encoding='utf8')
assert '.clearSolution(' not in t and '.initializeSolution(' not in t
r=subprocess.run([r'C:\Program Files\Eclipse Adoptium\jdk-25.0.3.9-hotspot\bin\javac.exe','-encoding','UTF-8','-cp',r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\java\platform\modules\ext\*','-d',str(H/'macros/compiled'),str(p)],capture_output=True,text=True)
(H/'audit/PRESSURE_RECOVERY_COMPILE.txt').write_text(r.stderr);print(r.stderr);assert r.returncode==0
print('Compiled one 50-step guarded recovery; no stage advancement.')
