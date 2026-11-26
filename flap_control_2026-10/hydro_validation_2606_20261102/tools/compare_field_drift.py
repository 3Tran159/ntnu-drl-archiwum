from pathlib import Path
import sys,json,datetime,numpy as np,pandas as pd
run=Path(sys.argv[1]);before=sys.argv[2];after=sys.argv[3];allrows=[]
cols=['X (m)','Y (m)','Z (m)'];uv=['Velocity[i] (m/s)','Velocity[j] (m/s)','Velocity[k] (m/s)']
for region in ['Background','FlapOverset']:
 a=pd.read_csv(run/(region+'_'+before+'_volume.csv')).sort_values(cols).reset_index(drop=True)
 b=pd.read_csv(run/(region+'_'+after+'_volume.csv')).sort_values(cols).reset_index(drop=True)
 assert len(a)==len(b) and np.max(np.abs(a[cols].to_numpy()-b[cols].to_numpy()))<1e-10
 keep=(a['Overset Cell Status']==0)&(b['Overset Cell Status']==0)
 b=b.loc[keep].copy();a=a.loc[keep]
 b['dU']=np.linalg.norm(b[uv].to_numpy()-a[uv].to_numpy(),axis=1)
 b['dP']=b['Pressure (Pa)'].to_numpy()-a['Pressure (Pa)'].to_numpy()
 b['region']=region;allrows.append(b)
f=pd.concat(allrows,ignore_index=True);near=(f['X (m)']>-.15)&(f['X (m)']<1.5)&(f['Z (m)']>-.3)&(f['Z (m)']<.35)
result=dict(at=datetime.datetime.now().astimezone().isoformat(),run=str(run),before=before,after=after,notes='Field change across different iteration snapshots, not PDE residual. Identical full-plane cells matched by sorted XYZ; active in both.')
for name,mask in [('all',np.ones(len(f),bool)),('near_foil',near),('far_field',~near)]:
 g=f[mask];v=g['Volume (m^3)'].to_numpy()
 result[name]=dict(cells=len(g),dU_max_m_s=float(g.dU.max()),dU_volume_rms_m_s=float(np.sqrt(np.average(g.dU**2,weights=v))),dP_max_abs_Pa=float(g.dP.abs().max()),dP_volume_rms_Pa=float(np.sqrt(np.average(g.dP**2,weights=v))))
result['largest_velocity_changes']=f.nlargest(8,'dU')[['region','X (m)','Z (m)','dU','dP','Volume (m^3)','Cell Quality','Wall Distance (m)']].to_dict(orient='records')
result['largest_pressure_changes']=f.loc[f.dP.abs().nlargest(8).index,['region','X (m)','Z (m)','dU','dP','Volume (m^3)','Cell Quality','Wall Distance (m)']].to_dict(orient='records')
(run/('field_drift_'+before+'_'+after+'.json')).write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if not k.startswith('largest')},indent=2))
print(json.dumps(dict(largest_velocity_changes=result['largest_velocity_changes'][:3],largest_pressure_changes=result['largest_pressure_changes'][:3]),indent=2))
