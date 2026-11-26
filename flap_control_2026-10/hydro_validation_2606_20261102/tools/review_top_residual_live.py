from pathlib import Path
import sys,json,re,datetime,numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1];run=Path(sys.argv[1]);read=lambda p:json.loads(p.read_text(encoding='utf8'))
state=read(h/'NIGHT_QUEUE_STATE.json');job=state.get('active') if (state.get('active') or {}).get('id')=='c0_top_backflow_extrapolated' else state['jobs']['c0_top_backflow_extrapolated'];assert Path(job['output'])==run
log=Path(job['log']);num=r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?';pattern=re.compile(r'^[ \t]*(\d+)[ \t]+'+r'[ \t]+'.join(['('+num+')']*6)+r'(?=[ \t\r\n]|$)',re.M)
rows={int(a[0]):list(map(float,a[1:])) for a in pattern.findall(log.read_text(encoding='utf8',errors='replace')) if int(a[0])>7560}
starts=sorted(set((it-7560-1)//40 for it in rows));groups=[];steps=[]
for k in starts:
 ids=list(range(7561+k*40,7601+k*40))
 if all(i in rows for i in ids):groups.append([rows[i] for i in ids]);steps.append(k+1)
assert groups,dict(reason='No complete40-inner timestep parsed',rows=len(rows),first=sorted(rows)[:6],last=sorted(rows)[-6:],block_counts={k:sum((it-7560-1)//40==k for it in rows) for k in starts});a=np.asarray(groups[-25:]);fields=['Continuity','X-momentum','Y-momentum','Z-momentum','Tke','Sdr']
old=h/'cases/SP_C_split0_overset/c0_urans_continue_inner40_20261103_041433';meta=(old/'residual_normalization_final.txt').read_text(encoding='utf8');nowmeta=(run/'residual_normalization_step_1.txt').read_text(encoding='utf8')
result=dict(at=datetime.datetime.now().astimezone().isoformat(),run=str(run),complete_steps=len(groups),last_step=steps[-1],window_steps=steps[-25:],cases={},scientific_approved=False,source='Current native STAR residual lines for complete40-inner blocks; baseline native exported monitors. No secret data output.')
curves={};result['native_csv_crosscheck']={}
for j,field in enumerate(fields):
 ref=pd.read_csv(run/('residual_step_1_'+field+'.csv'));ref=ref[(ref.iloc[:,0]>7560)&(ref.iloc[:,0]<=7600)];assert len(ref)==40
 actual=np.array([rows[int(i)][j] for i in ref.iloc[:,0]]);expected=ref.iloc[:,1].to_numpy(dtype=float);assert np.allclose(actual,expected,rtol=1e-6,atol=1e-15),(field,'log/export mismatch')
 result['native_csv_crosscheck'][field]=True
for case in ['normal','extrapolated']:result['cases'][case]={}
for j,field in enumerate(fields):
 if field=='Y-momentum':continue
 nf=lambda txt:float(re.search(re.escape(field)+r'.*?factor=([-+0-9.eE]+)',txt).group(1))
 assert abs(nf(meta)/nf(nowmeta)-1)<1e-10,'Normalization differs'
 df=pd.read_csv(old/('residual_final_'+field+'.csv'));it=df.iloc[:,0].to_numpy(dtype=int);vals=df.iloc[:,1].to_numpy(dtype=float);mask=it>4560;it=it[mask];vals=vals[mask];og=[]
 for k in sorted(set((it-4560-1)//40))[-25:]:
  ids=np.where((it-4560-1)//40==k)[0]
  if len(ids)==40 and np.array_equal((it[ids]-4560-1)%40,np.arange(40)):og.append(vals[ids])
 for case,data in [('normal',np.asarray(og)),('extrapolated',a[:,:,j])]:
  assert np.isfinite(data).all() and (data[:,0]>0).all()
  curve=data/data[:,0,None];curves[(case,field)]=np.median(curve,axis=0)
  result['cases'][case][field]=dict(normalization_factor=nf(meta),steps=len(data),median_last=float(np.median(data[:,-1])),median_last_over_first=float(np.median(curve[:,-1])),p90_last_over_first=float(np.quantile(curve[:,-1],.9)))
result['median_last_extrapolated_over_normal']={f:result['cases']['extrapolated'][f]['median_last']/result['cases']['normal'][f]['median_last'] for f in result['cases']['normal']}
(run/'top_residual_live_review.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(dict(at=result['at'],complete_steps=result['complete_steps'],ratios=result['median_last_extrapolated_over_normal'],within_step={k:{f:r['median_last_over_first'] for f,r in v.items()} for k,v in result['cases'].items()}),indent=2))
sys.path.insert(0,str(h/'tools/deps'));import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
fig,axes=plt.subplots(1,5,figsize=(15,3.6),sharey=True)
for ax,f in zip(axes,['Continuity','X-momentum','Z-momentum','Tke','Sdr']):
 for case in ['normal','extrapolated']:ax.plot(range(1,41),curves[(case,f)],label='Top '+case)
 ax.set(title=f,xlabel='Inner iteration',yscale='log');ax.grid(alpha=.2)
axes[0].set_ylabel('Residual / first inner residual');axes[-1].legend(fontsize=8);fig.suptitle('Top-backflow direction diagnostic: within-step residual decay\nNative normalization unchanged; separate physical-time windows',fontsize=10);fig.tight_layout();fig.savefig(h/'reports/C0_top_backflow_residual_decay.png',dpi=150);plt.close(fig)
