"""Actual geometry/field review for conservative mesh-cost reduction; no solver changes."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import sys,json,csv,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
sys.path.insert(0,str(Q/'deps311'))
import numpy as np,h5py,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.patches import Rectangle
def read(p):return json.loads(p.read_text())
def zones(x,z):
 out=np.full(len(x),5)
 masks=[(x>=-.6)&(x<=3)&(abs(z)<=.6),(z>=1.6)&(z<=2.4),(x>3)&(x<=10)&(abs(z)<=.6),z<-3,z>3.2]
 for i,m in reversed(list(enumerate(masks))):out[m]=i
 return out
names=['Foil control','Free-surface control','Protected wake corridor','Remote water z < -3m','Remote air z >3.2m','Other middle / transition']
def stats(a):
 return {'p05':float(np.percentile(a,5)),'p50':float(np.median(a)),'p95':float(np.percentile(a,95)),'max':float(a.max())} if len(a) else None
def geometry(m):
 with h5py.File(Q/m/'mesh.CGNS','r') as f:
  g=f['Base/fluid'];xv=g['GridCoordinates/CoordinateX/ data'][...];zv=g['GridCoordinates/CoordinateZ/ data'][...]
  e=g['Q2D_span_source'];off=e['ElementStartOffset/ data'][...].astype(int);ix=e['ElementConnectivity/ data'][...].astype(int)-1
  first=off[:-1];last=off[1:]-1
  xx=xv[ix];zz=zv[ix];xn=np.roll(xx,-1);zn=np.roll(zz,-1);xn[last]=xx[first];zn[last]=zz[first]
  cross=xx*zn-xn*zz;twice=np.add.reduceat(cross,first);assert np.all(abs(twice)>1e-16)
  x=np.add.reduceat((xx+xn)*cross,first)/(3*twice);z=np.add.reduceat((zz+zn)*cross,first)/(3*twice)
  dx=np.maximum.reduceat(xx,first)-np.minimum.reduceat(xx,first);dz=np.maximum.reduceat(zz,first)-np.minimum.reduceat(zz,first)
  area=abs(twice)/2
  n=len(x);assert n==read(Q/m/'measurement.json')['metrics']['cell_count']
  region=zones(x,z);result=[]
  for i,name in enumerate(names):
   mask=region==i
   result.append({'region':name,'cells':int(mask.sum()),'cell_share_pct':float(100*mask.mean()),'area_m2':float(area[mask].sum()),'dx_extent_m':stats(dx[mask]),'dz_extent_m':stats(dz[mask]),'sqrt_area_m':stats(np.sqrt(area[mask]))})
  return {'cells':n,'total_source_area_m2':float(area.sum()),'regions':result},(x,z,dx,dz,region)
result={'created_at':datetime.datetime.now().astimezone().isoformat(),'geometry':{},'fields':{}}
for m in ['M06','M07','M08']:
 a,b=geometry(m);result['geometry'][m]=a
 if m=='M08':m08=b
snap=read(R/'selected_snapshots.json')
for m in ['M06','M07']:
 a=np.loadtxt(snap[m]['velocity'],delimiter=',',skiprows=1);x=a[:,6];z=a[:,8];vf=a[:,4];region=zones(x,z)
 disturbance=np.linalg.norm(a[:,:3]-[18,0,0],axis=1)/18*100
 regions=[]
 for i,name in enumerate(names):
  v=disturbance[region==i]
  regions.append({'region':name,'n':len(v),'velocity_disturbance_pct_U':stats(v),'fraction_cells_below_0p5pct_disturbance':float(100*np.mean(v<.5)),'fraction_cells_below_1pct_disturbance':float(100*np.mean(v<1))})
 interface=(vf>.01)&(vf<.99)
 result['fields'][m]={'time_s':snap[m]['time_s'],'definition':'100*norm(U_vector-[18,0,0])/18. Cell-count weighted; a smooth small disturbance is a coarsening clue, not an error bound.','regions':regions,'interface_centroid_z_range_m':[float(z[interface].min()),float(z[interface].max())],'interface_cell_count':int(interface.sum())}
 if m=='M07':plotdata=(x,z,disturbance)
base=read(Q/'M08/design.json')['base_m'];n=result['geometry']['M08']['cells']
remote=sum(a['cells'] for a in result['geometry']['M08']['regions'] if a['region'].startswith('Remote'))
fitrows=[a for a in read(R/'mesh_convergence.json')['settled_results'] if a['id'] in ['M04','M06','M07']]
ns=np.array([a['cells'] for a in fitrows]);ts=np.array([a['wall_s_per_step_median'] for a in fitrows]);slope,intercept=np.polyfit(ns,ts,1)
result['runtime_fit']={'cases':[{'mesh':a['id'],'cells':a['cells'],'median_s_per_step':a['wall_s_per_step_median']} for a in fitrows],'descriptive_intercept_s':float(intercept),'slope_s_per_cell':float(slope),'limits':'Three-case descriptive fit atdt1ms/20inner, shared-machine load and mesh shapes differ. Intercept is not a measured fixed solver overhead. Predictions require actual benchmarks.'}
result['outer_size_screen']=[]
for h in [.20,.25,.30]:
 ideal=n-remote*(1-(base/h)**2)
 pred=intercept+slope*ideal;old=intercept+slope*n
 result['outer_size_screen'].append({'outer_target_m':h,'protected_middle_z_m':[-3,3.2],'ideal_cells':int(round(ideal)),'ideal_cell_reduction_pct':float(100*(n-ideal)/n),'descriptive_step_s':float(pred),'descriptive_runtime_reduction_pct':float(100*(old-pred)/old),'limits':'Geometric2D area scaling of remote cells only; transition and remeshing may reduce savings. No new mesh/flow run.'})
fs=result['geometry']['M08']['regions'][1]
result['wave_surface_opportunity']={'current_M08_nominal_isotropic_target_m':read(Q/'M08/design.json')['free_surface_m'],'current_FS_cells':fs['cells'],'wave_start_dx_m':.20,'wave_start_dz_m':.025,'intended_cells_per_wavelength':[100,150],'cells_per_height':20,'limits':'Anisotropic surface band is a separate meshing strategy, not a scalar size increase. Current directed polygon source uses one isotropic volume size. Need compatible anisotropic source/structured partition and mesh/VOF propagation checks. Do not use isotropic0.20m atsurface.'}
result['proposed_next_design']={'id':'M09','status':'conditional_design_only_not_built_or_admitted','base_reference':'M08 if accepted and consistent withM07; otherwise revisit refinement need first','change':'Outer base0.142857m to0.25m; add middle-domain protection atold0.142857m acrossx[-11.9,30.94],z[-3,3.2]. Existing finer foil andFScontrols remain.','preserved':{'foil_target_m':.004/1.4,'foil_min_m':.0004/1.4,'global_min_m':.0005/1.4,'near_foil_m':.0125/1.4,'free_surface_m':.04/1.4,'first_layer_m':3e-6/(1.4**2),'layers':48,'total_prism_m':.01546,'domain':'unchanged','surface_growth':1.2},'admission':'Reaudit source geometry,exactspan,layercoverage,zero invalidcells, transitions; then same force screen and1%comparison. Final time/order settings must match.'}
result['protected_features']=['Foil contour, LE/TE surface resolution and prism wall settings','Near-foil refinement box and wake corridor','Existing free-surface band and interface transport','Physical domain,boundaries,depth and submergence','One spanwise cell; no further spanwise coarsening is possible']
(R/'mesh_optimization_evidence.json').write_text(json.dumps(result,indent=2))
plt.rcParams.update({'font.size':10,'font.family':'DejaVu Sans','svg.fonttype':'none'})
fig,axs=plt.subplots(1,2,figsize=(13.5,5.5),layout='constrained')
bins=[np.arange(-12,31.5,.5),np.arange(-22,8.5,.5)]
x,z,dx,dz,reg=m08
count,xe,ze=np.histogram2d(x,z,bins=bins);total,_,_=np.histogram2d(x,z,bins=bins,weights=dx)
mean=np.divide(total,count,out=np.full_like(total,np.nan),where=count>0)
im=axs[0].pcolormesh(xe,ze,mean.T,cmap='viridis',norm=LogNorm(vmin=.003,vmax=.3),rasterized=True)
fig.colorbar(im,ax=axs[0],label='Mean projected cell extent in x [m]')
axs[0].set_title('M08: where the mesh is fine')
x,z,du=plotdata;count,xe,ze=np.histogram2d(x,z,bins=bins);total,_,_=np.histogram2d(x,z,bins=bins,weights=du)
mean=np.divide(total,count,out=np.full_like(total,np.nan),where=count>0)
im=axs[1].pcolormesh(xe,ze,np.maximum(mean.T,1e-5),cmap='magma',norm=LogNorm(vmin=1e-3,vmax=10),rasterized=True)
fig.colorbar(im,ax=axs[1],label='Mean velocity disturbance [% of U]')
axs[1].set_title('M07 accepted field: flow disturbance')
for ax in axs:
 ax.set(xlabel='x [m]',ylabel='z [m]',xlim=(-11.9,30.94),ylim=(-22,8),aspect='equal')
 ax.axhline(-3,color='#128a62',lw=1.4,ls='--');ax.axhline(3.2,color='#128a62',lw=1.4,ls='--')
 ax.add_patch(Rectangle((-.6,-.6),3.6,1.2,fill=False,ec='#55b8e7',lw=1.2))
 ax.add_patch(Rectangle((-11.9,1.6),42.84,.8,fill=False,ec='#55b8e7',lw=1.2))
axs[0].text(-10,-19,'Coarsening candidate',color='white',fontsize=10)
axs[0].text(-10,5.8,'Coarsening candidate',color='white',fontsize=10)
fig.savefig(R/'mesh_optimization_regions.png',dpi=160);fig.savefig(R/'mesh_optimization_regions.svg');plt.close(fig)
print(json.dumps({'M08_cells':n,'remote_cells':remote,'remote_share_pct':100*remote/n,'outer_size_screen':result['outer_size_screen'],'M08_FS_geometry':fs,'field_remote':{m:[a for a in f['regions'] if a['region'].startswith('Remote')] for m,f in result['fields'].items()},'fit':result['runtime_fit']},indent=2))
