from pathlib import Path
import json,re,sys,datetime
import numpy as np,pandas as pd
H=Path(__file__).resolve().parents[1]
out=H/'audit/bc_resume_review_20261103';out.mkdir(exist_ok=True)
runs={'B0':H/'cases/SP_B_split0_fixed/b0_top_direction_20261103_053542','C0':H/'cases/SP_C_split0_overset/c0_top_direction_20261103_050724'}
result={'at':datetime.datetime.now().astimezone().isoformat(),'source':'completed native exported histories; no new solver steps','cases':{},'quantitative_validation':False}
for case,run in runs.items():
 hist=pd.read_csv(run/'history.csv');far=pd.read_csv(run/'far_top_metrics.csv');base=2250 if case=='B0' else 7560
 d={'residuals':{},'force_windows':{},'far_top':{},'walls':{},'native_full_audit':(run/'full_audit_final.txt').read_text(),'existing_field_review':json.loads((run/'work_review.json').read_text())}
 for f in ['Continuity','X-momentum','Y-momentum','Z-momentum','Tke','Sdr']:
  df=pd.read_csv(run/('residual_final_'+f+'.csv'));it=df.iloc[:,0].to_numpy(dtype=int);values=df.iloc[:,1].to_numpy(dtype=float);blocks=[]
  for step in range(76,101):
   mask=(it>base+40*(step-1))&(it<=base+40*step);ids=it[mask];v=values[mask]
   assert len(v)==40 and np.array_equal(ids,np.arange(base+40*(step-1)+1,base+40*step+1)),(case,f,step)
   assert np.isfinite(v).all();blocks.append(v)
  a=np.array(blocks);ratio=np.divide(a[:,-1],a[:,0],out=np.zeros(25),where=a[:,0]!=0)
  factor=float(re.search(re.escape(f)+r'.*factor=([-+.eE0-9]+)',(run/'residual_normalization_final.txt').read_text()).group(1))
  d['residuals'][f]={'normalization_factor':factor,'median_last_normalized':float(np.median(a[:,-1])),'median_last_raw':float(np.median(a[:,-1])*factor),'median_last_over_first':float(np.median(ratio)),'p95_last_over_first':float(np.quantile(ratio,.95)),'max_last_over_first':float(ratio.max())}
 for f in ['CL_hydro','CD','Mh_Nm','Fx_N','Fz_N']:
  a=hist[f].iloc[-50:-25].to_numpy();b=hist[f].iloc[-25:].to_numpy()
  d['force_windows'][f]={'mean25':float(b.mean()),'relative_range_pct':float(100*np.ptp(b)/abs(b.mean())),'adjacent_mean_drift_pct':float(100*(b.mean()-a.mean())/abs(a.mean()))}
 for f in far.columns[2:]:
  a=far[f].iloc[-50:-25];b=far[f].iloc[-25:]
  d['far_top'][f]={'last':float(b.iloc[-1]),'last25_mean':float(b.mean()),'adjacent_mean_change':float(b.mean()-a.mean())}
 for group in ['main','flap']:
  df=pd.read_csv(run/(group+'_final_wall.csv'))
  d['walls'][group]={'rows':len(df),'columns':list(df.columns)}
  for f in df.columns:
   if 'Pressure' in f or 'Y+' in f or 'Yplus' in f:
    v=df[f].to_numpy();d['walls'][group][f]={'min':float(v.min()),'max':float(v.max()),'q99':float(np.quantile(v,.99))}
 d['residual_inner_decay_pass_for_POC']=all(v['p95_last_over_first']<.01 for k,v in d['residuals'].items() if k!='Y-momentum')
 d['force_window_pass_for_POC']=all(v['relative_range_pct']<.2 and abs(v['adjacent_mean_drift_pct'])<.2 for v in d['force_windows'].values())
 result['cases'][case]=d
result['important_limits']=['B/C residual normalization factors differ; compare within-step ratios, not plotted normalized amplitudes.','Different B/C grids: present force difference includes discretization and interpolation. No grid convergence index established.','dt0.002s not independently halved; low inner errors do not prove temporal accuracy.','Far-field velocity still below18m/s near top; retain as quantitative-validation uncertainty if near-foil guards and force stability pass.','Acceptance for frozen-flow kinematic POC is distinct from quantitative force/energy validation.']
(out/'review.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({k:{'residual_inner_decay_pass_for_POC':v['residual_inner_decay_pass_for_POC'],'force_window_pass_for_POC':v['force_window_pass_for_POC'],'residuals':v['residuals'],'force_windows':v['force_windows'],'far_top':v['far_top'],'walls':v['walls']} for k,v in result['cases'].items()},indent=2))
