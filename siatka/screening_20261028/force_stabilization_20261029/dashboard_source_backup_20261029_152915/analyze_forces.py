"""Live scientific diagnostics; no mutation of simulation files."""
import sys,csv,json,re,statistics,math,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
sys.path.insert(0,str(Q/'deps311'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({'font.size':12,'font.family':'DejaVu Sans','svg.fonttype':'none'})
def rows(p):
 try:
  with p.open(newline='',encoding='utf-8-sig') as f:
   return [{k:float(v) for k,v in a.items()} for a in csv.DictReader(f) if all(v is not None and v!='' for v in a.values())]
 except (OSError,ValueError):return []
def audit_inner(p):
 rr=rows(p)
 if not rr:return {}
 keys=list(rr[0]);it,force=keys[:2]
 # Pilot had exactly 20 iterations per time step; compare last 2 and last 5.
 recent=[r for r in rr if r[it]>rr[-1][it]-800]
 lookup={int(r[it]):r[force] for r in recent};changes2=[];changes5=[]
 for i,f in lookup.items():
  if i%20==0 and i-1 in lookup and i-4 in lookup and abs(f)>1e-9:
   changes2.append(100*abs(f-lookup[i-1])/abs(f));changes5.append(100*abs(f-lookup[i-4])/abs(f))
 return {'last_40_steps':len(changes2),'median_last_iteration_change_pct':statistics.median(changes2),'max_last_iteration_change_pct':max(changes2),'median_last_5_iterations_change_pct':statistics.median(changes5),'max_last_5_iterations_change_pct':max(changes5)}
jobs=json.loads((R/'queue.json').read_text())
audit={};fig,top=plt.subplots(2,1,figsize=(11,7),layout='constrained');extra,low=plt.subplots(2,1,figsize=(11,7),layout='constrained');axes=np.array([top,low])
for mesh,color in [('M03','#187b73'),('M02','#bf5a28'),('M04','#5267ad'),('M05','#6d7136')]:
 pilot=Q/(mesh+'_GPU')/'F18_dt1000us_long'
 old=rows(pilot/'history.csv');new=[]
 for j in jobs:
  if j['id'].startswith(mesh+'_'):new+=rows(R/j['id']/'history.csv')
 allrows=[r for r in old+new if r["physical_time_s"]>=.2-1e-8]
 if allrows:
  t=[a['physical_time_s'] for a in allrows]
  for ax,key,title in [(axes[0,0],'CD','Drag coefficient CD'),(axes[0,1],'CL_total','Lift coefficient CL (includes buoyancy)')]:
   ax.plot(t,[a[key] for a in allrows],label=mesh,color=color,lw=1.5);ax.set(title=title,xlabel='Physical time [s]');ax.axvline(.2,color='#777',ls=':',lw=.8);ax.grid(alpha=.2);ax.legend()
 if new:
  axes[1,0].plot([a['physical_time_s'] for a in new],[a['pressure_drag_N'] for a in new],color=color,label=mesh+' pressure')
  axes[1,0].plot([a['physical_time_s'] for a in new],[a['viscous_drag_N'] for a in new],color=color,ls='--',label=mesh+' viscous')
  axes[1,1].plot([a['physical_time_s'] for a in new],[a['interface_max_CFL'] for a in new],color=color,label=mesh+' interface')
 if not (pilot/'Fx_pressure_shear.txt').exists():continue
 force=(pilot/'Fx_pressure_shear.txt').read_text()
 vals=re.findall(r'Totals:\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)',force)[-1]
 audit[mesh]={'pilot_pressure_drag_N':float(vals[0]),'pilot_viscous_drag_N':float(vals[1]),'pilot_total_drag_N':float(vals[2]),'pilot_drag_inner_iterations':audit_inner(pilot/'monitor_Fx_half_Monitor.csv'),'pilot_lift_inner_iterations':audit_inner(pilot/'monitor_Fz_half_Monitor.csv')}
axes[1,0].set(title='Drag components on 0.02 m slice',xlabel='Physical time [s]',ylabel='Force [N]')
axes[1,1].set(title='Physical-step CFL in 0.01 < water VF < 0.99',xlabel='Physical time [s]')
for ax in axes[1]:ax.grid(alpha=.2);ax.legend()
fig.suptitle('Force histories after startup | t ≥ 0.2 s',fontsize=15)
extra.suptitle('Drag components and interface CFL',fontsize=15)
for ax in list(top)+list(low):ax.margins(x=.02,y=.12)
extra.savefig(R/'force_components.png',dpi=170);extra.savefig(R/'force_components.svg');plt.close(extra)
fig.savefig(R/'force_history.png',dpi=150);fig.savefig(R/'force_history.svg');plt.close(fig)
dp=audit['M02']['pilot_pressure_drag_N']-audit['M03']['pilot_pressure_drag_N'];dd=audit['M02']['pilot_total_drag_N']-audit['M03']['pilot_total_drag_N']
audit['pressure_share_of_pilot_drag_difference_pct']=100*dp/dd
audit['updated_at']=datetime.datetime.now().astimezone().isoformat()
(R/'force_diagnostic.json').write_text(json.dumps(audit,indent=2))
print(json.dumps(audit))
