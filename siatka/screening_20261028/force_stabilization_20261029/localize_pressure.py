import sys,csv,json
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
sys.path.insert(0,str(Q/'deps311'))
snapshots=json.loads((R/'selected_snapshots.json').read_text())
colours={'M03':'#187b73','M02':'#bf5a28','M04':'#5267ad','M05':'#6d7136','M06':'#963c77','M07':'#2d6590','M08':'#705841','M09':'#408f61','M10':'#805f9c'}
snapshot_label=' | '.join(m+' '+v['status']+' t='+format(v['time_s'],'.3f')+' s' for m,v in snapshots.items())
import numpy as np,h5py,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
summaries={}
for mesh in snapshots:
 color=colours[mesh]
 with Path(snapshots[mesh]['wall']).open() as f:rs=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]
 tablexyz=np.array([[r[a+' (m)'] for a in 'XYZ'] for r in rs]);pv=np.array([r['Pressure (Pa)'] for r in rs])
 with h5py.File(Q/mesh/'mesh.CGNS','r') as f:
  z=f['Base/fluid'];xyz=np.column_stack([z['GridCoordinates/Coordinate'+a+'/ data'][...] for a in 'XYZ'])
  faces={};wallids=[]
  for name,g in z.items():
   if isinstance(g,h5py.Group) and 'ElementConnectivity' in g and int(g[' data'][0])==22:
    off=g['ElementStartOffset/ data'][...];con=g['ElementConnectivity/ data'][...]-1;start=int(g['ElementRange/ data'][0])
    for i in range(len(off)-1):
     faces[start+i]=con[off[i]:off[i+1]]
     if name=='HF_012_wall':wallids.append(start+i)
  cg=z['fluid'];off=cg['ElementStartOffset/ data'][...];con=cg['ElementConnectivity/ data'][...]
  wallset=set(wallids);adj={}
  for i in range(len(off)-1):
   ff=np.abs(con[off[i]:off[i+1]]);ww=wallset.intersection(ff)
   if ww:
    centroid=xyz[np.unique(np.concatenate([faces[k] for k in ff]))].mean(axis=0)
    for w in ww:adj[w]=centroid
  records=[]
  for w in wallids:
   verts=xyz[faces[w]];center=verts.mean(axis=0)
   av=sum((np.cross(verts[i]-verts[0],verts[i+1]-verts[0])*.5 for i in range(1,len(verts)-1)),np.zeros(3))
   if np.dot(av,center-adj[w])<0:av=-av
   distances=np.linalg.norm(tablexyz-center,axis=1);j=int(np.argmin(distances));pressure=pv[j]
   records.append({'x':float(center[0]),'z':float(center[2]),'match_distance_m':float(distances[j]),'pressure_Pa':float(pressure),'area_x_m2':float(av[0]),'area_z_m2':float(av[2]),'pressure_drag_N':float(pressure*av[0]),'pressure_lift_N':float(pressure*av[2]),'edge_length_m':float(np.linalg.norm(av)/.02),'Cp_hydro_subtracted':float((pressure-1000*9.81*(2-center[2]))/(.5*1000*18**2))})
 exact=snapshots[mesh]['pressure_drag_N']
 zones={}
 for label,lo,hi in [('LE_0_1pct',-1,.01),('1_5pct',.01,.05),('5_20pct',.05,.2),('20_80pct',.2,.8),('TE_80_100pct',.8,2)]:
  subset=[r for r in records if lo<=r['x']/1.19<hi]
  zones[label]={'faces':len(subset),'pressure_drag_N':sum(r['pressure_drag_N'] for r in subset),'max_edge_mm':max([r['edge_length_m']*1000 for r in subset],default=None)}
 total=sum(r['pressure_drag_N'] for r in records)
 summaries[mesh]={'time_s':snapshots[mesh]['time_s'],'status':snapshots[mesh]['status'],'reconstructed_drag_N':total,'STAR_report_pressure_drag_N':exact,'relative_reconstruction_error_pct':100*(total-exact)/exact,'max_face_centroid_match_error_m':max(r['match_distance_m'] for r in records),'force_bins':zones,'method':'Pressure at nearest exact CGNS boundary-face centroid times face area vector oriented outward from fluid cell. Face matching error and STAR total reconstruction validate localization.'}
 with (R/(mesh+'_pressure_face_contributions.csv')).open('w',newline='') as f:
  wr=csv.DictWriter(f,fieldnames=records[0].keys());wr.writeheader();wr.writerows(records)
 for upper in [True,False]:
  a=sorted([r for r in records if (r['area_z_m2']<0)==upper],key=lambda r:r['x'])
  for ax in axes[0]:
   ax.plot([r['x']/1.19 for r in a],[r['Cp_hydro_subtracted'] for r in a],color=color,ls='-' if upper else '--',label=mesh+(' upper' if upper else ' lower'))
 a=sorted(records,key=lambda r:r['x'])
 axes[1,0].plot([r['x']/1.19 for r in a],np.cumsum([r['pressure_drag_N'] for r in a]),label=mesh,color=color)
 axes[1,1].scatter([r['x']/1.19 for r in a],[r['edge_length_m']*1000 for r in a],s=8,color=color,label=mesh)
for ax in axes.flat:ax.grid(alpha=.2);ax.legend(fontsize=8);ax.set_xlabel('x/c')
for ax in axes[0]:ax.set_ylabel('Cp (nominal hydrostatic pressure subtracted)');ax.invert_yaxis()
axes[0,0].set_title('Surface pressure coefficient')
axes[0,1].set(xlim=(-.002,.06),title='Leading-edge detail')
axes[1,0].set(ylabel='Cumulative pressure drag [N]',title='Signed integral along chord')
axes[1,1].set(xlim=(-.002,.06),ylabel='Boundary edge length [mm]',title='Leading-edge surface resolution')
fig.suptitle('Pressure drag and surface pressure\n'+snapshot_label)
fig.savefig(R/'pressure_localization.png',dpi=160);fig.savefig(R/'pressure_localization.svg')
(R/'pressure_localization.json').write_text(json.dumps(summaries,indent=2))
print(json.dumps(summaries))
