from pathlib import Path
import sys,json,datetime,re
import numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1]
run=Path(sys.argv[1]).resolve();assert run.is_relative_to(h/'cases/SP_C_split0_overset')
d=pd.read_csv(run/'steady_iterations.csv')
o=dict(at=datetime.datetime.now().astimezone().isoformat(),run=str(run),last_iteration=int(d.iteration.iloc[-1]),physical_time_s=0,phase='steady_initialization',scientific_approved=False,training_approved=False)
o['last']=d.iloc[-1].to_dict()
o['windows']=[]
for stop in range(10,len(d)+1,10):
 a=d.iloc[stop-10:stop]
 o['windows'].append(dict(iteration=int(a.iteration.iloc[-1]),CL=float(a.CL_hydro.mean()),CD=float(a.CD.mean()),Mh=float(a.Mh_Nm.mean()),pressure_min=float(a.p_absolute_min_Pa.min()),mass_max=float(a.mass_imbalance_relative.max()),omega_max=int(a.omega_floor_cells.max()),k_max=int(a.k_floor_cells.max()),viscosity_ratio_max=float(a.max_turbulent_viscosity_ratio.max())))
if len(o['windows'])>=2:
 a,b=o['windows'][-2:];o['last_window_changes_percent']={k:100*(b[k]/a[k]-1) for k in ['CL','CD','Mh']}
src=(h/'tools/review_c0_diagnostic.py').read_text(encoding='utf8')
exec(src[src.index("o['field_exports']={}"):src.index("(run/'work_review.json')")])
(run/'work_review.json').write_text(json.dumps(o,indent=2),encoding='utf8')
(h/'validation'/('review_'+run.name+'.json')).write_text(json.dumps(o,indent=2),encoding='utf8')
brief={k:v for k,v in o.items() if k not in ['windows','field_exports']}
brief['last_windows']=o['windows'][-3:]
brief['fields']=o['field_exports']
print(json.dumps(brief,indent=2))
