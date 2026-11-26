from pathlib import Path
import sys,json,datetime,numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1];run=Path(sys.argv[1]);label=sys.argv[2]
specs=[('B reference',h/'audit/matching_B_20261103_034849','',0,15),('C tight URANS',run,label,2310,15)]
result=dict(at=datetime.datetime.now().astimezone().isoformat(),scientific_approved=False,notes='Each timestep residual curve divided by its own first inner iteration; normalization cancels. Ratio alone does not prove equation convergence. Last25 complete timesteps; unchanged native monitor history.',cases={})
curves={}
for case,folder,suffix,start,inner in specs:
 rec={}
 for field in ['Continuity','X-momentum','Z-momentum','Tke','Sdr']:
  path=folder/('residual_'+(suffix+'_' if suffix else '')+field+'.csv')
  f=pd.read_csv(path);it=f.iloc[:,0].to_numpy(dtype=int);y=f.iloc[:,1].to_numpy(dtype=float);mask=it>start;it=it[mask];y=y[mask]
  groups=[]
  for step in sorted(set((it-start-1)//inner))[-25:]:
   ids=np.where((it-start-1)//inner==step)[0]
   if len(ids)!=inner or not np.array_equal((it[ids]-start-1)%inner,np.arange(inner)):continue
   vals=y[ids]
   if np.isfinite(vals).all() and vals[0]>0:groups.append(vals/vals[0])
  if not groups:continue
  a=np.array(groups);median=np.median(a,axis=0);curves[(case,field)]=median
  rec[field]=dict(steps=len(a),median_last_over_first=float(np.median(a[:,-1])),p90_last_over_first=float(np.quantile(a[:,-1],.9)),median_curve=median.tolist())
 result['cases'][case]=rec
(run/('inner_residual_review_'+label+'.json')).write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({case:{field:{k:v for k,v in val.items() if k!='median_curve'} for field,val in fields.items()} for case,fields in result['cases'].items()},indent=2))
sys.path.insert(0,str(h/'tools/deps'));import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
fig,axes=plt.subplots(1,5,figsize=(15,3.4),sharey=True)
for ax,field in zip(axes,['Continuity','X-momentum','Z-momentum','Tke','Sdr']):
 for case,_,_,_,inner in specs:
  if (case,field) in curves:ax.plot(np.arange(1,inner+1),curves[(case,field)],label=case)
 ax.axhline(1,color='gray',lw=.7);ax.set_title(field);ax.set_xlabel('Inner iteration');ax.set_yscale('log');ax.grid(alpha=.2)
axes[0].set_ylabel('Residual / first inner residual');axes[-1].legend(fontsize=8)
fig.suptitle('Within-step residual reduction: median of last25 complete timesteps; diagnostic only',fontsize=11);fig.tight_layout()
dest=h/'reports'/('C0_inner_residual_decay_'+label+'.png');fig.savefig(dest,dpi=160);plt.close(fig);print(dest)
