from pathlib import Path
import json,datetime,shutil,py_compile
h=Path(__file__).resolve().parents[1];at=datetime.datetime.now().astimezone().isoformat();backup=h/'runs/controller_snapshots'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True)
for name in ['night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/name,backup/name)
p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8')
i=s.index(" if review.get('current_mesh_cells') and any(tag");j=s.index(" atomic(H/'NIGHT_STATUS.json',base)",i)
s=s[:i]+""" flowpath=str(view['flow_metrics'].get('last_output_sim',''))
 if any(tag in flowpath for tag in ['c0_tight_','c0_urans_','c0_top_direction_']):
  base['last_solved_case']='C0 split flap,0degrees,Overset,333939cells';base['mesh_cells']=333939
 elif 'SP_B_split0_fixed' in flowpath:
  base['last_solved_case']='B0 split flap,0degrees,noOverset,256750cells';base['mesh_cells']=256750
 if active and review.get('current_run')==active.get('output'):
  base['current_case_label']=review.get('current_case_label',active['id']);base['current_case_mesh_cells']=review.get('current_mesh_cells')
  if view['metrics'].get('history_rows',0)>0:
   base['last_solved_case']=base['current_case_label'];base['mesh_cells']=review.get('current_mesh_cells')
 base['reviewed_recovery_checkpoint']=review.get('current_case_checkpoint',review.get('latest_top_boundary_checkpoint',review.get('reviewed_recovery_checkpoint')))
"""+s[j:]
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
p=h/'tools/night_dashboard.py';s=p.read_text(encoding='utf8')
s=s.replace("recovery=review.get('reviewed_recovery_checkpoint',{})","recovery=review.get('current_case_checkpoint',review.get('latest_top_boundary_checkpoint',review.get('reviewed_recovery_checkpoint',{})))")
needle=" state=base.get('solver_state','STOPPED');"
assert needle in s;s=s.replace(needle," if a and not a['macro'].startswith(('Inspect','Prepare','Finalize')) and view.get('metrics',{}).get('history_rows',0)==0:m={'physical_time_s':a.get('initial_time_s'),'operation':'Uruchamianie — brak nowych danych przepływu'}\n"+needle)
s=s.replace("<td>C bieżący — ostatni krok</td>","<td>'+e('B bieżący — bez Overset, ostatni krok' if a and a.get('variant')=='SP_B' else 'C bieżący — ostatni krok')+'</td>")
needle=" jobs=''.join("
assert needle in s
s=s.replace(needle," topmeans=review.get('completed_top_boundary_review',{}).get('last25_means',{})\n if topmeans:corrected_row+='<tr><td>C0 top Extrapolated — zakończony test</td><td>'+format(topmeans['CL_hydro'],'.7f')+'</td><td>'+format(topmeans['CD'],'.8f')+'</td><td>Mechanizm potwierdzony; dopasowane B i ustalanie przepływu nadal wymagane</td></tr>'\n"+needle)
s=s.replace('Siły ustabilizowane; bez walidacji siatki','Historyczna granica; wspólny problem górnej granicy — HOLD')
s=s.replace('Pełna kontrola Overset co 25 kroków.','W C pełna kontrola Overset co 25 kroków; B nie ma Overset.')
s=s.replace('Geometria fizyczna i warunki porównawcze są zachowane; zmiany siatki i numeryki opisano w dzienniku.','Geometria fizyczna jest zachowana. Zmiana górnej granicy i dopasowanie B/C są jawnie opisane w dzienniku; stare i nowe warunki nie są mieszane w zatwierdzonym porównaniu.')
s=s.replace('<details><summary>Porównanie pól po zmianie interpolacji</summary>', '<details><summary>Aktualna diagnostyka górnej granicy</summary><img src="reports/C0_top_boundary_fields_final.png" alt="Pola górnej granicy przed i po zmianie"><img src="reports/C0_top_backflow_residual_decay.png" alt="Poprawa redukcji residuals"></details><details><summary>Historyczne porównanie pól po zmianie interpolacji</summary>')
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text(encoding='utf8'));cfg['controller_exit_requested']=True;tmp=cfgp.with_suffix('.work_tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as out:out.write(json.dumps(dict(at=at,kind='status_presentation_BC_separation_fix',scope='Presentation only. Correct currentB label/cell count, avoid showing previousC forces during B startup, prefer latest reviewed checkpoint. No solver/geometry/physics mutation. Adopt active native process without interruption.'))+'\n')
print(json.dumps(dict(at=at,presentation_patch=True,solver_untouched=True),indent=2))
