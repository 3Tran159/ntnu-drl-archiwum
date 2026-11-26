from pathlib import Path
import csv,json,datetime
h=Path(__file__).resolve().parents[1];c=h/'cases/SP_C_split0_overset'
rows=[]
for p in sorted(c.rglob('initialization_status.json')):
 a=json.loads(p.read_text(encoding='utf8'));hist=p.parent/'steady_iterations.csv'
 if not hist.exists():continue
 data=list(csv.DictReader(hist.open(encoding='utf8')));last=data[-30:];values=lambda k:[float(x[k]) for x in last]
 row=dict(folder=str(p.parent),status=a['status'],additional_iterations=a['iterations'],final_CL=float(data[-1]['CL_hydro']),final_CD=float(data[-1]['CD']),max_relative_mass_last_300=float(max(values('mass_imbalance_relative'))),pressure_min_last_300_Pa=min(values('p_absolute_min_Pa')),training_approved=False)
 co=p.parent/'overset_conservation.json'
 if co.exists():row['conservation']=json.loads(co.read_text())
 row['interpretation']='Numerical initialization only, no accepted hydrodynamic result. Fields retained for separately gated URANS test.'
 rows.append(row)
out=h/'validation/SP_C_initialization_diagnostics.json';out.write_text(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),attempts=rows),indent=2),encoding='utf8')
print(json.dumps(rows,indent=2))
