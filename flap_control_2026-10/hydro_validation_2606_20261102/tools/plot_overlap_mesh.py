from pathlib import Path
import sys,json
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h/'tools/deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.patches import Polygon,Rectangle
import pandas as pd,numpy as np
run=Path(sys.argv[1]).resolve();g=json.loads((h/'geometry/gap_002500um/geometry.json').read_text())
control=h/'cases/SP_C_split0_overset/c0_distance_20261102_232050'
fig,axs=plt.subplots(2,2,figsize=(12,8),sharex=True,sharey=True,layout='constrained')
for j,(title,folder,tag) in enumerate([('Kontrola — 361532 komórki',control,'final'),('Lokalna poprawka — 424982 komórki',run,'mesh')]):
 frames=[]
 for region in ['Background','FlapOverset']:
  d=pd.read_csv(folder/(region+'_'+tag+'_full_plane.csv'));d['region']=region;frames.append(d)
 f=pd.concat(frames,ignore_index=True);vcol=next(c for c in f if c.startswith('Volume'));rc='Overset Interpolation Cell Size Ratio'
 near=f[f['X (m)'].between(.70,1.08)&f['Z (m)'].between(-.085,.125)]
 acc=near[near['Overset Cell Status']<0]
 im=axs[0,j].scatter(acc['X (m)'],acc['Z (m)'],c=acc[rc],norm=LogNorm(.2,10),cmap='coolwarm',s=6)
 act=near[near['Overset Cell Status']==0]
 im2=axs[1,j].scatter(act['X (m)'],act['Z (m)'],c=np.sqrt(act[vcol]/.02)*1000,norm=LogNorm(.01,10),cmap='viridis',s=1,rasterized=True)
 bad=near[near['Overset Interpolation Type'].between(4,6)]
 axs[0,j].scatter(bad['X (m)'],bad['Z (m)'],marker='x',s=70,c='black',linewidths=2,zorder=10)
 axs[0,j].set_title(('Kontrola' if j==0 else 'Lokalna poprawka')+' — '+str(len(f))+' komórek\nTrudne stencile w widoku: '+str(len(bad)),fontsize=11)
 for i in range(2):
  ax=axs[i,j]
  for key in ['main','flap']:ax.add_patch(Polygon(g[key+'_polygon'],facecolor='#dddddd',edgecolor='black',lw=.7,zorder=5))
  ax.add_patch(Rectangle((.70,-.10),.255,.25,fill=False,edgecolor='#444444',ls='--',lw=.8,zorder=6))
  ax.set_xlim(.70,1.08);ax.set_ylim(-.085,.125);ax.set_aspect('equal');ax.set_xlabel('x [m]')
  if j==0:ax.set_ylabel('z [m]')
fig.colorbar(im,ax=axs[0,:],shrink=.8,label='Natywny wskaźnik rozmiarów komórek interpolacji')
fig.colorbar(im2,ax=axs[1,:],shrink=.8,label='Rozmiar równoważny aktywnej komórki √(V/b) [mm]')
fig.suptitle('Kontrola lokalnej poprawki siatki Overset\nGóra: akceptory; dół: aktywne komórki. Geometria i siatka tła zachowane.',fontsize=14)
target=h/'reports'/('C0_overlap_mesh_'+run.name+'.png');fig.savefig(target,dpi=160);plt.close(fig);print(target)
