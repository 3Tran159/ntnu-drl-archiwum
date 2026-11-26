from pathlib import Path
import json,sys,numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h/'tools/deps'));sys.path.insert(0,str(h.parent/'flap_poc_2606_20261102/deps'))
from shapely.geometry import Polygon
from shapely import points,distance
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
g=json.loads((h/'geometry/gap_002500um/geometry.json').read_text());main=Polygon(g['main_polygon']);flap=Polygon(g['flap_polygon'])
sources={'B':h/'audit/comparison_SP_B_20261102_222923/Background_volume.csv','C background':h/'audit/comparison_SP_C_20261102_223230/Background_volume.csv','C overset':h/'audit/comparison_SP_C_20261102_223230/FlapOverset_volume.csv'}
out={};fig,axes=plt.subplots(1,2,figsize=(13,5.5),constrained_layout=True)
for label,file in sources.items():
 d=pd.read_csv(file)
 if 'Overset Cell Status' in d:d=d[d['Overset Cell Status']==0]
 q=d[d['X (m)'].between(.75,.915)].copy();pts=points(q[['X (m)','Z (m)']].to_numpy());dm=distance(pts,main.boundary);df=distance(pts,flap.boundary)
 mask=(dm>.0001)&(dm<.02)&(dm<df);q=q[mask].copy();q['native_wall_distance_m']=dm[mask];q['effective_cell_size_m']=np.sqrt(q['Volume (m^3)']/.02)
 out[label]=dict(cells=len(q),minimum_main_wall_distance_m=float(q.native_wall_distance_m.min()),maximum_main_wall_distance_m=float(q.native_wall_distance_m.max()),bins=[])
 for lo,hi in [(.0001,.0003),(.0003,.001),(.001,.003),(.003,.01),(.01,.02)]:
  a=q[q.native_wall_distance_m.between(lo,hi)]
  out[label]['bins'].append(dict(wall_distance_m=[lo,hi],cells=len(a),median_sqrt_cell_area_m=float(a.effective_cell_size_m.median()) if len(a) else None))
 for ax,(lo,hi) in zip(axes,[(.75,.85),(.85,.915)]):
  a=q[q['X (m)'].between(lo,hi)];ax.scatter(a.native_wall_distance_m*1000,a.effective_cell_size_m*1000,s=3,label=label,alpha=.5)
  ax.set_title('x = '+str(lo)+'–'+str(hi)+' m');ax.set_xlabel('Odległość od rodzimego obrysu [mm]');ax.set_ylabel('√(pole komórki w przekroju) [mm]');ax.set_xscale('log');ax.set_yscale('log');ax.grid(alpha=.2)
axes[0].legend(markerscale=3);fig.suptitle('Rozdzielczość aktywnych komórek przy nieruchomej części płata\nMiara pola nie zastępuje oceny anizotropii warstw przyściennych',fontsize=12)
fig.savefig(h/'reports/BC_nearwall_resolution.png',dpi=150);plt.close(fig)
(h/'validation/BC_nearwall_resolution.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out,indent=2))
