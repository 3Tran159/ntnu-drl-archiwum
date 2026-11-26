from pathlib import Path
import sys,json,datetime,re,numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1];run=Path(sys.argv[1]);label=sys.argv[2]
assert 'pressure_urf01' in run.name and (run/('residual_normalization_'+label+'.txt')).exists()
r40=h/'cases/SP_C_split0_overset/c0_urans_continue_inner40_20261103_041433'
specs=[('C: pressure URF 0.2',r40,'final',4560,40),('C: pressure URF 0.1',run,label,7560,40)]
fields=['Continuity','X-momentum','Z-momentum','Tke','Sdr'];result=dict(at=datetime.datetime.now().astimezone().isoformat(),scientific_approved=False,notes='Last25 complete timestep windows. Same geometry,physics,mesh,dt and40inner. PressureURF is the only numerical change, but physical time also advances; this is a controlled continuation, not a same-time branch comparison.',cases={});curves={}
for case,folder,tag,start,inner in specs:
 rec={};meta=(folder/('residual_normalization_'+tag+'.txt')).read_text(encoding='utf8')
 for field in fields:
  f=pd.read_csv(folder/('residual_'+tag+'_'+field+'.csv'));it=f.iloc[:,0].to_numpy(dtype=int);y=f.iloc[:,1].to_numpy(dtype=float);mask=it>start;it=it[mask];y=y[mask];groups=[]
  for step in sorted(set((it-start-1)//inner))[-25:]:
   ids=np.where((it-start-1)//inner==step)[0]
   if len(ids)==inner and np.array_equal((it[ids]-start-1)%inner,np.arange(inner)) and np.isfinite(y[ids]).all() and y[ids][0]>0:groups.append(y[ids])
  assert groups,(case,field);a=np.array(groups);normalized=a/a[:,0,None];curves[(case,field)]=np.median(normalized,axis=0)
  factor=float(re.search(re.escape(field)+r'.*?factor=([-+0-9.eE]+)',meta).group(1))
  rec[field]=dict(steps=len(a),normalization_factor=factor,median_last_reported_residual=float(np.median(a[:,-1])),median_first_reported_residual=float(np.median(a[:,0])),median_last_over_first=float(np.median(normalized[:,-1])),p90_last_over_first=float(np.quantile(normalized[:,-1],.9)),median_last5_over_first=float(np.median(normalized[:,-5:].mean(axis=1))))
 result['cases'][case]=rec
result['same_native_normalization_factors']=all(abs(result['cases'][specs[0][0]][field]['normalization_factor']/result['cases'][specs[1][0]][field]['normalization_factor']-1)<1e-10 for field in fields)
assert result['same_native_normalization_factors'],'Do not compare normalized levels with different factors'
result['median_last_residual_ratios_urf01_over_urf02']={field:result['cases'][specs[1][0]][field]['median_last_reported_residual']/result['cases'][specs[0][0]][field]['median_last_reported_residual'] for field in fields}
(run/('pressure_relaxation_residual_review_'+label+'.json')).write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(dict(label=label,same_normalization=True,median_final_residual_ratios=result['median_last_residual_ratios_urf01_over_urf02'],within_step={case:{k:v['median_last_over_first'] for k,v in rec.items()} for case,rec in result['cases'].items()}),indent=2))
sys.path.insert(0,str(h/'tools/deps'));import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
fig,axes=plt.subplots(1,5,figsize=(15,3.6),sharey=True)
for ax,field in zip(axes,fields):
 for case,_,_,_,inner in specs:ax.plot(np.arange(1,inner+1),curves[(case,field)],label=case)
 ax.set(title=field,xlabel='Inner iteration');ax.set_yscale('log');ax.grid(alpha=.2)
axes[0].set_ylabel('Residual / first inner residual');axes[-1].legend(fontsize=8)
fig.suptitle('Pressure-relaxation diagnostic: median within-step residual decay\\nSame native normalization; physical-time windows differ',fontsize=10);fig.tight_layout();p=h/'reports'/('C0_pressure_relaxation_residual_'+label+'.png');fig.savefig(p,dpi=150);plt.close(fig);print(p)
