from pathlib import Path
import sys,json,datetime
import numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h.parent/'flap_poc_2606_20261102/deps'))
import shapely
run=Path(sys.argv[1]).resolve();assert run.is_relative_to(h/'cases/SP_C_split0_overset')
status=json.loads((run/'status.json').read_text(encoding='utf8'));assert status['status']=='mesh_connectivity_prepared' and status['solver_steps']==0
metrics=json.loads((run/'mapped_initial_metrics.json').read_text(encoding='utf8'));assert metrics['native_iteration']==0 and metrics['physical_time_s']==0 and metrics['source_iteration']==1850
src=h/'cases/SP_C_split0_overset/c0_flux_recovery_20261103_012140'
mesh=h/'cases/SP_C_split0_overset/c0_tight_cage_v2_20261103_025110'
polys={name:shapely.Polygon(np.loadtxt(run/(name+'_native_polygon.csv'),delimiter=',',skiprows=1)) for name in ['main','flap']}
o=dict(at=datetime.datetime.now().astimezone().isoformat(),run=str(run),mapped_metrics=metrics,regions={},scientific_approved=False)
for name in ['Background','FlapOverset']:
 before=pd.read_csv(mesh/(name+'_mesh_full_plane.csv'));after=pd.read_csv(run/(name+'_fresh_initialized_full_plane.csv'))
 tree=shapely.STRtree(shapely.points(before['X (m)'],before['Z (m)']));idx=tree.nearest(shapely.points(after['X (m)'],after['Z (m)']));b=before.iloc[idx].reset_index(drop=True)
 err=np.linalg.norm(after[['X (m)','Y (m)','Z (m)']].to_numpy()-b[['X (m)','Y (m)','Z (m)']].to_numpy(),axis=1)
 identity=len(before)==len(after)==len(np.unique(idx)) and err.max()<1e-10 and np.max(np.abs(after['Volume (m^3)']/b['Volume (m^3)']-1))<1e-6
 mask_changes=int((after['Overset Cell Status']!=b['Overset Cell Status']).sum())
 d=pd.read_csv(run/(name+'_fresh_initialized_volume.csv'));d=d[d['Overset Cell Status']==0]
 speed=np.linalg.norm(d[['Velocity[i] (m/s)','Velocity[j] (m/s)','Velocity[k] (m/s)']].to_numpy(),axis=1)
 pts=shapely.points(d['X (m)'],d['Z (m)'])
 regions=dict(mesh_identity=bool(identity),mask_changes=mask_changes,active_cells=len(d),solid_intrusions={k:int(shapely.contains(p,pts).sum()) for k,p in polys.items()},min_pressure_absolute_Pa=float(d['Absolute Pressure (Pa)'].min()),speed_max_m_s=float(speed.max()),k_floor_cells=int((d['Turbulent Kinetic Energy (J/kg)']<=1.0001e-10).sum()),omega_floor_cells=int((d['Specific Dissipation Rate (/s)']<=1.0001e-10).sum()),max_viscosity_ratio=float(d['Turbulent Viscosity Ratio'].max()))
 if name=='Background':
  old=pd.read_csv(src/(name+'_final_volume.csv'));old=old[old['Overset Cell Status']==0].reset_index(drop=True)
  tree=shapely.STRtree(shapely.points(old['X (m)'],old['Z (m)']));j=tree.nearest(pts);match=old.iloc[j].reset_index(drop=True);new=d.reset_index(drop=True)
  dist=np.linalg.norm(new[['X (m)','Y (m)','Z (m)']].to_numpy()-match[['X (m)','Y (m)','Z (m)']].to_numpy(),axis=1);same=dist<1e-10
  regions['previously_active_same_centers']=int(same.sum())
  regions['same_center_mapping_differences']={col:dict(max_abs=float(np.max(np.abs(new.loc[same,col].to_numpy()-match.loc[same,col].to_numpy()))),median_abs=float(np.median(np.abs(new.loc[same,col].to_numpy()-match.loc[same,col].to_numpy())))) for col in ['Pressure (Pa)','Velocity[i] (m/s)','Velocity[k] (m/s)','Turbulent Kinetic Energy (J/kg)','Specific Dissipation Rate (/s)']}
 o['regions'][name]=regions
o['technical_mapping_review_pass']=all(r['mesh_identity'] and r['mask_changes']==0 and sum(r['solid_intrusions'].values())==0 and r['min_pressure_absolute_Pa']>12339.214766776897 and r['speed_max_m_s']<25 and r['k_floor_cells']==r['omega_floor_cells']==0 and r['max_viscosity_ratio']<99999 for r in o['regions'].values()) and metrics['mass_imbalance_relative']<1e-4
(run/'work_mapping_review.json').write_text(json.dumps(o,indent=2),encoding='utf8')
print(json.dumps(o,indent=2))
