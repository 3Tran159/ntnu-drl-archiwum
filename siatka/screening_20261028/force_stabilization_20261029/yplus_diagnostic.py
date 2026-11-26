import csv,json,re,sys,datetime,math
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
sys.path.insert(0,str(Q/'deps311'))
snapshots=json.loads((R/'selected_snapshots.json').read_text())
colours={'M03':'#187b73','M02':'#bf5a28','M04':'#5267ad','M05':'#6d7136','M06':'#963c77','M07':'#2d6590','M08':'#705841','M09':'#408f61','M10':'#805f9c'}
snapshot_label=' | '.join(m+' '+v['status']+' t='+format(v['time_s'],'.3f')+' s' for m,v in snapshots.items())
import numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':12,'font.family':'DejaVu Sans','svg.fonttype':'none'})
def csvrows(p):
 try:
  with p.open(encoding='utf-8-sig',newline='') as f:return [{k:float(v) for k,v in r.items()} for r in csv.DictReader(f) if all(v is not None and v!='' for v in r.values())]
 except (OSError,ValueError):return []
def live_yplus(folder):
 path=folder/'star.log'
 if not path.exists():return []
 fields=None;tt=None;out=[]
 crosscheck={round(a['physical_time_s'],7):a for a in csvrows(folder/'history.csv')}
 with path.open(encoding='utf-8',errors='replace') as f:
  for line in f:
   if 'Iteration' in line and 'Short_MaxYplus' in line and 'Continuity' in line:fields=re.split(r'\s{2,}',line.strip())
   mm=re.search(r'^TimeStep\s+\d+: Time\s+([\d.eE+-]+)',line)
   if mm:tt=float(mm.group(1))
   if fields and tt is not None and re.match(r'^\s*\d+\s',line):
    vals=line.split()
    if len(vals)>=17:
     try:
      a=list(map(float,vals));h=crosscheck.get(round(tt,7))
      # Pilot monitor schema: first diagnostic group follows 12 solver columns.
      # Verify both mean y+ and Fx against the independently written history.
      if h and abs(a[14]-h['mean_yplus'])<.0001 and abs(a[8]-h['Fx_slice_N'])<.0001:
       out.append({'time':tt,'mean':a[14],'min':a[16],'max':a[15]})
     except (ValueError,KeyError):pass
 return out
def wquantile(x,w,q):
 ix=np.argsort(x);return float(x[ix][np.searchsorted(np.cumsum(w[ix])/sum(w),q)])
jobs=json.loads((R/'queue.json').read_text());summary={};histories={}
fig,hax=plt.subplots(3,1,figsize=(11,9),layout='constrained')
distribution,dax=plt.subplots(figsize=(11,3.4),layout='constrained')
axes=np.array([[hax[0],hax[1]],[hax[2],dax]])
fig2,ax2=plt.subplots(2,2,figsize=(13,8),layout='constrained')
bins=[0,1,5,30,100,300,float('inf')];labels=['<1','1–5','5–30','30–100','100–300','>300']
registry=json.loads((R/'campaign_registry.json').read_text())
layer_counts={c['id']:c['layers'] for c in registry['cases']}
for n,mesh in enumerate(layer_counts):
 color=colours[mesh]
 pilot=Q/(mesh+'_GPU')/'F18_dt1000us_long'
 old=csvrows(pilot/'history.csv')
 hh=[{'time':r['physical_time_s'],'mean':r['foil_mean_yplus'],'min':r['foil_min_yplus'],'max':r['foil_max_yplus']} for r in old]
 for j in jobs:
  if j['id'].startswith(mesh+'_'):
   direct=csvrows(R/j['id']/'history.csv')
   if direct and 'min_yplus' in direct[-1]:hh += [{'time':a['physical_time_s'],'mean':a['mean_yplus'],'min':a['min_yplus'],'max':a['max_yplus']} for a in direct]
   else:hh+=live_yplus(R/j['id'])
 hh=list({round(a['time'],8):a for a in hh}.values());hh.sort(key=lambda a:a['time']);histories[mesh]=hh
 for ax,key,title in [(axes[0,0],'max','Maximum wall y+ over time'),(axes[0,1],'mean','Area-weighted mean wall y+'),(axes[1,0],'min','Minimum wall y+ over time')]:
  ax.plot([a['time'] for a in hh if a['time']>=.2-1e-8],[a[key] for a in hh if a['time']>=.2-1e-8],label=mesh,color=color,lw=1.8);ax.set(title=title,xlabel='Physical time [s]',ylabel='Wall y+');ax.grid(alpha=.2);ax.legend()
 if mesh not in snapshots:continue
 n=list(snapshots).index(mesh)
 rr=csvrows(Path(snapshots[mesh]['wall']));xyz=np.array([[a['X (m)'],a['Z (m)']] for a in rr]);yy=np.array([a['Wall Y+'] for a in rr])
 face=csvrows(R/(mesh+'_pressure_face_contributions.csv'));fxyz=np.array([[a['x'],a['z']] for a in face])
 match=np.argmin(np.linalg.norm(fxyz[:,None,:]-xyz[None,:,:],axis=2),axis=1);yv=yy[match];weights=np.array([a['edge_length_m']*.02 for a in face])
 fractions=[100*float(weights[(yv>=lo)&(yv<hi)].sum()/weights.sum()) for lo,hi in zip(bins[:-1],bins[1:])]
 weightedmean=float(np.average(yv,weights=weights))
 imax=int(np.argmax(yv))
 topo=csvrows(Q/mesh/'foil_layer_topology.csv');txz=np.array([[a['x'],a['z']] for a in topo]);ti=np.argmin(np.linalg.norm(fxyz[:,None,:]-txz[None,:,:],axis=2),axis=1)
 height=np.array([topo[i]['first_thickness_m'] for i in ti]);layers=np.array([topo[i]['continuous_quad_layers'] for i in ti]);valid=(layers>=layer_counts[mesh])&(yv>1e-8)&(height>0)
 required=height[valid]/yv[valid]*1e6
 vals={'snapshot_time_s':snapshots[mesh]['time_s'],'status':snapshots[mesh]['status'],'min':float(yv.min()),'area_mean':weightedmean,'max':float(yv.max()),'max_at_x_over_c':float(fxyz[imax,0]/1.19),'max_at_z_m':float(fxyz[imax,1]),'max_at_continuous_layers':float(layers[imax]),'area_fraction_pct':dict(zip(labels,fractions)),'area_weighted_p50':wquantile(yv,weights,.5),'area_weighted_p95':wquantile(yv,weights,.95),'area_weighted_p99':wquantile(yv,weights,.99),'first_full_layer_um_for_yplus1_frozen_shear':{'p05':wquantile(required,weights[valid],.05),'p50':wquantile(required,weights[valid],.5),'p95':wquantile(required,weights[valid],.95)},'latest_time_s':hh[-1]['time'],'latest':hh[-1],'weighted_mean_crosscheck_abs':abs(weightedmean-snapshots[mesh]['mean_yplus'])}
 summary[mesh]=vals
 axes[1,1].bar(np.arange(len(labels))+(n-(len(snapshots)-1)/2)*(.8/len(snapshots)),fractions,.8/len(snapshots),label=mesh,color=color)
 for upper in [True,False]:
  keep=np.array([a['area_z_m2']<0 for a in face])==upper;ix=np.where(keep)[0];ix=ix[np.argsort(fxyz[ix,0])]
  for ax in ax2[0]:
   ax.plot(fxyz[ix,0]/1.19,yv[ix],color=color,ls='-' if upper else '--',lw=1.5,label=mesh+(' upper' if upper else ' lower'))
 ax2[1,0].scatter(fxyz[:,0]/1.19,height*1e6,s=10,color=color,label=mesh)
 ax2[1,1].scatter(fxyz[:,0]/1.19,layers,s=9,color=color,label=mesh)
 for ax in ax2[0]:
  ax.scatter(fxyz[imax,0]/1.19,yv[imax],color=color,s=45,marker='x')
