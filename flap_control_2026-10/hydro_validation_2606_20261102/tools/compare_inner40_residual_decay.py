from pathlib import Path
import sys,json,datetime,numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1];run=Path(sys.argv[1]);label=sys.argv[2]
assert 'inner40' in run.name and (run/('residual_normalization_'+label+'.txt')).exists()
u15=h/'cases/SP_C_split0_overset/c0_tight_urans_v2_20261103_035710'
specs=[('B: 15 inner',h/'audit/matching_B_20261103_034849','',0,15),('C corrected: 15 inner',u15,'final',2310,15),('C corrected: 40 inner',run,label,4560,40)]
result=dict(at=datetime.datetime.now().astimezone().isoformat(),scientific_approved=False,notes='Each complete timestep residual divided by its own first inner residual. Normalization cancels. Last 25 complete timesteps of each phase. Continuations differ in physical time, so this is a numerical diagnostic, not paired-time isolation or proof of equation convergence.',cases={})
curves={}
for case,folder,suffix,start,inner in specs:
 rec={}
 for field in ['Continuity','X-momentum','Z-momentum','Tke','Sdr']:
  f=pd.read_csv(folder/('residual_'+(suffix+'_' if suffix else '')+field+'.csv'))
  it=f.iloc[:,0].to_numpy(dtype=int);y=f.iloc[:,1].to_numpy(dtype=float);mask=it>start;it=it[mask];y=y[mask];groups=[]
  for step in sorted(set((it-start-1)//inner))[-25:]:
   ids=np.where((it-start-1)//inner==step)[0]
   if len(ids)!=inner or not np.array_equal((it[ids]-start-1)%inner,np.arange(inner)):continue
   vals=y[ids]
   if np.isfinite(vals).all() and vals[0]>0:groups.append(vals/vals[0])
  assert groups,(case,field)
  a=np.array(groups);curves[(case,field)]=np.median(a,axis=0)
  rec[field]=dict(steps=len(a),median_last_over_first=float(np.median(a[:,-1])),p90_last_over_first=float(np.quantile(a[:,-1],.9)),median_last5_over_first=float(np.median(a[:,-5:].mean(axis=1))))
 result['cases'][case]=rec
(run/('inner40_residual_review_'+label+'.json')).write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result,indent=2))
sys.path.insert(0,str(h/'tools/deps'));import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
fig,axes=plt.subplots(1,5,figsize=(15,3.7),sharey=True)
for ax,field in zip(axes,['Continuity','X-momentum','Z-momentum','Tke','Sdr']):
 for case,_,_,_,inner in specs:ax.plot(np.arange(1,inner+1),curves[(case,field)],label=case)
 ax.axhline(1,color='gray',lw=.7);ax.set_title(field);ax.set_xlabel('Inner iteration');ax.set_yscale('log');ax.grid(alpha=.2)
axes[0].set_ylabel('Residual / first inner residual');axes[-1].legend(fontsize=7)
fig.suptitle('Within-step residual reduction; median of last 25 complete steps\nDifferent physical-time windows; diagnostic, not a convergence certificate',fontsize=10)
fig.tight_layout();dest=h/'reports'/('C0_inner40_residual_decay_'+label+'.png');fig.savefig(dest,dpi=150);plt.close(fig);print(dest)
