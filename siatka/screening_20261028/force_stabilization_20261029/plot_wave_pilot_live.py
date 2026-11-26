import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import sys,csv,json,math,datetime,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029';sys.path.insert(0,str(Q/'deps311'))
import numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
st=json.loads((R/'wave_propagation_state.json').read_text());p=Path(st['directory'])
raw_sources={}
def rows(path):
 import io
 raw_sources[str(path)]=path.read_text()
 return [{k:float(v) for k,v in x.items()} for x in csv.DictReader(io.StringIO(raw_sources[str(path)]))]
g=rows(p/'gauges.csv');h=rows(p/'history.csv')
assert g and h and all(math.isfinite(v) for a in g+h for v in a.values())
end=max(x['time_s'] for x in g)
fig,axes=plt.subplots(3,1,figsize=(10,7),layout='constrained',sharex=True,sharey=True)
metrics=[]
for ax,x in zip(axes,[0,2.5,5]):
 v=[a for a in g if abs(a['x_m']-x)<1e-8];t=np.array([a['time_s'] for a in v]);y=np.array([a['eta_actual_m'] for a in v]);ref=np.array([a['eta_analytic_m'] for a in v])
 ax.plot(t,y,color='#005f9e',lw=1.8,label='Computed');ax.plot(t,ref,color='#d25d00',lw=1.6,ls='--',label='Fifth-order reference')
 ax.set_ylabel('Elevation [m]');ax.set_title(f'Gauge x = {x:g} m',loc='left',fontsize=11);ax.grid(alpha=.18);ax.set_ylim(-.3,.32)
 metrics.append({'x_m':x,'samples':len(v),'available_trace_RMS_difference_mm':float(np.sqrt(np.mean((y-ref)**2))*1000),'available_trace_max_abs_difference_mm':float(abs(y-ref).max()*1000)})
axes[0].legend(loc='lower left',ncol=2,frameon=False);axes[-1].set_xlabel('Physical time [s]')
fig.suptitle(f'No-foil wave pilot | computed through {end:.3f} s',fontsize=14)
fig.savefig(R/'wave_pilot_live.png',dpi=160);fig.savefig(R/'wave_pilot_live.svg');plt.close(fig)
res=[]
for i in range(2,len(h)):
 dt=h[i]['time_s']-h[i-1]['time_s'];v=(3*h[i]['mass_kg']-4*h[i-1]['mass_kg']+h[i-2]['mass_kg'])/(2*dt)+h[i]['net_outward_mass_kg_s']
 res.append(abs(v)/h[i]['inward_mass_kg_s']*100)
out={'updated_at':datetime.datetime.now().astimezone().isoformat(),'case':p.name,'status':'pilot_in_progress' if st['status']=='propagation_CPU_running' else st['status'],'max_gauge_time_s':end,'max_history_time_s':h[-1]['time_s'],'all_independent_values_finite':True,'phase_bounds':[min(a['alpha_min'] for a in h),max(a['alpha_max'] for a in h)],'max_speed_m_s':max(a['max_speed_m_s'] for a in h),'max_interface_CFL':max(a['interface_CFL'] for a in h),'max_BDF2_mass_budget_pct_of_inlet':max(res),'gauges':metrics,'source':str(p/'gauges.csv'),'source_sha256':hashlib.sha256(raw_sources[str(p/'gauges.csv')].encode()).hexdigest(),'meaning':'Difference along the available partial trace only; not wave-height/phase/reflection validation or a force result. Period about0.8473s. Initialmeanleveloffset remains recorded.','figures':['wave_pilot_live.png','wave_pilot_live.svg']}
(R/'wave_pilot_live.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
