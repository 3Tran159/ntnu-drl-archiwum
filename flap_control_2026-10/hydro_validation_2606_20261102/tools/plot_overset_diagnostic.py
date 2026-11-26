from pathlib import Path
import sys,json
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h/'tools/deps'))
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
b=h/'cases/SP_B_split0_fixed/steady_init_20261102_195203/stabilize_20261102_195203'
c=h/'cases/SP_C_split0_overset/motion_20261102_194119/steady_init_20261102_200834/steady_init_20261102_202530'
db=pd.read_csv(b/'foil_pressure.csv');dc=pd.concat([pd.read_csv(c/'wall_fixed.csv'),pd.read_csv(c/'wall_flap.csv')])
fig,ax=plt.subplots(2,1,figsize=(12,8),constrained_layout=True,sharex=True)
for df,label,color,m in [(db,'B: klapka 0°, URANS po stabilizacji','#146c94','o'),(dc,'C: Overset 0°, NIEZATWIERDZONA inicjalizacja steady','#cf7b20','x')]:
 ax[0].scatter(df['X (m)']/1.19,df['Pressure (Pa)']/162000,s=8,c=color,marker=m,label=label,alpha=.8)
 ax[1].scatter(df['X (m)']/1.19,df['Wall Y+'],s=8,c=color,marker=m,alpha=.8)
ax[0].invert_yaxis();ax[0].set_ylabel('Cp (ciśnienie piezometryczne / q)');ax[0].legend(loc='upper left',fontsize=9)
ax[1].set_yscale('log');ax[1].set_ylabel('y+ na ścianie');ax[1].set_xlabel('x/c')
for a in ax:a.grid(alpha=.2);a.axvline(.8,c='#777',ls=':',lw=1)
fig.suptitle('Diagnostyka B / C: rozkład ciśnienia i y+\nC wymaga dalszej kontroli bilansu masy i URANS — to nie jest wynik końcowy',fontsize=14)
fig.savefig(h/'reports/BC_unaccepted_steady_diagnostic.png',dpi=150);plt.close(fig)
print(str(h/'reports/BC_unaccepted_steady_diagnostic.png'))
