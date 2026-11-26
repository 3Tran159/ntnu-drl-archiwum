"""Native signed omega_y from an audited saved field; CPU-only, no CFD actions."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
from pathlib import Path
import csv,json,math,time,datetime
import plot_wave_side_view as base
import numpy as np,matplotlib.pyplot as plt,matplotlib.tri as mtri
from matplotlib.path import Path as MPath
R=base.R;AUDIT=base.BASE/'W01a_inlet_ramp_api_audit_r1';SOURCE=AUDIT/'physical_fields.csv'
OUT=R/'wave_vorticity_frames';OUT.mkdir(exist_ok=True)
def main():
 identity=base.read_json(AUDIT/'source_identity.json');audit=base.read_json(AUDIT/'controller_result.json')
 assert audit.get('status')=='zero_step_audit_complete' and audit.get('source_unchanged') is True
 assert audit.get('flow_steps')==0 and audit.get('initialized_or_cleared') is False and audit.get('physical_field_csv_bitwise_equal') is True
 assert identity.get('computed_checkpoint') is True and identity.get('source_sha256')==identity.get('copy_sha256')==audit.get('source_sha256')
 native=audit.get('native_vorticity',{})
 assert native.get('found') is True and native.get('component_index')==1 and native.get('function_name')=='VorticityVector'
 digest=base.sha(SOURCE);assert digest==audit['physical_field_csv_sha256_before']==audit['physical_field_csv_sha256_after']
 source_case=identity['source_case'];field_time=float(audit['time_s'])
 current=base.read_json(R/'wave_vorticity_current.json')
 if current.get('renderer_version')==2 and current.get('source_sha256')==digest and Path(current.get('image_path','missing')).is_file():
  print(json.dumps({'status':'cached','field_time_s':field_time}));return
 pts=[];count=0;lo=math.inf;hi=-math.inf
 with SOURCE.open(encoding='utf-8-sig',newline='') as f:
  reader=csv.DictReader(f)
  assert {'X (m)','Y (m)','Z (m)','Vorticity[j] (/s)'}.issubset(reader.fieldnames)
  for row in reader:
   x,y,z,w=map(float,(row['X (m)'],row['Y (m)'],row['Z (m)'],row['Vorticity[j] (/s)']))
   assert all(math.isfinite(v) for v in (x,y,z,w)) and abs(y-.02)<1e-7
   count+=1;lo=min(lo,w);hi=max(hi,w)
   if -2.3<=x<=6.3 and -1.3<=z<=1.8:pts.append((x,z,w))
 assert count==317277 and abs(lo-native['omega_y_min_per_s'])<1e-6 and abs(hi-native['omega_y_max_per_s'])<1e-6
 data=np.array(pts);_,ii=np.unique(data[:,:2],axis=0,return_index=True);data=data[np.sort(ii)]
 x,z,omega=data.T;poly=base.foil_geometry();body=MPath(np.vstack([poly,poly[0]]),closed=True)
 tri=mtri.Triangulation(x,z);vertices=data[:,:2][tri.triangles]
 lower=vertices.min(axis=1);upper=vertices.max(axis=1);plow=poly.min(axis=0);phigh=poly.max(axis=0)
 possible=np.all(upper>=plow,axis=1)&np.all(lower<=phigh,axis=1);mask=np.zeros(len(vertices),dtype=bool)
 for i in np.flatnonzero(possible):
  triangle=MPath(np.vstack([vertices[i],vertices[i,0]]),closed=True)
  mask[i]=triangle.intersects_path(body,filled=True)
 tri.set_mask(mask);interpolate=mtri.LinearTriInterpolator(tri,omega)
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none'})
 fig,axes=plt.subplots(2,1,figsize=(13.5,8.5));fig.subplots_adjust(left=.075,right=.89,top=.86,bottom=.15,hspace=.50)
 views=[{'name':'Foil and near wake','x':[-2.,6.],'z':[-1.,1.5],'range':1000.},
        {'name':'Wake focus','x':[float(phigh[0])+.015,6.],'z':[-.6,.6],'range':200.}]
 stats=[]
 for ax,v in zip(axes,views):
  gx=np.linspace(*v['x'],1051);gz=np.linspace(*v['z'],321);xx,zz=np.meshgrid(gx,gz)
  a=interpolate(xx,zz);a=np.ma.masked_where(body.contains_points(np.column_stack([xx.ravel(),zz.ravel()])).reshape(xx.shape)|np.ma.getmaskarray(a),a)
  image=ax.pcolormesh(xx,zz,a,cmap='RdBu_r',vmin=-v['range'],vmax=v['range'],shading='auto',rasterized=True)
  ax.fill(poly[:,0],poly[:,1],color='#182f40',zorder=5)
  ax.set(xlim=v['x'],ylim=v['z'],xlabel='x [m]',ylabel='z [m]');ax.set_aspect('equal',adjustable='box');ax.spines[['top','right']].set_visible(False)
  selected=(x>=v['x'][0])&(x<=v['x'][1])&(z>=v['z'][0])&(z<=v['z'][1]);clipped=100*np.mean(np.abs(omega[selected])>v['range'])
  ax.set_title(v['name']+' · colour range ±'+format(v['range'],'.0f')+' /s · '+format(clipped,'.3f')+'% of saved cells clipped',loc='left',fontsize=11)
  pos=ax.get_position();cax=fig.add_axes([.915,pos.y0,.015,pos.height]);fig.colorbar(image,cax=cax,label='Native ωy [1/s]',extend='both')
  stats.append({**v,'saved_cells_in_view':int(selected.sum()),'saved_cell_clipping_pct':float(clipped),'display_min_per_s':-v['range'],'display_max_per_s':v['range']})
 fig.suptitle('W01a · signed spanwise vorticity',x=.075,y=.97,ha='left',fontsize=18,fontweight='bold',color='#17384c')
 fig.text(.075,.915,'Actual calm checkpoint at t = '+format(field_time,'.3f')+' s · native STAR Vorticity[j] · no inlet wave in this saved state',fontsize=11,color='#536c7c')
 fig.text(.075,.075,'Red / blue show opposite rotation signs. Colour limits deliberately expose the wake; saturated colours are not maxima.',fontsize=10,color='#536c7c')
 fig.text(.075,.042,'Cell-centre interpolation. Every triangle intersecting the solid foil is masked; blank near-wall regions are not zero vorticity.',fontsize=10,color='#536c7c')
 token=source_case+'_native_omega_y_t'+format(field_time,'.3f').replace('.','p');png=OUT/(token+'.png');svg=OUT/(token+'.svg')
 fig.savefig(png,dpi=160,facecolor='white');fig.savefig(svg,facecolor='white');plt.close(fig)
 prov={'generated_at':datetime.datetime.now().astimezone().isoformat(),'case':source_case,'source_case':source_case,'field_time_s':field_time,'source_file':str(SOURCE),'source_sha256':digest,'source_checkpoint':identity['source'],'source_checkpoint_sha256':identity['source_sha256'],'audit_result':str(AUDIT/'controller_result.json'),'zero_flow_steps':True,'physical_fields_unchanged':True,'native_function':native,'source_cells':count,'source_range_per_s':[lo,hi],'geometry_file':str(base.MESH),'geometry_sha256':base.sha(base.MESH),'foil_edges':len(poly),'views':stats,'method':'Delaunay interpolation of native saved Vorticity[j] (/s). Exact closed polygon-path intersection masks every Delaunay triangle touching/intersecting the foil; raster points inside the solid also masked. No velocity-gradient reconstruction.','masked_triangles':int(mask.sum()),'triangle_count':len(mask),'limitations':['Saved calm checkpoint; not current solver time.','Clipping fraction is by saved cell centres in each displayed rectangle, not physical area.','White masked near-wall gaps do not mean zero vorticity.','No wave/force accuracy acceptance.'],'solver_actions':0}
 provpath=OUT/(token+'_provenance.json');base.write_json(provpath,prov)
 caption='Native signed ωy from the actual W01a calm checkpoint at t = '+format(field_time,'.3f')+' s. Opposite signs use blue and red; fixed colour limits and cell clipping are stated on each view. This is saved diagnostic evidence, not the current solver time or wave acceptance.'
 base.write_json(R/'wave_vorticity_current.json',{'status':'ready','renderer_version':2,'case':source_case,'source_case':source_case,'field_time_s':field_time,'time_s':field_time,'caption':caption,'image_path':str(png),'image_png':str(png),'image_svg':str(svg),'provenance_path':str(provpath),'source_sha256':digest,'accepted':False,'live':False,'views':stats})
 print(json.dumps({'status':'ready','field_time_s':field_time,'image':str(png),'masked_triangles':int(mask.sum()),'views':stats}))
if __name__=='__main__':main()
