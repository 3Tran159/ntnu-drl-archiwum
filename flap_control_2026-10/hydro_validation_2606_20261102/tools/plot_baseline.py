from pathlib import Path
import sys,json
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools/deps'))
import pandas as pd,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=R/'cases/SP_A_original_singlephase/steady_init_20261102_182100/smoke_20261102_183017';a=pd.read_csv(D/'foil_pressure.csv');a['x_over_c']=a['X (m)']/1.19;a['Cp_piezometric']=a['Pressure (Pa)']/162000;a.to_csv(D/'foil_pressure_normalized.csv',index=False)
y=a['Wall Y+'];summary={'wall_samples':len(a),'sample_weighted_yplus_quantiles':{str(q):float(y.quantile(q)) for q in [.5,.9,.95,.99,1]},'fraction_samples_yplus_gt5':float((y>5).mean()),'max_yplus_sample':a.loc[y.idxmax()].to_dict(),'interpretation':'Quantiles are sample-weighted, not surface-area-weighted. Native AreaAverageReport supplies area-weighted mean.'}
(R/'validation/SP_A_wall_diagnostics.json').write_text(json.dumps(summary,indent=2))
fig,axs=plt.subplots(2,1,figsize=(10,6),layout='constrained',sharex=True);axs[0].scatter(a['x_over_c'],a['Cp_piezometric'],s=5,c='#14679b');axs[0].invert_yaxis();axs[0].set(ylabel='Cp (bez składowej hydrostatycznej)',title='SP_A — profil oryginalny, woda jednofazowa, t = 0.008 s');axs[1].scatter(a['x_over_c'],y,s=5,c='#14679b');axs[1].set(yscale='log',xlabel='x/c',ylabel='y+');axs[1].axhline(1,c='#6d7880',ls=':',lw=1);axs[1].axhline(5,c='#b77913',ls='--',lw=1)
for ax in axs:ax.grid(alpha=.2)
fig.savefig(R/'reports/SP_A_pressure_yplus.png',dpi=160);plt.close(fig)
p=R/'tools/refresh_report.py';t=p.read_text(encoding="utf-8").replace("encoding='utf8-sig'","encoding='utf-8-sig'");p.write_text(t,encoding='utf8')
print(json.dumps(summary,indent=2))
