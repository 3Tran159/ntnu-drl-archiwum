"""Standalone scientific figures from accepted force windows and recorded step timing."""
import sys,csv,json,os,datetime
from pathlib import Path
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R.parent/'quasi2d_012_20261029'/'deps311'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter,MaxNLocator
import numpy as np
from mesh_convergence import plot_signature
plt.rcParams.update({'font.size':11,'font.family':'DejaVu Sans','svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
d=json.loads((R/'mesh_convergence.json').read_text(encoding='utf-8'))
rows=d['settled_results']
valid=[r for r in rows if r.get('Fx_pressure_N') is not None and r.get('Fx_viscous_N') is not None]
fig,axes=plt.subplots(1,2,figsize=(13,4.9),layout='constrained')
force,runtime=axes
if valid:
    x=np.arange(len(valid))
    pressure=np.array([r['Fx_pressure_N'] for r in valid])
    viscous=np.array([r['Fx_viscous_N'] for r in valid])
    bottom=np.where(viscous>=0,np.maximum(pressure,0),np.minimum(pressure,0))
    force.bar(x,pressure,.62,color='#5267ad',label='Pressure')
    force.bar(x,viscous,.62,bottom=bottom,color='#288578',label='Viscous')
    top=np.maximum(pressure,0)+np.maximum(viscous,0)
    for i,r in enumerate(valid):
        force.annotate(f"{r['Fx_total_N']:.2f}",(i,top[i]),xytext=(0,5),textcoords='offset points',ha='center',fontsize=10)
    force.set_xticks(x,[r['id']+'\n'+f"{r['cells']/1000:.0f}k cells" for r in valid])
    force.set_ylim(bottom=min(0,float(np.min(pressure+np.minimum(viscous,0))))*1.18,top=max(top)*1.23)
    force.legend(loc='upper right',frameon=False,ncol=2,fontsize=10)
else:
    force.text(.5,.5,'Waiting for accepted force components',ha='center',transform=force.transAxes)
force.set(title='Mean drag: pressure + viscosity',ylabel='Fx on the 20 mm slice [N]')
force.grid(axis='y',alpha=.2);force.set_axisbelow(True)
timed=[r for r in rows if r.get('wall_s_per_step_median') is not None]
for family,color,label,offset,style in [('wall_function','#D55E00','Wall-function spacing',11,'--o'),('low_yplus','#0072B2','Fine near-wall spacing',-17,'-s')]:
    group=sorted((r for r in timed if r['family']==family),key=lambda r:r['cells'])
    if not group:continue
    runtime.plot([r['cells'] for r in group],[r['wall_s_per_step_median'] for r in group],style,color=color,lw=1.6,ms=6,label=label)
    for r in group:
        runtime.annotate(r['id'],(r['cells'],r['wall_s_per_step_median']),xytext=(-9,10) if r['id']=='M06' else (6,offset),ha='right' if r['id']=='M06' else 'left',textcoords='offset points',fontsize=10,color=color,bbox=dict(facecolor='white',edgecolor='none',pad=.3,alpha=.9))
if timed:
    runtime.set_ylim(0,max(r['wall_s_per_step_median'] for r in timed)*1.42)
    runtime.margins(x=.16)
    runtime.legend(loc='upper left',frameon=False,fontsize=10)
else:
    runtime.text(.5,.5,'Waiting for recorded step intervals',ha='center',transform=runtime.transAxes)
runtime.set(title='Computing time versus mesh size',xlabel='Mesh cells',ylabel='Median wall time / physical step [s]')
runtime.xaxis.set_major_formatter(FuncFormatter(lambda v,pos:f'{v/1000:,.0f}k'))
runtime.xaxis.set_major_locator(MaxNLocator(6))
runtime.grid(alpha=.2)
fig.suptitle('Accepted states | final 0.2 s windows | one step = 1 ms, 20 inner iterations',fontsize=12)
for extension in ['png','svg']:
    output=R/('mesh_force_cost.'+extension)
    tmp=output.with_name(output.name+f'.{os.getpid()}.tmp')
    fig.savefig(tmp,format=extension,dpi=160)
    tmp.replace(output)
plt.close(fig)
keys=['id','cells','family','window_start_s','time_s','CD','CL_total','Fx_pressure_N','Fx_viscous_N','Fx_total_N','wall_s_per_step_median','wall_s_per_step_mean','timing_intervals','timing_window_start_s','timing_window_end_s','observed_inner_iterations_per_step']
p=R/'mesh_force_cost.csv';tmp=p.with_name(p.name+f'.{os.getpid()}.tmp')
with tmp.open('w',encoding='utf-8',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=keys,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
tmp.replace(p)
meta={'signature':plot_signature(rows),'generated_at':datetime.datetime.now().astimezone().isoformat(),'meshes':[r['id'] for r in rows],'timing_method':d['timing_method'],'source':'mesh_convergence.json; force components from independent STAR reports in the accepted final 0.2 s window','files':['mesh_force_cost.png','mesh_force_cost.svg','mesh_force_cost.csv']}
p=R/'mesh_force_cost_provenance.json';tmp=p.with_name(p.name+f'.{os.getpid()}.tmp')
tmp.write_text(json.dumps(meta,indent=2),encoding='utf-8');tmp.replace(p)
print('Updated force-component and runtime figure: '+', '.join(meta['meshes']))
