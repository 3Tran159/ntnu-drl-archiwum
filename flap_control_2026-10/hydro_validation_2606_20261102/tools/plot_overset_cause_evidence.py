from pathlib import Path
import sys,json,pandas as pd,numpy as np
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h/'tools/deps'))
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.patches import Polygon
g=json.loads((h/'geometry/gap_002500um/geometry.json').read_text())
b=h/'audit/comparison_SP_B_20261102_222923';c=h/'audit/comparison_SP_C_20261102_223230'
def walls(ax):
 for key in ['main_polygon','flap_polygon']:ax.add_patch(Polygon(g[key],facecolor='white',edgecolor='#161616',lw=1,zorder=4))
 ax.set_aspect('equal');ax.set_xlim(.71,1.05);ax.set_ylim(-.085,.15);ax.set_xlabel('x [m]');ax.set_ylabel('z [m]')
fig,axes=plt.subplots(2,1,figsize=(12,10),constrained_layout=True)
acceptors=[]
for region in ['Background','FlapOverset']:
 df=pd.read_csv(c/(region+'_full_plane.csv'));df=df[df['Overset Cell Status'].isin([-2,-1])].copy();df['region']=region;acceptors.append(df)
ad=pd.concat(acceptors)
sc=axes[0].scatter(ad['X (m)'],ad['Z (m)'],c=ad['Overset Interpolation Cell Size Ratio'],s=14,norm=LogNorm(vmin=.25,vmax=10),cmap='viridis')
walls(axes[0]);axes[0].set_title('Niedopasowanie rozmiarów komórek akceptor / donor — wskaźnik STAR');fig.colorbar(sc,ax=axes[0],label='Wskaźnik rozmiaru komórek')
colors={0:'#dd6b20',2:'#2477b2',7:'#82912b'}
for k,label in [(0,'0: distance weighted'),(2,'2: linear quasi-2D'),(7,'7: ghost-cell interpolation')]:
 d=ad[ad['Overset Interpolation Type']==k];axes[1].scatter(d['X (m)'],d['Z (m)'],s=10,color=colors[k],label=label)
walls(axes[1]);axes[1].legend(fontsize=9,loc='upper right');axes[1].set_title('Rzeczywisty typ interpolacji w pełnym zbiorze 2559 akceptorów')
fig.suptitle('C0: łączność poprawna, lokalna dokładność nadal niezatwierdzona',fontsize=14)
fig.savefig(h/'reports/C0_overset_resolution_diagnostic.png',dpi=150);plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(14,6),constrained_layout=True)
summary={}
for ax,label,folder in [(axes[0],'B — bez Overset',b),(axes[1],'C — Overset (niezatwierdzony)',c)]:
 all_df=[]
 for p in folder.glob('*_volume.csv'):
  df=pd.read_csv(p)
  if 'Overset Cell Status' in df:df=df[df['Overset Cell Status']==0]
  all_df.append(df)
 df=pd.concat(all_df);zone=df[df['X (m)'].between(.71,1.05)&df['Z (m)'].between(-.085,.15)]
 sc=ax.scatter(zone['X (m)'],zone['Z (m)'],c=zone['Turbulent Viscosity Ratio'],s=3,norm=LogNorm(vmin=.01,vmax=100000),cmap='magma')
 walls(ax);ax.set_title(label);summary[label]=dict(active_cells=len(df),omega_at_floor=int((df['Specific Dissipation Rate (/s)']<=1.0001e-10).sum()),k_at_floor=int((df['Turbulent Kinetic Energy (J/kg)']<=1.0001e-10).sum()),turb_viscosity_at_cap=int((df['Turbulent Viscosity Ratio']>=99999).sum()),maximum_turb_viscosity_ratio=float(df['Turbulent Viscosity Ratio'].max()))
fig.colorbar(sc,ax=axes,label='Lepkość turbulentna / lepkość molekularna')
fig.suptitle('Porównanie pól turbulencji przy zawiasie',fontsize=14)
fig.savefig(h/'reports/BC_turbulence_diagnostic.png',dpi=150);plt.close(fig)
(h/'validation/BC_turbulence_floor_counts.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(json.dumps(summary,indent=2))
