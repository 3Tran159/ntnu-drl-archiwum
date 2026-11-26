from pathlib import Path
import json,hashlib,datetime
import pandas as pd,numpy as np
h=Path(__file__).resolve().parents[1]
src=h/'cases/SP_C_split0_overset/c0_flux_recovery_20261103_012140'
cp=src/'steady_checkpoint.sim';digest=hashlib.file_digest(cp.open('rb'),'sha256').hexdigest()
assert digest=='932e6c274be656cdfab3c5d19c78c5f5d6f1fda8d3226b9633e950c3b637ee18'
cols={'X (m)':'X','Y (m)':'Y','Z (m)':'Z','Pressure (Pa)':'pressure','Velocity[i] (m/s)':'ux','Velocity[j] (m/s)':'uy','Velocity[k] (m/s)':'uz','Turbulent Kinetic Energy (J/kg)':'k','Specific Dissipation Rate (/s)':'omega'}
pieces=[];inputs={}
for reg in ['Background','FlapOverset']:
 p=src/(reg+'_final_volume.csv');inputs[reg]=dict(path=str(p),sha256=hashlib.file_digest(p.open('rb'),'sha256').hexdigest())
 d=pd.read_csv(p);d=d[d['Overset Cell Status']==0]
 assert (d['Overset Error Status']==0).all()
 assert d['Absolute Pressure (Pa)'].min()>12339.214766776897
 assert d['Turbulent Kinetic Energy (J/kg)'].min()>1.0001e-10 and d['Specific Dissipation Rate (/s)'].min()>1.0001e-10
 pieces.append(d[list(cols)].rename(columns=cols))
a=pd.concat(pieces,ignore_index=True)
assert np.isfinite(a.to_numpy()).all()
duplicates=int(a.duplicated(['X','Y','Z']).sum());assert duplicates==0,'Review duplicate donors before interpolation'
speed=np.linalg.norm(a[['ux','uy','uz']].to_numpy(),axis=1);assert speed.max()<25
out=h/'initialization/c0_tight_from_flux1850';out.mkdir(parents=True,exist_ok=False)
table=out/'warm_fields.csv';a.to_csv(table,index=False,float_format='%.17g')
meta=dict(at=datetime.datetime.now().astimezone().isoformat(),method='Supported STAR restart using XYZ table of initial dependent variables. Only active source volume cells; no pressure/velocity clipping, no averaging, no coordinate changes.',source_checkpoint=str(cp),source_checkpoint_sha256=digest,source_native_iteration=1850,source_physical_time_s=0,source_scientific_approved=False,source_purpose='Numerically healthy first-order recovery field, not validated hydrodynamic data',inputs=inputs,rows=len(a),duplicate_positions=duplicates,columns_units={'X':'m','Y':'m','Z':'m','pressure':'Pa piezometric','ux':'m/s','uy':'m/s','uz':'m/s','k':'J/kg','omega':'1/s'},source_max_speed_m_s=float(speed.max()),source_pressure_range_Pa=[float(a.pressure.min()),float(a.pressure.max())],source_k_range=[float(a.k.min()),float(a.k.max())],source_omega_range=[float(a.omega.min()),float(a.omega.max())],table=str(table),table_sha256=hashlib.file_digest(table.open('rb'),'sha256').hexdigest(),table_bytes=table.stat().st_size,native_mapping_run=False,scientific_approved=False)
(out/'mapping_source.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
print(json.dumps(meta,indent=2))
