from pathlib import Path
import sys,json,numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h/'tools/deps'))
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
b=h/'cases/SP_B_split0_fixed/steady_init_20261102_195203/stabilize_20261102_195203/foil_pressure.csv'
c=h/'audit/comparison_SP_C_20261102_222216'
db=pd.read_csv(b);dc=pd.concat([pd.read_csv(c/'main_wall.csv'),pd.read_csv(c/'flap_wall.csv')])
fig,ax=plt.subplots(3,1,figsize=(12,11),constrained_layout=True)
for df,label,color,mark in [(db,'B: klapka 0°, bez Overset, t=0.3000 s','#087f8c','o'),(dc,'C: klapka 0°, Overset, t=0.3024 s — niezatwierdzona','#cf6b17','x')]:
 ax[0].scatter(df['X (m)']/1.19,df['Pressure (Pa)']/162000,s=7,c=color,marker=mark,label=label,alpha=.8)
 ax[1].scatter(df['X (m)']/1.19,df['Pressure (Pa)']/162000,s=10,c=color,marker=mark,alpha=.85)
 ax[2].scatter(df['X (m)']/1.19,df['Wall Y+'],s=7,c=color,marker=mark,alpha=.8)
ax[0].invert_yaxis();ax[1].invert_yaxis()
ax[0].set_ylabel('Cp = p piezometryczne / q');ax[1].set_ylabel('Cp — otoczenie zawiasu')
ax[1].set_xlim(.55,1.02);ax[2].set_yscale('log');ax[2].set_ylabel('y+');ax[2].set_xlabel('x/c')
for a in ax:
 a.grid(alpha=.2);a.axvline(.8,c='#777',ls=':',lw=1);a.axvline(.732/1.19,c='#a22',ls='--',lw=1)
ax[0].legend(loc='upper left',fontsize=9)
fig.suptitle('B/C: ten sam płat i warunki fizyczne, różne siatki i Overset\nLinia przerywana: początek klatki Overset; kropkowana: zawias',fontsize=14)
out=h/'reports/BC_current_Cp_yplus_diagnostic.png';fig.savefig(out,dpi=150);plt.close(fig)
summary={}
for name,df in [('B',db),('C',dc)]:
 summary[name]=dict(wall_samples=len(df),pabs_min=float(df['Absolute Pressure (Pa)'].min()) if 'Absolute Pressure (Pa)' in df else None,columns=list(df),yplus_max=float(df['Wall Y+'].max()),zones=[])
 for lo,hi in [(0,.55),(.55,.7),(.7,.8),(.8,1)]:
  sub=df[df['X (m)'].between(lo*1.19,hi*1.19)];summary[name]['zones'].append(dict(xc=[lo,hi],Cpmin=float(sub['Pressure (Pa)'].min()/162000),Cpmax=float(sub['Pressure (Pa)'].max()/162000),yplusmax=float(sub['Wall Y+'].max())))
(h/'validation/BC_current_wall_diagnostic.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
print(json.dumps(summary,indent=2));print(str(out))
