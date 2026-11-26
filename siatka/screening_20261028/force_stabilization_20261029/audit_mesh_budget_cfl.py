"""Cell census and physical convective-CFL diagnostics from accepted saved fields."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
import sys,json,csv,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029';sys.path.insert(0,str(Q/'deps311'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.patches import Rectangle
snap=json.loads((R/'selected_snapshots.json').read_text())
labels=['Foil refinement box','Free-surface band','Downstream corridor','Deep water','Upper air','Remaining outer cells']
colors=['#305d72','#2d8d99','#a58149','#547fb0','#bdcbd1','#929b9e']
result={};mapdata=None
def stats(v):
 return {'n':int(len(v)),'p50':float(np.percentile(v,50)),'p95':float(np.percentile(v,95)),'p99':float(np.percentile(v,99)),'max':float(v.max()),'cells_above1_pct':float(100*np.mean(v>1))} if len(v) else None
for mesh,s in snap.items():
 if s['status']!='Settled':continue
 a=np.loadtxt(s['velocity'],delimiter=',',skiprows=1)
 assert a.shape[1]==9 and np.isfinite(a).all()
 n=len(a);x=a[:,6];z=a[:,8];vf=a[:,4];co=a[:,5];vel=np.sqrt(np.sum(a[:,:3]**2,axis=1))
 expected=json.loads((Q/mesh/'measurement.json').read_text())['metrics']['cell_count'];assert n==expected,(mesh,n,expected)
 with Path(s['history']).open() as f:history=list(csv.DictReader(f))
 last=history[-1];dt=float(last['dt_s']);interface=(vf>.01)&(vf<.99)
 imax=int(co.argmax());inds=np.where(interface)[0];jmax=int(inds[np.argmax(co[interface])]) if len(inds) else None
 def loc(i):return None if i is None else {'x_m':float(x[i]),'z_m':float(z[i]),'water_fraction':float(vf[i]),'speed_m_s':float(vel[i]),'CFL':float(co[i])}
 masks=[(x>=-.6)&(x<=3)&(z>=-.6)&(z<=.6),(z>=1.6)&(z<=2.4),(x>3)&(x<=10)&(abs(z)<=.6),z<-2,z>2.4]
 assign=np.full(n,5)
 for i,m in reversed(list(enumerate(masks))):assign[m]=i
 counts=[int(np.sum(assign==i)) for i in range(6)];assert sum(counts)==n
 nearfs=(z>=1.9)&(z<=2.1)
 groups=[{'region':label,'cells':count,'share_pct':100*count/n} for label,count in zip(labels,counts)]
 cfl={'dt_s':dt,'snapshot_time_s':s['time_s'],'all_cells':stats(co),'interface_cells':stats(co[interface]),'global_max_location':loc(imax),'interface_max_location':loc(jmax),
 'history_global_max':float(last['max_CFL']),'history_interface_max':float(last['interface_max_CFL']),
 'field_report_global_abs_difference':abs(float(co.max())-float(last['max_CFL'])),
 'field_report_interface_abs_difference':None if jmax is None else abs(float(co[jmax])-float(last['interface_max_CFL'])),
 'dt_for_interface_CFL1_frozen_field_s':None if jmax is None else dt/float(co[jmax]),
 'dt_for_interface_CFL05_frozen_field_s':None if jmax is None else .5*dt/float(co[jmax]),
 'review':'Check VOF substepping and time-step sensitivity before final validation; convective CFL>1 is not by itself an implicit-solver instability proof.'}
 assert cfl['field_report_global_abs_difference']<1e-6,(mesh,cfl)
 assert cfl['field_report_interface_abs_difference'] is None or cfl['field_report_interface_abs_difference']<1e-6,(mesh,cfl)
 result[mesh]={'cells':n,'time_s':s['time_s'],'regions':groups,'cfl':cfl,'cells_within_0p1m_of_calm_surface':int(nearfs.sum()),'cells_in_FS_band_outside_0p1m':int(((assign==1)&~nearfs).sum())}
 if mesh=='M07':mapdata=(x.copy(),z.copy())
document={'updated_at':datetime.datetime.now().astimezone().isoformat(),'cases':result,
 'regions':'Mutually exclusive cell-centroid bins. Foil control x[-0.6,3],z[-0.6,0.6]m; full-width FS control z[1.6,2.4]m. Downstream diagnostic corridor x(3,10],|z|<=0.6m; deep water z<-2m; upper air z>2.4m; remainder. Foil and FS bounds come from the mesh-creation macro; other bins are diagnostic partitions, not existing controls.',
 'limits':['Counts indicate mesh cost, not removable cells or measured runtime savings.','CFL statistics count cells without volume weighting.','Interface uses0.01<water fraction<0.99, matching Stab_InterfaceCFL report.','Frozen-field dt estimates require recomputation after any mesh/velocity change.','VOF dynamic target0.5/max20 is configured in M07; reported step count is1. Verify active strategy and effective behavior; configuration alone does not prove substepping is active.','Wave meshes need separate propagation/interface resolution and matched calm validation.']}
(R/'mesh_budget_cfl.json').write_text(json.dumps(document,indent=2))
chosen=[m for m in ['M04','M06','M07','M08'] if m in result]
plt.rcParams.update({'font.size':10,'font.family':'DejaVu Sans','svg.fonttype':'none'})
fig,axs=plt.subplots(1,2,figsize=(13,5),layout='constrained')
left=np.zeros(len(chosen))
for i,label in enumerate(labels):
 widths=np.array([result[m]['regions'][i]['cells']/1000 for m in chosen])
 axs[0].barh(chosen,widths,left=left,color=colors[i],label=label)
 left+=widths
for i,m in enumerate(chosen):axs[0].text(left[i]+2,i,f"{result[m]['cells']:,}",va='center',fontsize=9)
axs[0].set(xlabel='Cells [thousands]',title='Where the cells are allocated',xlim=(0,max(left)*1.20));axs[0].grid(axis='x',alpha=.18);axs[0].set_axisbelow(True)
axs[0].legend(fontsize=8,loc='lower right')
if mapdata:
 x,z=mapdata;xx=np.arange(-11.9,31.2,.25);zz=np.arange(-22,8.25,.25);H,xe,ze=np.histogram2d(x,z,bins=[xx,zz])
 im=axs[1].pcolormesh(xe,ze,np.ma.masked_equal(H.T,0),norm=LogNorm(vmin=1,vmax=float(H.max())),cmap='viridis',shading='auto')
 for rect in [(-.6,-.6,3.6,1.2),(-11.9,1.6,42.84,.8)]:axs[1].add_patch(Rectangle(rect[:2],rect[2],rect[3],fill=False,edgecolor='#ad4b2c',linewidth=1))
 axs[1].plot([0,1.19],[0,0],color='black',linewidth=2);axs[1].set(xlabel='x [m]',ylabel='z [m]',title='M07 cell count in 0.25 × 0.25 m bins',xlim=(-11.9,30.94),ylim=(-22,8));axs[1].set_aspect('equal')
 fig.colorbar(im,ax=axs[1],label='Cells per bin (log scale)',shrink=.8)
fig.savefig(R/'mesh_cell_budget.png',dpi=160);fig.savefig(R/'mesh_cell_budget.svg');plt.close(fig)
print(json.dumps({m:{'cells':d['cells'],'regions':d['regions'],'cfl_global':d['cfl']['global_max_location'],'cfl_interface':d['cfl']['interface_max_location'],'interface_p99':d['cfl']['interface_cells']['p99']} for m,d in result.items()}))
