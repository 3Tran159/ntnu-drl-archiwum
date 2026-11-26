from pathlib import Path
import sys,json,datetime,numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1];r40=Path(sys.argv[1]);r15=h/'cases/SP_C_split0_overset/c0_tight_urans_v2_20261103_035710'
a=pd.read_csv(r15/'history.csv');b=pd.read_csv(r40/'history.csv')
refs=dict(CL_hydro=.32729653634048,CD=.007163580556642399,Mh_Nm=-12.1660832)
o=dict(at=datetime.datetime.now().astimezone().isoformat(),run=str(r40),time_s=float(b.time_s.iloc[-1]),samples=len(b),scientific_approved=False,warning='15-to-40 is a continuous-time continuation, so phase mean changes include physical drift. No paired-time claim.',metrics={})
for k in refs:
 old=float(a[k].tail(25).mean());new=float(b[k].tail(25).mean());jump=float(b[k].head(5).mean()/a[k].iloc[-1]-1)
 last=b.tail(25);slope=float(np.polyfit(last.time_s,last[k],1)[0])
 o['metrics'][k]=dict(mean15_last25=old,mean40_last25=new,phase_change_percent=100*(new/old-1),first5_vs_saved15_percent=100*jump,change_vs_B_percent=100*(new/refs[k]-1),last25_range_percent=100*float(np.ptp(last[k]))/abs(new),last25_slope_percent_per_0p05s=100*slope*.05/abs(new))
o['pressure_min_Pa']=float(b.p_absolute_min_Pa.min());o['safety_reserve_min_Pa']=float(b.safety_reserve_Pa.min());o['mass_imbalance_max']=float(b.mass_imbalance_relative.max())
(r40/'inner40_force_sensitivity.json').write_text(json.dumps(o,indent=2),encoding='utf8');print(json.dumps(o,indent=2))
sys.path.insert(0,str(h/'tools/deps'));import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
fig,axes=plt.subplots(2,2,figsize=(11,7))
for ax,k,title in zip(axes.ravel(),['CL_hydro','CD','Mh_Nm','p_absolute_min_Pa'],['Lift coefficient','Drag coefficient','Hinge moment [Nm]','Minimum absolute pressure [kPa]']):
 scale=.001 if k=='p_absolute_min_Pa' else 1
 ax.plot(a.time_s,a[k]*scale,label='C corrected: 15 inner');ax.plot(b.time_s,b[k]*scale,label='C corrected: 40 inner')
 if k in refs:ax.axhline(refs[k],ls='--',lw=1,color='black',label='B final-window mean')
 else:ax.axhline(12.3392147668,ls='--',lw=1,color='crimson',label='Required screening threshold')
 ax.axvline(.3,color='gray',lw=.7);ax.set(title=title,xlabel='Physical time [s]');ax.grid(alpha=.2);ax.legend(fontsize=8)
fig.suptitle('Corrected 0-degree flap: retained solution, unchanged geometry and physics\n40-inner continuation at t = 0.300 s; scientific audit pending',fontsize=11)
fig.tight_layout();dest=h/'reports/C0_corrected_URANS_history.png';fig.savefig(dest,dpi=150);plt.close(fig);print(dest)
