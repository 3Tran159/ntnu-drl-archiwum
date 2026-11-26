from pathlib import Path
import sys,json,datetime,re
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h/'tools/deps'));sys.path.insert(0,str(h.parent/'flap_poc_2606_20261102/deps'))
import numpy as np,pandas as pd
from shapely.geometry import Polygon
from shapely import points,distance,contains_xy
g=json.loads((h/'geometry/gap_002500um/geometry.json').read_text())
polys={k:Polygon(g[k+'_polygon']) for k in ['main','flap']}
folders={}
for v in ['SP_B','SP_C']:
 candidates=[p for p in (h/'audit').glob('comparison_'+v+'_*') if (p/'status.json').exists() and json.loads((p/'status.json').read_text()).get('status')=='inspection_complete']
 if not candidates:print(json.dumps(dict(pending=v)));sys.exit(0)
 folders[v]=max(candidates,key=lambda p:p.name)
result=dict(at=datetime.datetime.now().astimezone().isoformat(),sources={k:str(p) for k,p in folders.items()},force={},fields={},full_overset={},training_approved=False,scientific_gate=False)
for v,folder in folders.items():
 text=(folder/'diagnostic.txt').read_text(encoding='utf8');vals={}
 for m in re.finditer(r'(main|flap)_(pressure|shear|total)_force=\[([^\]]+)\]',text):
  vals[m.group(1)+'_'+m.group(2)]=[float(x) for x in m.group(3).split(',')]
 result['force'][v]=vals
 for file in folder.glob('*_volume.csv'):
  region=file.stem.replace('_volume','');df=pd.read_csv(file)
  xy=df[['X (m)','Z (m)']].to_numpy();good=np.isfinite(xy).all(1)
  if 'Overset Cell Status' in df:good&=df['Overset Cell Status'].to_numpy()==0
  df=df[good].copy();xy=xy[good];geompts=points(xy)
  dm=distance(geompts,polys['main'].boundary);dfp=distance(geompts,polys['flap'].boundary)
  near=np.minimum(dm,dfp);mask=(dm>.00015)&(dm<.008)&(dfp>2*dm)
  row=dict(region=region,active_exported_cells=len(df),columns=list(df),near_main_samples=int(mask.sum()))
  for field in ['Overset Error Status','Overset Interpolation Type','Overset Cell Type']:
   if field in df:row[field]={str(k):int(n) for k,n in df[field].value_counts().items()}
  wallcols=[col for col in df if 'wall distance' in col.lower()]
  if wallcols and mask.any():
   a=df.loc[mask,wallcols[0]].to_numpy();ratio=a/dm[mask]
   row['wall_distance_to_native_main_ratio_quantiles']={str(q):float(np.quantile(ratio,q)) for q in [0,.01,.1,.5,.9,.99,1]}
   row['wall_distance_absolute_error_max_m']=float(np.max(np.abs(a-dm[mask])))
   df.loc[mask].assign(native_main_distance_m=dm[mask],wall_distance_ratio=ratio).to_csv(folder/(region+'_wall_distance_near_main.csv'),index=False)
  for solid in ['main','flap']:
   inside=contains_xy(polys[solid].buffer(-1e-6),xy[:,0],xy[:,1])
   row['inside_native_'+solid]=int(inside.sum())
  result['fields'][v+'_'+region]=row
 for file in folder.glob('*_full_plane.csv'):
  df=pd.read_csv(file);key=file.stem
  valid='Overset Cell Status' in df and df['Overset Cell Status'].between(-2,1).all() and len(df)>0
  row=dict(rows=len(df),finite_status_verified=bool(valid),columns=list(df))
  if valid:
   for fld in ['Overset Cell Status','Overset Cell Type','Overset Error Status','Overset Interpolation Type']:
    row[fld]={str(k):int(n) for k,n in df[fld].value_counts().items()}
   acc=df[df['Overset Cell Status'].isin([-1,-2])]
   col=next((c for c in df if 'Interpolation Cell Size Ratio' in c),None)
   if col and len(acc):row['acceptor_size_ratio_quantiles']={str(q):float(acc[col].quantile(q)) for q in [0,.01,.1,.5,.9,.99,1]}
  result['full_overset'][key]=row
if all(v in result['force'] for v in ['SP_B','SP_C']):
 diff={}
 for key in result['force']['SP_B']:
  if key in result['force']['SP_C']:diff[key]=[c-b for c,b in zip(result['force']['SP_C'][key],result['force']['SP_B'][key])]
 result['force_C_minus_B_N']=diff
(h/'validation/BC_native_diagnosis.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result,indent=2))
