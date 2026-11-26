from pathlib import Path
import pandas as pd,json
h=Path(__file__).resolve().parents[1];out={}
for r in ['Background','FlapOverset']:
 d=pd.read_csv(h/'audit/comparison_SP_C_20261102_223230'/(r+'_full_plane.csv'))
 d=d[d['Overset Cell Status'].isin([-2,-1])]
 out[r]={}
 for kind,x in d.groupby('Overset Interpolation Type'):
  col='Overset Interpolation Cell Size Ratio'
  out[r][str(int(kind))]=dict(count=len(x),ratio_median=float(x[col].median()),ratio_p99=float(x[col].quantile(.99)),ratio_max=float(x[col].max()),greater_2=int((x[col]>2).sum()),less_half=int((x[col]<.5).sum()),worst=x.loc[x[col].idxmax(),['X (m)','Z (m)',col]].to_dict())
(h/'validation/C0_size_ratio_by_interpolation.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out,indent=2))
