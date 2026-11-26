from pathlib import Path
import json,pandas as pd,numpy as np,datetime
h=Path(__file__).resolve().parents[1];run=h/'cases/SP_C_split0_overset/c0_inner40_20261102_223940'
df=pd.read_csv(run/'history.csv');base=json.loads((h/'validation/NIGHT_C0_readonly_review.json').read_text(encoding='utf8'));b=json.loads((h/'validation/SP_B_stabilized_result.json').read_text(encoding='utf8'))
out=dict(at=datetime.datetime.now().astimezone().isoformat(),case=str(run),samples=len(df),time_s=float(df.time_s.iloc[-1]) if len(df) else .3024,complete=(run/'status.json').exists(),scientific_gate=False)
if len(df):
 last=df.tail(25);out['last_25']=dict(CL=float(last.CL_hydro.mean()),CD=float(last.CD.mean()),Mh_Nm=float(last.Mh_Nm.mean()),mass_max=float(last.mass_imbalance_relative.max()),pabs_min=float(last.p_absolute_min_Pa.min()),CL_relative_range=float(last.CL_hydro.max()-last.CL_hydro.min())/abs(float(last.CL_hydro.mean())),CD_relative_range=float(last.CD.max()-last.CD.min())/abs(float(last.CD.mean())))
 out['delta_vs_original_C_percent']=dict(CL=100*(out['last_25']['CL']/base['CL_mean']-1),CD=100*(out['last_25']['CD']/base['CD_mean']-1))
 out['delta_vs_B_percent']=dict(CL=100*(out['last_25']['CL']/.32729653634048-1),CD=100*(out['last_25']['CD']/.007163580556642399-1))
 out['pressure_gate_pass_so_far']=bool((df.p_absolute_min_Pa>12339.214766776897).all())
 out['positive_volume_so_far']=bool((df.min_volume_m3>0).all())
 out['partial_result_not_approved']=True
(h/'validation/C0_inner40_work_review.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out,indent=2))
