"""Read completed STAR wave-tank builds without touching the simulations."""
import csv,json,re
from pathlib import Path
root=Path(r'F:\ntnu\wave_depth_20261029')
rows=[]
for case in json.loads((root/'cases.json').read_text(encoding='utf-8')):
 name=case['id'];d=root/name
 sim=d/'built.sim'; success=(d/'SUCCESS.txt').exists();report=d/'mesh_report.txt'
 obj=dict(case=name,lambda_m=case['lambda_m'],depth_m=case['depth_m'],domain_lambda=case['domain_lambda'],dt_s=case['dt_s'],
 status='MESHD_AND_SAVED' if sim.is_file() and success else 'MISSING_OR_INCOMPLETE',
 sim_megabytes=round(sim.stat().st_size/1e6,3) if sim.exists() else '',
 cells='',mesh_issues='')
 if (d/'verified_setup.txt').is_file():
  m=re.search(r'(?m)^cells=(\d+)',(d/'verified_setup.txt').read_text())
  if m:obj['cells']=int(m.group(1))
 if report.exists():
  txt=report.read_text(encoding='utf-8',errors='replace')
  obj['mesh_issues']=";".join(k for k in ('NegativeVolumeCells','UnclosedCells','DegeneratedFeCells') if k not in txt)
 rows.append(obj)
with (root/'status.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
print('RESULT',sum(r['status']=='MESHD_AND_SAVED' for r in rows),'of',len(rows),'built')
