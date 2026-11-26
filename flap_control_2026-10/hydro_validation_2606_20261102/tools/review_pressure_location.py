from pathlib import Path
import sys,json,datetime,numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1];run=Path(sys.argv[1]);label=sys.argv[2]
assert (run/('residual_normalization_'+label+'.txt')).exists()
frames=[]
for region in ['Background','FlapOverset']:
 f=pd.read_csv(run/(region+'_'+label+'_volume.csv'));f=f[f['Overset Cell Status']==0].copy();f['region']=region;frames.append(f)
f=pd.concat(frames,ignore_index=True);f['speed_m_s']=np.sqrt(sum(f['Velocity['+k+'] (m/s)']**2 for k in 'ijk'))
cols=['region','X (m)','Y (m)','Z (m)','Absolute Pressure (Pa)','Pressure (Pa)','speed_m_s','Volume (m^3)','Cell Quality','Wall Distance (m)']
masks={'all_active':np.ones(len(f),dtype=bool),'near_foil':f['X (m)'].between(-.15,1.5)&f['Z (m)'].between(-.3,.35),'top_boundary_band':f['Z (m)']>7,'far_aft_top':(f['Z (m)']>7)&(f['X (m)']>20)}
o=dict(at=datetime.datetime.now().astimezone().isoformat(),label=label,run=str(run),scientific_approved=False,notes='Snapshot localization of active-cell pressure minima. Does not localize earlier unsaved pressure dips; no inference that all history minima share this position.',zones={})
for name,mask in masks.items():
 z=f[mask];o['zones'][name]=dict(cells=len(z),pabs_min_Pa=float(z['Absolute Pressure (Pa)'].min()),speed_max_m_s=float(z.speed_m_s.max()),lowest5=z.nsmallest(5,'Absolute Pressure (Pa)')[cols].to_dict('records'))
hist=pd.read_csv(run/'history.csv')
o['history_summary']=dict(samples=len(hist),min_pabs_Pa=float(hist.p_absolute_min_Pa.min()),max_mass_imbalance=float(hist.mass_imbalance_relative.max()),correlation_pabs_mass=float(hist.p_absolute_min_Pa.corr(hist.mass_imbalance_relative)))
(run/('pressure_location_'+label+'.json')).write_text(json.dumps(o,indent=2),encoding='utf8')
brief=dict(at=o['at'],label=label,zones={k:dict(min_pabs_Pa=v['pabs_min_Pa'],speed_max_m_s=v['speed_max_m_s'],lowest=v['lowest5'][0]) for k,v in o['zones'].items()},history=o['history_summary'])
print(json.dumps(brief,indent=2))
