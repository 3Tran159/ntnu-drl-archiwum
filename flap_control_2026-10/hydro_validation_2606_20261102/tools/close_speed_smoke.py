from pathlib import Path
import json,hashlib,csv,subprocess,shutil,html
import night_queue as q
H=Path(__file__).resolve().parents[1];R=H.parent;E='SPEED_SWEEP_PLUS2_20261103'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
st=q.read(q.STATE);cfg=q.read(q.CFG);rec=st['jobs'][E+'_SMOKE'];assert st.get('active') is None and rec['state']=='failed'
out=Path(rec['output']);cp=out/'error_checkpoint.sim';meta=st['checkpoint_integrity'][str(cp)]
assert meta['native_save_complete'] and sha(cp)==meta['sha256']
with (out/'history.csv').open() as f:rows=list(csv.DictReader(f))
assert len(rows)==1;row=rows[-1]
source=Path(rec['input']);assert sha(source)=='4f5fd71acc76a75f21fbacdaa8d6e2e0c3b4145d34fd3480b0a19429fbeba22a'
old=st['jobs']['RAMP_C0_PLUS2_S5_20261103_RUN'];assert old['state']=='failed'
oldcp=Path(old['output'])/'error_checkpoint.sim';assert sha(oldcp)=='971a9409a9fc4cc09e5cb38644b97cfacde3f59b71a5a483a5ebd2b65a08aa48'
exe=r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\win64\clang20.1vc14.2-r8\lib\starccm+.exe'
info=subprocess.run([exe,'-info',str(cp)],capture_output=True,text=True,check=True,timeout=60);assert 'Time 0.002 Iter 40' in info.stdout
(H/'audit/SPEED_CHECKPOINT_NATIVE_INFO_20261103.txt').write_text(info.stdout,encoding='utf8')
review=dict(at=q.now(),experiment_id=E,passed=False,status='FAIL_HOLD',native_test_steps=1,time_s=.002,iteration=40,U_m_s=10,flap_deg=2,CPU=8,GPU=False,dt=.002,inner_iterations=40,mesh_cells=333939,source_preserved=True,old_ramp_block_and_checkpoint_preserved=True,checkpoint=meta,native_metadata_readable=True,native_full_solution_reopen_tested=False,pressure_min_Pa=float(row['p_absolute_min_Pa']),mass_imbalance_relative=float(row['mass_imbalance_relative']),maximum_velocity_m_s=float(row['max_speed_m_s']),overset_errors=int(float(row['overset_error_cells'])),min_volume_m3=float(row['min_volume_m3']),min_quality=float(row['min_cell_quality']),flap_angle_deg=float(row['measured_angle_deg']),center_error_m=float(row['center_error_m']),cause_confirmed='Fresh uniform10m/s initialization diverged on first URANS timestep; strict pressure, mass and velocity guards rejected it.',not_proven='This is a numerical startup failure, not a physical cavitation prediction and not a stabilized+2 result. Exact startup mechanism not isolated.',next_required='Prepare and test a consistent, stable fixed+2/10m/s startup in a separately identified diagnostic. Do not continue this failed checkpoint, do not relax guards. No full sweep until native startup passes.',infrastructure_tests_passed=19,full_sweep_executed=False,static_points_accepted=[],scientific_approved=False,training_approved=False)
q.atomic(H/'audit/SPEED_SMOKE_REVIEW_20261103.json',review)
ap=H/'audit/SPEED_PLUS2_EXPLICIT_APPROVAL_20261103.json';a=q.read(ap);a.update(smoke_passed=False,full_run_launch_permitted=False,blocking_job=E+'_SMOKE',full_run_macro_sha256=sha(H/'macros/SpeedSweepPlus2Run.java'),infrastructure_tests='audit/SPEED_WORKFLOW_TESTS_20261103.txt');q.atomic(ap,a)
cfg['accept_new_jobs']=False;q.atomic(q.CFG,cfg)
work=q.read(H/'WORK_CURRENT_REVIEW.json');work.update(at=q.now(),status='FAIL_SPEED_STARTUP_HOLD',current_job_kind='speed_sweep',current_case_label='Fixed+2 at10m/s failed fresh startup',current_run=str(out),current_case_checkpoint=meta,last_decision='Fresh fixed+2/10m/s smoke failed after one timestep. Checkpoint saved, guards unchanged, no12/14/16/18 run. Ramp and abrupt+2 failures preserved.',obstacle=review['next_required'],next='HOLD: stable10m/s startup is missing. START_SPEED_SWEEP_PLUS2 refuses launch.',next_test=review['next_required'],current_mesh_cells=333939,scientific_approved=False,training_eligible=False);q.atomic(H/'WORK_CURRENT_REVIEW.json',work)
q.event('speed_smoke_failed_work_review',review=review)
dest=H/'reports/SPEED_SWEEP_PLUS2_20261103';dest.mkdir(exist_ok=True)
q.atomic(dest/'REPORT.json',review)
report='''<!doctype html><html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Stała klapka +2 — test workflow</title><style>body{font:17px system-ui;max-width:900px;margin:30px auto;padding:20px;line-height:1.5}pre{white-space:pre-wrap;overflow-wrap:anywhere}table{border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #ccc}</style><h1>FAIL / HOLD — rozruch przy 10 m/s</h1><p>Nowy eksperyment SPEED_SWEEP_PLUS2_20261103. Infrastruktura przygotowana, pełny sweep zablokowany.</p><p>Niezależna inicjalizacja: stała klapka +2°, 10 m/s, hydrostatyka, SST I=0,001 i μt/μ=10. Wyczyszczono odziedziczone pola i historię wyłącznie w roboczym stanie; oryginały zachowano. Siatka333939, geometria, Overset i model SST niezmienione. dt0,002s,40iteracji,8CPU.</p><table><tr><th>U [m/s]</th><th>Stan</th><th>CL/CD do porównania</th></tr><tr><td>10</td><td>FAIL po1 kroku, t0,002s</td><td>brak — niezbieżne</td></tr><tr><td>12/14/16/18</td><td>Nie uruchomiono</td><td>brak</td></tr></table><p>Ciśnienie−6,68×10¹⁰Pa i prędkość28510m/s są objawami rozbieżności numerycznej. Nie stanowią prognozy kawitacji. Overset:0błędów,1472acceptory,brak trudnej interpolacji. Dodatnie objętości i niezmienny kąt potwierdzone.</p><p>19 testów infrastruktury przeszło. Testy obejmują rzeczywiste procedury kolejki i makra, z atrapą zakończenia pełnego sweepu; nie zastępują obliczeń hydrodynamicznych. Natywnie potwierdzono reakcję na błąd, zapis i zakończenie procesu. Pełnego sweepu ani pełnego odtworzenia po awarii nie testowano.</p><p>Brakujący element: stabilna inicjalizacja stałej klapki+2 przy10m/s. Launcher odmawia uruchomienia do jej poprawnego testu. Nie wykonano kolejnej ręcznej próby naprawy solvera.</p><h2>Checkpoint i diagnostyka</h2><pre>'''+html.escape(json.dumps(review,indent=2,ensure_ascii=False))+'</pre></html>'
(dest/'REPORT.html').write_text(report,encoding='utf8')
manual='''# Stała klapka +2° — autonomiczny sweep prędkości

Stan 03.11.2026: **FAIL/HOLD po krótkim rozruchu10m/s; pełny sweep nie jest dopuszczony do startu.**

Nowy identyfikator: SPEED_SWEEP_PLUS2_20261103. Osobne zatwierdzenie: hydro_validation_2606_20261102\\audit\\SPEED_PLUS2_EXPLICIT_APPROVAL_20261103.json. Nie zwalnia ono nieudanego RAMP_C0_PLUS2_S5_20261103_RUN ani skokowego+2. Żadnego wyniku statycznego nie zaakceptowano.

| Operacja | Polecenie z F:\\ntnu\\flap_control |
|---|---|
| START | START_SPEED_SWEEP_PLUS2.cmd — obecnie bezpieczna odmowa: native smoke nie przeszedł |
| STOP | STOP_CFD.cmd — koniec przy bezpiecznej granicy kroku, checkpoint, brak następnego zadania |
| RESUME po ręcznej pauzie | START_SPEED_SWEEP_PLUS2.cmd — tylko zweryfikowany paused_checkpoint.sim tego eksperymentu; nigdy FAIL |
| STATUS | STATUS_CFD.cmd; NIGHT_DASHBOARD.html i SPEED_SWEEP_STATUS.json w katalogu kampanii |

Launcher wykorzystuje istniejący kontroler. Nie instaluje autostartu ani nowej kolejki. Nie powtarza ukończonych/nieudanych zadań. Wynik startu jest w runs\\speed_start_console.log; błędy w speed_start_error.log.

Przygotowany dalszy workflow (skompilowany, hydrodynamicznie nieprzetestowany): po udanym rozruchu stałe10m/s, potem12,14,16,18m/s. Zmiany U trwają0,2s według smoothstep5. Klapka pozostaje+2°, bez ruchu. Inlet i qS=0,5ρU²S aktualizowane w każdym kroku, S=0,0238m². CL z dotychczasową korektą wyporu22,6669635388N. Bilans masy względem bieżącego strumienia wlotowego. SST, hydrostatyczne granice ciśnieniowe i Overset pozostają niezmienione.

Do przejścia potrzeba co najmniej200 kroków przy stałym U, dwóch kolejnych kontroli okien25kroków: dryf CL/CD/Mh<0,5%, rozstęp<1%; redukcja residuals końcowe/początkowe≤0,01 w40iteracjach (Y-momentum pomijany jak wcześniej, z powodu poziomu zaokrągleń). Najwyżej500kroków ustalania danego U; brak stabilizacji daje HOLD. Próg pabs12339,2147668Pa, masa<1e-4, k/ω floor0, Overset error0, dodatnie V i jakość, face validity≥0,5, μt/μ<99999, Umax≤180m/s. Progi nie są obniżone.

Historia zmian U jest zachowana oddzielnie od tabeli statycznej. Tabela statyczna używa ostatniego zaakceptowanego okna25kroków. Ciśnienia mają osobne minima i współrzędne dla płata, klapki, szczeliny, otoczenia i całej cieczy. Akceptacja automatyczna dotyczy kontroli numerycznej POC, nie pełnej walidacji ilościowej ani danych treningowych.

Checkpointy: co100kroków, po zaakceptowanym U, na końcu i przy STOP/FAIL. Każdy zapis ma SHA-256 i metadane czasu/etapu. W nowym katalogu RUN zachowywane będą dwie ostatnie kopie okresowe; starsza kopia okresowa może być usunięta dopiero po zakończeniu i sprawdzeniu nowego zapisu. Wszystkie checkpointy etapowe, końcowe oraz istniejące wcześniejsze checkpointy są zachowywane. Przed kolejnym krokiem wymagane7GiB wolnego miejsca, aby zostawić miejsce na zapis; istniejące progi kontrolera niezmienione. Wznowienie od ręcznej pauzy zachowuje pola, czas, bieżący etap i wyniki ukończonych U, a ponownie zbiera okna stabilizacji.

Dashboard: NIGHT_DASHBOARD.html, SPEED_SWEEP_STATUS.json, SPEED_SWEEP_HISTORY.csv, SPEED_SWEEP_PRESSURE_HISTORY.csv, SPEED_SWEEP_STATIC_RESULTS.csv; po ustaleniu także SPEED_SWEEP_STATIC_PRESSURES.csv. Obecnie tabele statyczne są puste z powodu FAIL.

Kontroler może działać bez Work, jeśli komputer i licencja są dostępne. **Obecnego eksperymentu nie wolno jednak uruchomić autonomicznie:** brakuje stabilnego stanu startowego10m/s. START celowo blokuje ten przypadek. Nie edytować passed/failure_hold ani progów, aby go uruchomić. W04 pozostaje niezależny.

Raport: hydro_validation_2606_20261102\\reports\\SPEED_SWEEP_PLUS2_20261103\\REPORT.html. Testy: audit\\SPEED_WORKFLOW_TESTS_20261103.txt (19PASS). Natywny test:1krok, FAIL i checkpoint; pełne przejście pięciu U nie było liczone. Testowana była logika zakończenia kolejki na atrapach, a nie pięć poprawnych rozwiązań CFD.
'''
(R/'SPEED_SWEEP_PLUS2_WORKFLOW.md').write_text(manual,encoding='utf8')
for name in ['HOME_RESUME_INSTRUCTIONS.md','CFD_LOCAL_CONTROL.md']:
 p=R/name;shutil.copy2(p,H/'audit'/('before_speed_'+name));text=p.read_text(encoding='utf8');p.write_text('# Aktualizacja 03.11.2026 — obowiązująca blokada\n\nStała klapka+2, sweep10–18m/s: krótki rozruch10m/s zakończył się FAIL/HOLD przyt0,002s. Nie uruchamiać rampy ani kontynuować błędnego checkpointu. START_SPEED_SWEEP_PLUS2.cmd przygotowany, lecz celowo blokuje pełny start do uzyskania poprawnego smoke. Szczegóły: [SPEED_SWEEP_PLUS2_WORKFLOW.md](SPEED_SWEEP_PLUS2_WORKFLOW.md). W04 pozostaje niezależny. Poniższy wcześniejszy opis nie jest zgodą na wznowienie błędnych przypadków.\n\n---\n\n'+text,encoding='utf8')
q.publish(st,cfg,{},q.resources())
print(json.dumps(dict(status='FAIL_HOLD',checkpoint=meta,review=str(H/'audit/SPEED_SMOKE_REVIEW_20261103.json'),report=str(dest/'REPORT.html')),indent=2))
