from pathlib import Path
import sys,json,datetime,numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1];run=Path(sys.argv[1]);label=sys.argv[2]
out=dict(at=datetime.datetime.now().astimezone().isoformat(),run=str(run),label=label,scientific_approved=False,notes='Matching wall-face export coordinates at0deg; Cp from piezometric pressure/rhoU2over2. Local differences do not by themselves identify a cause.')
for group in ['main','flap']:
 a=pd.read_csv(h/'audit/comparison_SP_B_20261102_234628'/(group+'_wall.csv'))
 b=pd.read_csv(run/(group+'_'+label+'_wall.csv'))
 coords=['X (m)','Y (m)','Z (m)'];a['Cp_B']=a['Pressure (Pa)']/162000;b['Cp_C']=b['Pressure (Pa)']/162000
 for dim in coords:a['key_'+dim]=a[dim].round(9);b['key_'+dim]=b[dim].round(9)
 keys=['key_'+dim for dim in coords]
 assert not a.duplicated(keys).any() and not b.duplicated(keys).any()
 f=a.merge(b,on=keys,suffixes=('_B','_C'));f['dCp']=f.Cp_C-f.Cp_B
 bins=[]
 for lo,hi in [(0,.2),(.2,.4),(.4,.55),(.55,.7),(.7,.78),(.78,.82),(.82,1.01)]:
  g=f[f['X (m)_B'].between(lo*1.19,hi*1.19)]
  if len(g):bins.append(dict(x_over_c=[lo,hi],matched_faces=len(g),dCp_rms=float(np.sqrt(np.mean(g.dCp**2))),dCp_max_abs=float(g.dCp.abs().max()),Cp_B_mean=float(g.Cp_B.mean()),Cp_C_mean=float(g.Cp_C.mean())))
 out[group]=dict(B_faces=len(a),C_faces=len(b),matched_faces=len(f),unmatched_B=len(a)-len(f),unmatched_C=len(b)-len(f),bins=bins)
 if len(f):out[group]['largest_differences']=f.loc[f.dCp.abs().nlargest(5).index,['X (m)_B','Z (m)_B','Cp_B','Cp_C','dCp']].to_dict(orient='records')
p=run/('wall_pair_review_'+label+'.json');p.write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps(out,indent=2))
