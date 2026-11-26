from pathlib import Path
import sys,json
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h/'tools/deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm,Normalize
from matplotlib.patches import Polygon
import pandas as pd,numpy as np
run=Path(sys.argv[1]);label=sys.argv[2];g=json.loads((h/'geometry/gap_002500um/geometry.json').read_text())
sets=[('B — bez Overset',h/'audit/comparison_SP_B_20261102_222923',''),('C0 — przed zmianą',run,'continuation_initial_'),('C0 — po zmianie',run,label+'_')]
fig,axs=plt.subplots(2,3,figsize=(15,7),sharex=True,sharey=True,layout='constrained')
for col,(name,folder,tag) in enumerate(sets):
 frames=[]
 for region in ['Background','FlapOverset']:
  p=folder/(region+'_'+tag+'volume.csv')
  if not p.exists():continue
  d=pd.read_csv(p)
  if 'Overset Cell Status' in d:d=d[d['Overset Cell Status']==0]
  d=d[d['X (m)'].between(.65,1.30)&d['Z (m)'].between(-.10,.18)].copy();frames.append(d)
 assert frames,name
 d=pd.concat(frames,ignore_index=True);d['p0q']=(d['Pressure (Pa)']+500*sum(d['Velocity['+k+'] (m/s)']**2 for k in 'ijk'))/162000
 floors=d[d['Specific Dissipation Rate (/s)']<=1.0001e-10]
 for row,(field,norm,cmap) in enumerate([('Turbulent Viscosity Ratio',LogNorm(.01,1e5),'viridis'),('p0q',Normalize(.5,3),'coolwarm')]):
  ax=axs[row,col];im=ax.scatter(d['X (m)'],d['Z (m)'],c=d[field],norm=norm,cmap=cmap,s=2,rasterized=True)
  for k in ['main','flap']:ax.add_patch(Polygon(g[k+'_polygon'],facecolor='#dddddd',edgecolor='black',linewidth=.5,zorder=5))
  if row==0:ax.scatter(floors['X (m)'],floors['Z (m)'],s=2,color='red',zorder=4,label='ω na ograniczeniu')
  ax.set_xlim(.65,1.30);ax.set_ylim(-.10,.18);ax.set_aspect('equal');ax.set_xlabel('x [m]')
  if col==0:ax.set_ylabel('z [m]')
  if row==0:ax.set_title(name+'\nω na ograniczeniu w widoku: '+str(len(floors)),fontsize=10)
  if col==2:fig.colorbar(im,ax=axs[row,:],shrink=.85,label='μt/μ' if row==0 else '(p piez. + ρ|U|²/2) / q∞')
fig.suptitle('Lokalne pola: kontrolowana zmiana na identycznej siatce C0 — '+label+'\nParametr energii średniego przepływu służy do diagnostyki; nie jest ścisłą granicą Bernoulliego.',fontsize=13)
target=h/'reports'/('C0_controlled_fields_'+run.name+'_'+label+'.png');fig.savefig(target,dpi=160);plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(13,4),layout='constrained')
for name,folder,tag in sets:
 for group in ['main','flap']:
  p=folder/(group+'_'+tag+'wall.csv')
  if not p.exists():continue
  d=pd.read_csv(p);color={'B — bez Overset':'black','C0 — przed zmianą':'#d68a1e','C0 — po zmianie':'#00859c'}[name]
  for ax,field,div in [(axs[0],'Pressure (Pa)',162000),(axs[1],'Wall Y+',1)]:
   if field not in d:continue
   ax.scatter(d['X (m)']/1.19,d[field]/div,s=4,alpha=.7,color=color,label=name if group=='main' else None)
for ax,ylabel in zip(axs,['Cp (ciśnienie piezometryczne)','y+']):
 ax.axvline(.8,color='gray',ls=':',label='Zawias x/c=0,80');ax.set_xlim(.55,1.01);ax.set_xlabel('x/c');ax.set_ylabel(ylabel);ax.grid(alpha=.2);ax.legend(fontsize=8)
fig.suptitle('Powierzchnia płata i klapki 0° — '+label+'; wynik diagnostyczny niezatwierdzony')
wall=h/'reports'/('C0_controlled_Cp_'+run.name+'_'+label+'.png');fig.savefig(wall,dpi=160);plt.close(fig)
print(target);print(wall)
