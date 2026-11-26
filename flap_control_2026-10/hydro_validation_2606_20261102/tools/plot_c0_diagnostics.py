from pathlib import Path
import sys,json
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h/'tools/deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
ref=json.loads((h/'validation/NIGHT_C0_readonly_review.json').read_text(encoding='utf8'))
runs=[('C0: 15 iteracji',Path(ref['source_result']),'#9879b5'),('C0: 40 iteracji',h/'cases/SP_C_split0_overset/c0_inner40_20261102_223940','#d68a1e')]
if len(sys.argv)>1:runs.append(('C0: interpolacja odległościowa',Path(sys.argv[1]),'#007d99'))
fig,axes=plt.subplots(3,2,figsize=(13,10),layout='constrained')
columns=['CL_hydro','CD','Mh_Nm','p_absolute_min_Pa','mass_imbalance_relative','omega_floor_cells']
labels=['CL hydrodynamiczne','CD','Moment zawiasowy [Nm]','Minimalne ciśnienie bezwzględne [Pa]','Względny bilans masy','Komórki z ω na dolnym ograniczeniu']
for name,path,color in runs:
 if not (path/'history.csv').exists():continue
 d=pd.read_csv(path/'history.csv')
 for ax,col,label in zip(axes.flat,columns,labels):
  if col in d:ax.plot(d.time_s,d[col],label=name,color=color,linewidth=1.5)
for ax,col,label in zip(axes.flat,columns,labels):
 ax.set_xlabel('Czas fizyczny [s]');ax.set_ylabel(label);ax.grid(alpha=.2)
 if col=='CL_hydro':ax.axhline(.32729653634048,color='black',ls='--',label='B: bez Overset')
 if col=='CD':ax.axhline(.007163580556642399,color='black',ls='--',label='B: bez Overset')
 if col=='Mh_Nm':ax.axhline(-12.1660832,color='black',ls='--',label='B: bez Overset')
 if col=='p_absolute_min_Pa':ax.axhline(12339.214766776897,color='#c03739',ls='--',label='Próg: para + 10 kPa')
 if col=='mass_imbalance_relative':ax.set_yscale('symlog',linthresh=1e-8);ax.axhline(1e-4,color='#c03739',ls='--',label='Próg okna sił')
 if col=='omega_floor_cells' and len(ax.lines)==0:ax.text(.5,.5,'Eksport rozpocznie się w teście interpolacji',ha='center',va='center',transform=ax.transAxes)
 if len(ax.lines):ax.legend(fontsize=8)
fig.suptitle('C0 — kontrolowane testy diagnostyczne; wyniki niezatwierdzone\nTa sama geometria, siatka 361 532 komórek, U = 18 m/s, Δt = 0,002 s',fontsize=14)
target=h/'reports/C0_night_diagnostics.png';fig.savefig(target,dpi=160);plt.close(fig);print(target)
