from pathlib import Path
import sys,json,datetime,numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1];run=Path(sys.argv[1]);label=sys.argv[2]
specs=[('B without Overset',h/'audit/comparison_SP_B_20261102_222923/Background_volume.csv'),('C pressureURF0.2',h/'cases/SP_C_split0_overset/c0_urans_continue_inner40_20261103_041433/Background_final_volume.csv'),('C pressureURF0.1',run/('Background_'+label+'_volume.csv'))]
o=dict(at=datetime.datetime.now().astimezone().isoformat(),scientific_approved=False,selection='Background active cells with10<x<43m and7<z<8m; cells adjacent to remote top pressure boundary, no foil or Overset region.',cases={})
for name,p in specs:
 f=pd.read_csv(p)
 if 'Overset Cell Status' in f:f=f[f['Overset Cell Status']==0]
 f=f[f['X (m)'].between(10,43)&f['Z (m)'].between(7,8)].copy()
 vx=f['Velocity[i] (m/s)'];vz=f['Velocity[k] (m/s)'];vol=f['Volume (m^3)']
 cols=['X (m)','Z (m)','Pressure (Pa)','Absolute Pressure (Pa)','Velocity[i] (m/s)','Velocity[k] (m/s)','Cell Quality']
 rec=dict(cells=len(f),volume_m3=float(vol.sum()),vx_min=float(vx.min()),vx_max=float(vx.max()),vx_volume_mean=float(np.average(vx,weights=vol)),vz_min=float(vz.min()),vz_max=float(vz.max()),vz_volume_rms=float(np.sqrt(np.average(vz**2,weights=vol))),velocity_deviation_from_uniform18_volume_rms=float(np.sqrt(np.average((vx-18)**2+vz**2,weights=vol))),min_pressure=f.nsmallest(1,'Absolute Pressure (Pa)')[cols].to_dict('records')[0],largest_abs_vz=f.loc[vz.abs().nlargest(3).index,cols].to_dict('records'))
 o['cases'][name]=rec
(run/('far_top_vectors_'+label+'.json')).write_text(json.dumps(o,indent=2),encoding='utf8')
print(json.dumps(o,indent=2))
