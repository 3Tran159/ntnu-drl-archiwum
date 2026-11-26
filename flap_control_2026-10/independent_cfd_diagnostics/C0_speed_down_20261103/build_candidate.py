from pathlib import Path
import re,hashlib,json
root=Path(r"F:\ntnu\flap_control")
camp=root/"hydro_validation_2606_20261102"
base=root/"independent_cfd_diagnostics"/"C0_speed_down_20261103"
src=camp/"macros"/"RampPlus2Run.java"
s=src.read_text(encoding="utf-8")
original_hash=hashlib.sha256(src.read_bytes()).hexdigest()
def one(old,new,label):
    global s
    n=s.count(old)
    if n!=1: raise RuntimeError(f"{label} expected1 found{n}")
    s=s.replace(old,new)
one("public class RampPlus2Run extends StarMacro","public class C0SpeedDownSmoke extends StarMacro","class")
one('out=root.resolve("cases/SP_C_split0_overset/ramp_plus2_"+System.getenv("NTNU_HYDRO_RUN_ID"))',
    'out=Paths.get("F:/ntnu/flap_control/independent_cfd_diagnostics/C0_speed_down_20261103/run_"+System.getenv("NTNU_HYDRO_RUN_ID"))',"output")
start=s.index('if(SMOKE){\n if(!input.equals(')
end=s.index('for(Region r:s.getRegionManager().getRegions())',start)
s=s[:start]+'''// Independent diagnostic: only verified C0 solution at 0deg/18mps.
Path source=root.resolve("cases/SP_C_split0_overset/relocation_reopen_20261103_082325/C0_recovered_t065.sim").toAbsolutePath().normalize();
if(!"YES".equals(System.getenv("NTNU_C0_SPEEDDOWN_ALLOWED")))throw new IllegalStateException("Requires explicit independent diagnostic authorization");
if(!input.equals(source)||Math.abs(t0-.65)>1e-9||s.getSimulationIterator().getCurrentIteration()!=11560)throw new IllegalStateException("Only native reopened C0 t=0.650s/iter=11560 allowed");
''' +s[end:]
s,n=re.subn(r'final String LAW=".*";', 'final String LAW="<0 deg>";',s)
if n!=1: raise RuntimeError("law replacement mismatch")
s,n=re.subn(r'double ramp\(double t\)\{[^\n]+\}', 'double ramp(double t){return 0.0;}',s)
if n!=1: raise RuntimeError("ramp replacement mismatch")
s,n=re.subn(r'double rampRate\(double t\)\{[^\n]+\}', 'double rampRate(double t){return 0.0;}',s)
if n!=1: raise RuntimeError("rate replacement mismatch")
fragment='''double speedDown(double t){
 double x=Math.max(0.0,Math.min(1.0,(t-.65)/.4));
 return 18.0-8.0*(10*x*x*x-15*Math.pow(x,4)+6*Math.pow(x,5));
}
void setInletU(double u)throws Exception{
 if(!Double.isFinite(u)||u<10.0||u>18.0)throw new IllegalStateException("Speed ramp out of bounds");
 int n=0;
 for(Region r:regions)for(Boundary b:r.getBoundaryManager().getBoundaries())if(b.getBoundaryType() instanceof InletBoundary){
  if(b.getConditions().get(InletVelocityOption.class).getSelected()!=InletVelocityOption.Type.COMPONENTS.getValue())throw new IllegalStateException("Inlet velocity specification changed");
  VectorProfile p=b.getValues().get(VelocityProfile.class);
  p.setMethod(ConstantVectorProfileMethod.class);
  p.getMethod(ConstantVectorProfileMethod.class).getQuantity().setComponents(u,0,0);
  n++;
 }
 if(n==0)throw new IllegalStateException("No inlet found");
 double qs=11.9*u*u;
 ((ExpressionReport)s.getReportManager().getReport("HF_CL_hydro")).setDefinition("($"+"{HF_Fz_NReport} - <22.666963538808645 N>)/<"+qs+" N>");
 ((ExpressionReport)s.getReportManager().getReport("HF_CD")).setDefinition("$"+"{HF_Fx_NReport}/<"+qs+" N>");
}
'''
one('boolean residualGate()throws Exception{',fragment+'boolean residualGate()throws Exception{',"insert setU")
one('for(int i=1;i<=(SMOKE?5:(int)Math.round((1.25-t0)/.002));i++){','for(int i=1;i<=20;i++){',"bounded iterations")
one('double cb=comm.getReportMonitorValue();long epoch=System.currentTimeMillis()',
    'double commandedU=speedDown(s.getSolution().getPhysicalTime()+.002);setInletU(commandedU);double cb=comm.getReportMonitorValue();long epoch=System.currentTimeMillis()',"gradual inlet change")
one('measured_angle_deg,center_error_m\\n");pw.write',
    'measured_angle_deg,center_error_m,U_m_s,qS_N\\n");pw.write',"history header")
one('+","+actual+","+ce+"\\n");w.flush();',
    '+","+actual+","+ce+","+commandedU+","+(11.9*commandedU*commandedU)+"\\n");w.flush();',"history row")
one('String status=SMOKE?"ramp_smoke_passed":stable?"ramp_stable_candidate":"ramp_limit_reached";','String status="speed_down_smoke_passed_not_scientific_validation";',"status")
s=s.replace('Files.createDirectories(out);guard();','Files.createDirectories(out);guard();')
# Macro is deliberately NOT launched by this builder.
assert "clearSolution" not in s[s.index('public void execute()'):]
assert "initializeSolution" not in s[s.index('public void execute()'):]
assert "RAMP_PLUS2_RUNTIME.properties" not in s
assert "20;i++" in s and "speedDown" in s
assert s.count("public class C0SpeedDownSmoke") == 1
out=base/"C0SpeedDownSmoke.java"
if out.exists(): raise FileExistsError(out)
out.write_text(s,encoding="utf-8")
meta={"source":str(src),"source_sha256":original_hash,"candidate":str(out),"candidate_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
"status":"PREPARED_NOT_LAUNCHED","max_steps":20,"start_s":0.65,"dt_s":0.002,"ramp_U_start":18,"ramp_U_target":10,
"ramp_duration_s":0.4,"flap_deg":0,"numeric_guard_unchanged":True,"source_solution_preserved":True,
"manual_review_required":True}
(base/"CANDIDATE.json").write_text(json.dumps(meta,indent=2),encoding="utf-8")
print(json.dumps(meta,indent=2))
