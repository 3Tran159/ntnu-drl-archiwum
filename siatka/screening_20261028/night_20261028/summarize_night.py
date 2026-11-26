"""Summarize recorded startup runs; never infer force convergence."""
import csv,json,math
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(r'F:\ntnu\mesh_screening_20261028\night_20261028')
def read(path,default=None):
 try:return json.loads(path.read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return default
def write(path,text):
 temp=path.with_suffix(path.suffix+'.new');temp.write_text(text,encoding='utf-8');temp.replace(path)
def summarize(manifest):
 runs=[]
 for jobpath in manifest['jobs']:
  job=read(Path(jobpath),{});out=Path(job.get('output','missing'))
  history=[]
  if (out/'history.csv').exists():
   with (out/'history.csv').open() as stream:
    for row in csv.DictReader(stream):
     try:
      values={k:float(v) for k,v in row.items()}
      if all(math.isfinite(v) for v in values.values()):history.append(values)
     except (ValueError,TypeError):continue
  result=read(out/'controller_result.json',{})
  run={'case':out.name,'status':result.get('status','pending or running'),'completed_outer_calls':len(history),'minimum_free_ram_gib':result.get('min_free_gib'),'output':str(out),'last':history[-1] if history else None,'_history':history}
  if history:run['mean_wall_seconds_per_outer_call']=history[-1]['wall_seconds']/len(history)
  runs.append(run)
 available=[r for r in runs if r['_history']]
 common=min(r['last']['physical_time_s'] for r in available) if available else None
 for r in available:
  matching=[h for h in r['_history'] if h['physical_time_s']<=common+1e-12]
  r['at_common_time']=matching[-1] if matching else None
 for r in runs:r.pop('_history')
 data={'updated_at':datetime.now(timezone.utc).isoformat(),'purpose':'startup stability/resource screening, not converged forces','expected_cases':len(runs),'cases_with_progress':len(available),'common_physical_time_s':common,'all_cases_have_progress':len(available)==len(runs),'runs':runs}
 write(ROOT/'nightly_summary.json',json.dumps(data,indent=2)+'\n')
 lines=['# Nocne próby CFD — automatyczne podsumowanie','', 'Aktualizacja: '+data['updated_at'],'', 'Cel: rozruch, stabilność i koszt obliczeń. Wyniki nie potwierdzają zbieżności sił ani niezależności od siatki.','',f"Przypadki z ukończonym krokiem: {len(available)}/{len(runs)}. Wspólny czas fizyczny dostępnych prób: {common} s.",'', '| Przypadek | Status | Kroki | Czas fizyczny [s] | Min. wolny RAM [GiB] | Śr. czas kroku [s] |','|---|---|---:|---:|---:|---:|']
 for r in runs:lines.append('| '+ ' | '.join(str(v) for v in [r['case'],r['status'],r['completed_outer_calls'],r['last']['physical_time_s'] if r['last'] else '—',r['minimum_free_ram_gib'],r.get('mean_wall_seconds_per_outer_call','—')])+' |')
 lines+=['','## Odczyty przy wspólnym czasie','', '| Przypadek | t [s] | Fx_half [N] | Fz_half [N] | max CFL | Śr. y+ |','|---|---:|---:|---:|---:|---:|']
 for r in runs:
  h=r.get('at_common_time')
  if h:lines.append('| '+ ' | '.join(str(v) for v in [r['case'],h['physical_time_s'],h['Fx_half_N'],h['Fz_half_N'],h['max_convective_CFL'],h['foil_mean_yplus']])+' |')
 lines+=['','Porównanie obejmuje tylko próby z zapisanym postępem. Jeśli nie wszystkie cztery mają postęp, nie jest to pełne porównanie. Sprawdź logi residuali, lokalne y+, CFL i checkpointy. Pokrycie pełnymi pryzmami nadal wymaga oceny lokalnej.','']
 write(ROOT/'nightly_summary.md','\n'.join(lines))
 return data

