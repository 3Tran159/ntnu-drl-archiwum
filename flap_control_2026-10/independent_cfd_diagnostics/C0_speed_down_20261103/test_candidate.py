from pathlib import Path
import json,hashlib,math
p=Path(r"F:\ntnu\flap_control\independent_cfd_diagnostics\C0_speed_down_20261103")
m=json.loads((p/"CANDIDATE.json").read_text(encoding="utf-8"))
src=Path(m["source"])
c=p/"C0SpeedDownSmoke.java"
s=c.read_text(encoding="utf-8")
checks={
"Original macro unchanged": hashlib.sha256(src.read_bytes()).hexdigest()==m["source_sha256"],
"New macro unchanged": hashlib.sha256(c.read_bytes()).hexdigest()==m["candidate_sha256"],
"Compiled bytecode present":(p/"compiled"/"macro"/"C0SpeedDownSmoke.class").is_file(),
"Only original verified C0 allowed":'C0_recovered_t065.sim' in s and '11560' in s and 'Math.abs(t0-.65)>1e-9' in s,
"No field reset in execute":not any(x in s[s.index("public void execute()"):] for x in ("clearSolution","initializeSolution")),
"Flap fixed at zero":'final String LAW="<0 deg>";' in s and "double ramp(double t){return 0.0;}" in s,
"Explicit authorization environment required":'NTNU_C0_SPEEDDOWN_ALLOWED' in s,
"20-step limit":'for(int i=1;i<=20;i++)' in s,
"Guard unchanged":'p<=12339.214766776897' in s and 'err>0' in s and 'u>180' in s,
"Speed history recorded":'U_m_s,qS_N' in s and 'commandedU' in s
}
assert all(checks.values()),checks
def speed(t):
 x=max(0.,min(1.,(t-.65)/.4));return 18-8*(10*x**3-15*x**4+6*x**5)
profile=[{"time_s":t,"speed_m_s":round(speed(t),6)} for t in (.65,.69,.75,.85,1.05)]
assert profile[0]["speed_m_s"]==18 and profile[-1]["speed_m_s"]==10
out={"status":"COMPILE_PASS_PRELAUNCH_AUDIT_PASS_NOT_EXECUTED",
"checks":checks,"speed_profile":profile,
"approved_job_registered":False,
"star_solver_launched":False,
"scientific_validation":False,
"source_untouched":True}
(p/"PRELAUNCH_AUDIT.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out,indent=2))
