from pathlib import Path
import shutil
R=Path(__file__).resolve().parent
p=R/'analyze_forces.py';s=p.read_text()
if not (R/'analyze_forces_before_readability.py').exists():shutil.copy2(p,R/'analyze_forces_before_readability.py')
s=s.replace("'font.size':10","'font.size':12")
s=s.replace("audit={};fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')","audit={};fig,top=plt.subplots(2,1,figsize=(11,7),layout='constrained');extra,low=plt.subplots(2,1,figsize=(11,7),layout='constrained');axes=np.array([top,low])")
s=s.replace('allrows=old+new','allrows=[r for r in old+new if r["physical_time_s"]>=.2-1e-8]')
s=s.replace("fig.suptitle('M03 / M02 - continuation from 0.2 s | first-order, dt = 1 ms | diagnostic only')","fig.suptitle('Force histories after startup | t ≥ 0.2 s',fontsize=15)\nextra.suptitle('Drag components and interface CFL',fontsize=15)\nfor ax in list(top)+list(low):ax.margins(x=.02,y=.12)\nextra.savefig(R/'force_components.png',dpi=170);extra.savefig(R/'force_components.svg');plt.close(extra)")
tmp=p.with_suffix('.tmp');tmp.write_text(s);tmp.replace(p)
print('Static force figures rescaled.')
