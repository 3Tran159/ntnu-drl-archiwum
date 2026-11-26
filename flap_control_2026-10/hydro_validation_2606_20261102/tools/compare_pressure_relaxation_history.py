from pathlib import Path
import sys,json,datetime,numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1];run=Path(sys.argv[1]);old=h/'cases/SP_C_split0_overset/c0_urans_continue_inner40_20261103_041433'
d=pd.read_csv(run/'history.csv');a=pd.read_csv(old/'history.csv');zones=pd.read_csv(run/'pressure_zones.csv')
last=d.tail(25);p=zones[(zones.zone=='liquid_all')&zones.step.isin(last.step)]
near=zones[(zones.zone=='near')&zones.step.isin(last.step)]
o=dict(at=datetime.datetime.now().astimezone().isoformat(),run=str(run),samples=len(d),time_s=float(d.time_s.iloc[-1]),scientific_approved=False,notes='Continuous-time pressureURF0.2to0.1 test; geometry,physics,mesh,40inner anddt unchanged. Phase mean changes include physical drift.',means={k:float(last[k].mean()) for k in ['CL_hydro','CD','Fx_N','Fz_N','Mh_Nm']},phase_change_percent={k:100*(last[k].mean()/a[k].tail(25).mean()-1) for k in ['CL_hydro','CD','Mh_Nm']},delta_B_percent={k:100*(last[k].mean()/v-1) for k,v in dict(CL_hydro=.32729653634048,CD=.007163580556642399).items()},last25_pressure=dict(min_global_Pa=float(last.p_absolute_min_Pa.min()),max_global_Pa=float(last.p_absolute_min_Pa.max()),std_global_Pa=float(last.p_absolute_min_Pa.std()),min_near_Pa=float(near.pabs_Pa.min()),top_minimum_steps=int((p.z_m>7).sum()),all_minimum_steps=len(p)),last25_mass_max=float(last.mass_imbalance_relative.max()),prior_urf02_last25=dict(min_global_Pa=float(a.p_absolute_min_Pa.tail(25).min()),std_global_Pa=float(a.p_absolute_min_Pa.tail(25).std()),mass_max=float(a.mass_imbalance_relative.tail(25).max())))
(run/'pressure_relaxation_live_review.json').write_text(json.dumps(o,indent=2),encoding='utf8');print(json.dumps(o,indent=2))
sys.path.insert(0,str(h/'tools/deps'));import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
fig,axes=plt.subplots(2,2,figsize=(11,7))
for ax,k,title in zip(axes.ravel(),['CL_hydro','CD','p_absolute_min_Pa','mass_imbalance_relative'],['Lift coefficient','Drag coefficient','Minimum absolute pressure [kPa]','Relative mass imbalance']):
 scale=.001 if k=='p_absolute_min_Pa' else 1
 ax.plot(a.time_s,a[k]*scale,label='Pressure URF 0.2');ax.plot(d.time_s,d[k]*scale,label='Pressure URF 0.1')
 if k=='p_absolute_min_Pa':
  f=zones[zones.zone=='near'];ax.plot(f.time_s,f.pabs_Pa*.001,ls=':',label='Near-foil minimum, URF0.1')
 if k=='mass_imbalance_relative':ax.set_yscale('log')
 ax.axvline(.45,color='gray',lw=.7);ax.set(title=title,xlabel='Physical time [s]');ax.grid(alpha=.2);ax.legend(fontsize=8)
fig.suptitle('0-degree pressure-relaxation diagnostic: unchanged physical problem\\nNo scientific approval; transient solution retained',fontsize=11);fig.tight_layout();p=h/'reports/C0_pressure_relaxation_history.png';fig.savefig(p,dpi=150);plt.close(fig);print(p)
