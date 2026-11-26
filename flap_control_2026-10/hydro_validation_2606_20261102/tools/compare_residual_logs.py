from pathlib import Path
import re,json,numpy as np
h=Path(__file__).resolve().parents[1]
sources={'B':h/'runs/RunHydroStatic_SP_B_20261102_195203.log','C':h/'runs/RunURANSFromSteady_SP_C_20261102_203650.log'}
out={}
for label,p in sources.items():
 text=p.read_text(encoding='utf8',errors='replace')
 numeric=[];stepdata=[];current_time=None
 for line in text.splitlines():
  m=re.search(r'TimeStep\s+(\d+):\s+Time\s+([+\d.eE-]+)',line)
  if m:current_time=float(m.group(2))
  v=line.split()
  if len(v)>=7 and v[0].isdigit():
   try:row=[float(x) for x in v[1:7]]
   except ValueError:continue
   if len(row)==6:numeric.append(row)
   if m is None and current_time is not None and len(v)>15:stepdata.append([current_time,*row])
 a=np.array(numeric[-375:]);warnings=re.findall(r'Turbulent viscosity limited on\s+(\d+) cells in ([^\r\n]+)',text)
 out[label]=dict(source=str(p),residual_columns=['Continuity','Xmomentum','Ymomentum','Zmomentum','Tke','Sdr'],last375_median=np.median(a,axis=0).tolist(),last375_max=np.max(a,axis=0).tolist(),last375_min=np.min(a,axis=0).tolist(),final_numeric=numeric[-1],turbulent_viscosity_limiter_messages=len(warnings),last_limiter=warnings[-3:],last_report_rows=stepdata[-3:],interpretation='Logged normalized residuals; normalization/reference scales must be considered, not standalone acceptance.')
(h/'validation/BC_residual_diagnosis.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out,indent=2))
