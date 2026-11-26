from pathlib import Path
import pandas as pd,numpy as np,json,sys
h=Path(__file__).resolve().parents[1];root=h/'audit/comparison_SP_C_20261102_223230';out={}
for region in ['Background','FlapOverset']:
 full=pd.read_csv(root/(region+'_full_plane.csv'));vol=pd.read_csv(root/(region+'_volume.csv'))
 active=vol[vol['Overset Cell Status']==0].copy();acc=full[full['Overset Cell Status'].isin([-2,-1])].copy();r='Overset Interpolation Cell Size Ratio'
 bad=acc.nlargest(15,r);out[region]=dict(top_size_ratio=bad.to_dict('records'),turbulence_extrema={})
 for fld in ['Turbulent Viscosity Ratio','Turbulent Kinetic Energy (J/kg)','Specific Dissipation Rate (/s)','Absolute Pressure (Pa)']:
  if fld not in active:continue
  vals=active[fld].to_numpy();idx=active[fld].idxmax() if fld in ['Turbulent Viscosity Ratio','Turbulent Kinetic Energy (J/kg)'] else active[fld].idxmin()
  row=active.loc[idx];pos=row[['X (m)','Z (m)']].to_numpy(dtype=float);a=acc[['X (m)','Z (m)']].to_numpy();dst=np.linalg.norm(a-pos,axis=1);ii=int(dst.argmin())
  out[region]['turbulence_extrema'][fld]=dict(min=float(vals.min()),max=float(vals.max()),percentiles={str(q):float(np.quantile(vals,q)) for q in [.01,.5,.99,.999]},point=row.to_dict(),nearest_acceptor_distance_m=float(dst[ii]),nearest_acceptor=acc.iloc[ii].to_dict())
 out[region]['acceptor_summary_by_x']=[]
 for lo,hi in [(.0,.732),(.732,.85),(.85,.915),(.915,.99),(.99,1.20),(1.20,1.56)]:
  part=acc[acc['X (m)'].between(lo,hi)];out[region]['acceptor_summary_by_x'].append(dict(x=[lo,hi],n=len(part),max_ratio=float(part[r].max()) if len(part) else None,distance_weighted=int((part['Overset Interpolation Type']==0).sum())))
 bad.to_csv(root/(region+'_worst_size_ratio.csv'),index=False)
 (root/(region+'_turbulence_extrema.json')).write_text(json.dumps(out[region]['turbulence_extrema'],indent=2),encoding='utf8')
(h/'validation/C0_overset_local_defects.json').write_text(json.dumps(out,indent=2),encoding='utf8')
brief={k:dict(worst_ratio=v['top_size_ratio'][:3],turbulence=v['turbulence_extrema'],bands=v['acceptor_summary_by_x']) for k,v in out.items()}
print(json.dumps(brief,indent=2))