axes[1,1].set(xticks=np.arange(len(labels)),xticklabels=labels,ylabel='Foil surface area [%]',xlabel='Wall y+ range',title='Area-weighted wall y+ distribution');axes[1,1].legend();axes[1,1].grid(axis='y',alpha=.2)
for ax in axes.flat[:3]:
 for val,sty in [(1,':'),(5,':'),(30,'--')]:ax.axhline(val,color='#555',lw=.8,ls=sty)
 ax.axvline(.2,color='#888',ls=':',lw=.8)
axes[0,0].text(.98,.97,'Reference lines: y+ = 1, 5 and 30',transform=axes[0,0].transAxes,ha='right',va='top',fontsize=9)
fig.suptitle('Wall y+ histories | t ≥ 0.2 s')
for ax in hax:ax.set_xlim(left=.2);ax.margins(y=.12)
distribution.suptitle(snapshot_label,fontsize=10)
distribution.savefig(R/'yplus_distribution.png',dpi=170);distribution.savefig(R/'yplus_distribution.svg');plt.close(distribution)
fig.savefig(R/'yplus_history_distribution.png',dpi=160);fig.savefig(R/'yplus_history_distribution.svg');plt.close(fig)
for ax in ax2.flat:ax.grid(alpha=.2);ax.set_xlabel('x/c');ax.legend(fontsize=8)
for ax in ax2[0]:
 ax.set_ylabel('Wall y+')
 for val in [1,5,30]:ax.axhline(val,color='#888',lw=.8,ls=':')
ax2[0,0].set_title('Wall y+ along the foil')
ax2[0,1].set(xlim=(.93,1.005),title='Trailing edge - localized peaks')
ax2[1,0].set(ylabel='Actual first-layer thickness [µm]',title='Layer thickness from mesh connectivity')
ax2[1,1].axhline(15,color='#777',ls=':')
ax2[1,1].set(ylabel='Consecutive regular layers',title='Actual layer coverage')
fig2.suptitle('Wall resolution and layer coverage\n'+snapshot_label)
fig2.savefig(R/'yplus_spatial_m04.png',dpi=160);fig2.savefig(R/'yplus_spatial_m04.svg');plt.close(fig2)
summary['updated_at']=datetime.datetime.now().astimezone().isoformat()
summary['sources']={'Siemens_2602_setup':r'E:\Program Files\Siemens\21.02.007-R8\STAR-CCM+21.02.007-R8\doc\en\online\STARCCMP\GUID-70D648E4-1172-43E5-8F45-C8D92F12D814.html','NASA_SST_wall_spacing':'https://nasa.github.io/CFL3D/Cfl3dv6/cfl3dv6_testcases.html'}
yout=R/'yplus_summary.json';ytmp=yout.with_suffix('.json.tmp');ytmp.write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8');ytmp.replace(yout)
for mesh,hh in histories.items():
 with (R/(mesh+'_yplus_history.csv')).open('w',newline='') as f:
  wr=csv.DictWriter(f,fieldnames=['time','min','mean','max']);wr.writeheader();wr.writerows(hh)
print(json.dumps(summary,ensure_ascii=False))
