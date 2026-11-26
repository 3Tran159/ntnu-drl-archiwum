from pathlib import Path
import json,datetime,os,shutil,py_compile
h=Path(__file__).resolve().parents[1];stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
queue=h/'tools/night_queue.py';dash=h/'tools/night_dashboard.py'
for p in [queue,dash,h/'NIGHT_QUEUE.json']:shutil.copy2(p,backup/p.name)
s=queue.read_text(encoding='utf8')
needle=" atomic(H/'NIGHT_STATUS.json',base)"
assert s.count(needle)==1
s=s.replace(needle," base['C0_bias_status']=cfg['scientific_gates'].get('reason','')\n if active and review.get('current_run')==active.get('output'):\n  base['last_solved_case']='C0 split flap, 0 degrees, '+str(review.get('current_mesh_cells','unknown'))+' cells'\n  base['mesh_cells']=review.get('current_mesh_cells')\n"+needle)
queue.write_text(s,encoding='utf8');py_compile.compile(str(queue),doraise=True)
s=dash.read_text(encoding='utf8')
needle=" jobs=''.join("
assert needle in s
pos=s.index(needle)
s=s[:pos]+" corrected=review.get('completed_urans_review',{}).get('last_25_means',{});corrected_row=''<+>\n".replace("'<+>","'")+s[pos:]
# Insert presentation-only rows. No queue or scientific gate changes.
s=s.replace("corrected_row=''\n",'''corrected_row=''
 if corrected:corrected_row='<tr><td>C poprawiony — URANS, 15 iteracji</td><td>'+format(corrected.get('CL_hydro',0),'.7f')+'</td><td>'+format(corrected.get('CD',0),'.8f')+'</td><td>Kontrola pól i okien sił przeszła; audyt naukowy trwa</td></tr>'
 if m.get('CL_hydro') is not None:corrected_row+='<tr><td>C bieżący — ostatni krok</td><td>'+format(m['CL_hydro'],'.7f')+'</td><td>'+format(m.get('CD',0),'.8f')+'</td><td>'+e(review.get('obstacle','Oczekuje oceny Work'))+'</td></tr>'
''')
s=s.replace('W przebiegu transient zapis co 25 kroków, Δt = 0,002 s. W osobnym teście czystej inicjalizacji zapis co 250 iteracji; czas fizyczny pozostaje 0 s. Każdy wynik wymaga oceny Work.','Bieżący test URANS: checkpoint co 50 kroków oraz na zakończenie; Δt = 0,002 s. Pełna kontrola Overset co 25 kroków. Każdy wynik wymaga oceny Work.')
s=s.replace('C — klapka 0°, Overset, 15 iteracji','C stary — odrzucona konfiguracja Overset')
s=s.replace('<td>HOLD — niezatwierdzony</td></tr></table>','<td>ODRZUCONY — artefakty pól</td></tr>{corrected_row}</table>')
dash.write_text(s,encoding='utf8');py_compile.compile(str(dash),doraise=True)
cfgpath=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgpath.read_text(encoding='utf8'));assert cfg['scientific_gates']['C0_bias_explained_and_approved'] is False
cfg['controller_exit_requested']=True;tmp=cfgpath.with_suffix('.work_tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');os.replace(tmp,cfgpath)
print(json.dumps(dict(backup=str(backup),change='Status/dashboard presentation only; active native solver untouched; request controller handover'),indent=2))
