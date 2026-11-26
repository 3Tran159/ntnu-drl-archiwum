from pathlib import Path
import json,sys,html,shutil,datetime
import pandas as pd,numpy as np
H=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102');R=H.parent;D=Path(__file__).resolve().parent
sys.path.insert(0,str(H/'tools'));import night_queue as q
result=q.read(D/'RECOVERY_RESULT.json');assert result['status']=='PASS'
cp=result['checkpoint'];P=Path(cp['path']).parent;hist=pd.read_csv(P/'history.csv');pr=pd.read_csv(P/'pressure_zones.csv')
st=q.read(q.STATE);cfg=q.read(q.CFG);assert not st.get('active') and not q.LOCK.exists();assert not any(p['ownedBatch'] for p in q.processes());assert cfg['accept_new_jobs'] is False
rs=q.resources();initial=result['initial_native_readback'];last=hist.iloc[-1]
force={}
for col,src in [('CL_hydro','CL'),('CD','CD'),('Mh_Nm','Mh')]:
 mean=hist[col].tail(25).mean();previous=hist[col].iloc[-50:-25].mean();ran=hist[col].tail(25).max()-hist[col].tail(25).min()
 force[col]=dict(initial=initial[src],final=float(last[col]),change_percent=float(100*(last[col]-initial[src])/abs(initial[src])),last25_vs_previous25_drift_percent=float(100*abs(mean-previous)/abs(mean)),last25_range_percent=float(100*ran/abs(mean)))
force_review=dict(quantitative_static_acceptance=False,reason='U remains time-dependent; forces and CD are still drifting. Initial saved forces match exactly. No static data point has been accepted.',values=force,velocity_propagation=result['velocity_field'],preserved_force_gate='After U reaches10 and at each static point: minimum200holdsteps; adjacent25-step windows, drift<0.5%,range<1%,last25 residual pass; two consecutive checks; max750holdsteps thenHOLD.')
q.atomic(D/'FORCE_TRANSIENT_REVIEW.json',force_review)
matched=hist.iloc[(hist.U_m_s-17.8239976448).abs().argmin()]
evidence=q.read(D/'ROOT_CAUSE_EVIDENCE.json');evidence.update(test_status='PASS_PRESSURE_RECOVERY_DIAGNOSTIC',test_result=str(D/'RECOVERY_RESULT.json'),matched_failure_speed=dict(U_m_s=float(matched.U_m_s),time_s=float(matched.time_s),new_global_pmin_Pa=float(matched.p_absolute_min_Pa),old_global_pmin_Pa=7175.4822901048465),campaign='PREPARED_NOT_STARTED; resource HOLD: freeF<15GiB',force_static_acceptance=False)
q.atomic(D/'ROOT_CAUSE_EVIDENCE.json',evidence)
verify=dict(at=q.now(),checkpoint=cp,source_native_readback=True,output_native_info_success=True,output_native_info='STAR2606.0002 Np8 Step395 Time0.79 Iter14860',output_full_solution_reopen_performed=False,failed_checkpoint_native_info_success=True,failed_checkpoint_native_info='Step353 Time0.71(rounded) Iter12760; exact stored export time0.706',owned_STAR_roots=[],owned_children_remaining=st.get('last_metrics',{}).get('owned_active_pids',[]),controller_running=False,accept_new_jobs=False,pending_job='RECOVERED_FIXED_PLUS2_SWEEP_20261103_RUN',launcher='F:\\ntnu\\flap_control\\START_RECOVERED_FLAP_SWEEP.cmd',launcher_preflight='HOLD: Insufficient resource reserve',resources=rs,minimum_launch_disk_GiB=15,guard_tests='15 isolated tests passed; no CFD launched by tests',old_failures_preserved=True,W04_untouched=True)
q.atomic(D/'FINAL_STATUS.json',verify)
work=q.read(H/'WORK_CURRENT_REVIEW.json');work.update(at=q.now(),status='PRESSURE_REPAIR_PASS_DIAGNOSTIC_ONLY',current_job_kind='pressure_recovery',current_case_label='C0 pressure recovery, t0.790, delta0',current_run=str(P),current_mesh_cells=333939,scientific_approved=False,training_eligible=False,last_decision='Single 50-step C2 deceleration repair passed pressure/residual/mass/Overset checks. Domain inertia caused inlet depression. Forces remain transient. Full campaign prepared but not started.',obstacle=f'F: {rs["disk_free_GiB"]}GiB free; unchanged startup reserve15GiB. Static forces not yet stabilized.',next='After sufficient disk reserve, manual START_RECOVERED_FLAP_SWEEP.cmd continues from t0.790 without reset; settleC0at10 before flap+2.',next_test='Prepared guarded continuation; no further smoke variants',parameters={**work.get('parameters',{}),'U':cp['U_m_s'],'Re':1190000*cp['U_m_s'],'delta':0,'dt':.002,'inner':50,'CPU_max':8},current_case_checkpoint={**cp,'saved_time_s':cp['time_s'],'native_save_complete':True,'native_reopen_verified':False,'native_metadata_read_verified':True},root_cause_report=str(D/'ROOT_CAUSE_REPORT.html'),pressure_recovery_result=str(D/'RECOVERY_RESULT.json'))
q.atomic(H/'WORK_CURRENT_REVIEW.json',work)
# Publish one final snapshot without starting a controller or solver.
st['queue_state']='CONTROLLER_STOPPED';st['next_job']='RECOVERED_FIXED_PLUS2_SWEEP_20261103_RUN';q.publish(st,cfg,st.get('last_metrics',{}),rs)
base=q.read(H/'NIGHT_STATUS.json');base.update(queue_pid=None,local_queue_started=False,solver_state='STOPPED',operation='STOPPED',solver_actually_advancing=False,last_solved_case='C0 pressure recovery diagnostic,0deg,333939cells',current_case_path=str(P),pending_campaign_state='HOLD_RESOURCES_AND_MANUAL_START');q.atomic(H/'NIGHT_STATUS.json',base)
report=(D/'ROOT_CAUSE_REPORT.html').read_text(encoding='utf8');a=report.index('<p><b>Wynik testu:</b>');b=report.index('<details>',a)
summary=f'''<h2>Wynik jedynego testu: PASS diagnostyczny</h2><p>50 kroków, t=0,690→0,790 s, iteracje12360→14860, U=17,93152→17,796725 m/s, δ=0°. Najniższe pABS podczas całego testu: <b>22,443 kPa</b>; przy wlocie <b>34,567 kPa</b>. Końcowe minimum globalne 29,264 kPa; inlet42,604 kPa, klapka47,720 kPa, szczelina52,060 kPa. W starej komórce minimum jest teraz94,211 kPa.</p>
<p>Przy dokładnie tej samej U=17,8239976 m/s: poprzednio7,175 kPa, po poprawce29,268 kPa. Przyspieszenie jest dziesięciokrotnie mniejsze. To kontrolowana interwencja potwierdzająca mechanizm ciśnienia bezwładnościowego.</p>
<p>Wszystkie50 okien residuali spełniają pierwotny próg0,01 dla kontrolowanych równań. Maksimum ω w ostatnich25 krokach:0,00390206. Y-momentum zachowuje wcześniejsze jawne wyłączenie dla quasi2D ze względu na normalizację4,9145e−16; nie jest prezentowane jako spełniające ten sam próg. Maksymalny względny niezbilansowany strumień masy1,74214e−7. Overset:333939komórek,255350aktywnych,77108nieaktywnych,1481acceptorów,0błędów i0trudnych interpolacji. MinV=9,12875e−12m³, minQ=0,0610482; brak zmiany pozycji klapki.</p>
<p><b>Siły pozostają przejściowe.</b> Odczyt początkowy zgadza się dokładnie z checkpointem. Na końcu CL={last.CL_hydro:.9f}, CD={last.CD:.9f}, Mh={last.Mh_Nm:.6f}Nm. CD wzrósł o{force['CD']['change_percent']:.2f}% podczas zmiany przepływu; to nie jest zaakceptowany punkt statyczny. Średnia składowa U w pierwszej warstwie przy wlocie17,796778m/s, w obszarze przed płatem17,925291m/s: pole nie jest jeszcze ustalone. Pełna interpretacja sił wymaga etapów stabilizacji i kontroli siatki/czasu. Dotychczasowe bramki sił pozostają bez zmian.</p>
<img src="recovery_result.png"><p>Checkpoint: <code>{html.escape(cp['path'])}</code><br>Rozmiar:{cp['bytes']}B<br>SHA-256:<code>{cp['sha256']}</code><br>Zapis natywny kompletny; STAR-info odczytał Step395, Time0,79, Iter14860, Np8. Sprawdzono nagłówek i integralność; nie wykonano dodatkowego pełnego otwarcia nowego rozwiązania w solverze.</p>
<h2>GO / HOLD</h2><p><b>GO: poprawka tempa hamowania do dalszej diagnostyki.</b> Kontynuacja przygotowana w istniejącym kontrolerze, skompilowana;15 izolowanych testów zabezpieczeń PASS. Nie rozpoczęto pełnej kampanii. Nowy identyfikator RECOVERED_FIXED_PLUS2_SWEEP_20261103; poprzednie FAIL pozostają zablokowane. W04 nietknięty.</p>
<p><b>HOLD uruchomienia:</b> F: ma {rs['disk_free_GiB']:.2f}GiB wolnego przy wymaganych15GiB; trzeba odzyskać co najmniej{15-rs['disk_free_GiB']:.2f}GiB. Sprawdzony launcher odmawia startu przy tym stanie. Nic nie usunięto i progu nie obniżono. Po zapewnieniu miejsca: <code>F:\\ntnu\\flap_control\\START_RECOVERED_FLAP_SWEEP.cmd</code>. Kolejność: kontynuacja hamowania do10 (t=4,2), stabilizacja0°, płynna klapka+2° przy10, stabilizacja, następnie12/14/16/18 tylko po bramkach. Brak autostartu po restarcie systemu.</p>
<p><a href="RECOVERY_RESULT.json">Wynik testu JSON</a> · <a href="FORCE_TRANSIENT_REVIEW.json">Ocena sił</a> · <a href="FINAL_STATUS.json">Stan końcowy</a></p>'''
report=report[:a]+summary+report[b:];report=report.replace('"test_status": "RUNNING_OR_PENDING_NATIVE_RESULT"','"test_status": "PASS_PRESSURE_RECOVERY_DIAGNOSTIC"').replace('"campaign": "HOLD until test review"','"campaign": "PREPARED_NOT_STARTED; HOLD_RESOURCES"')
(D/'ROOT_CAUSE_REPORT.html').write_text(report,encoding='utf8')
instructions=R/'HOME_RESUME_INSTRUCTIONS.md';backup=H/'audit'/('HOME_RESUME_before_pressure_repair_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.md');shutil.copy2(instructions,backup)
head=f'''# Bieżący stan — 03.11.2026: poprawka hamowania C0

Jedyny test naprawczy PASS diagnostyczny. Solver i kontroler zatrzymane. Kampania przygotowana, ale NIE uruchomiona. Poprzednie FAIL pozostają zablokowane; W04 niezależny i nietknięty.

- Checkpoint: `{cp['path']}`
- STAR2606.0002, 8MPI CPU, bezGPU; t={cp['time_s']}, iteracja{cp['iteration']}, dt=0.002s, inner50; U={cp['U_m_s']}, δ=0°.
- SHA256: `{cp['sha256']}`; {cp['bytes']}B; natywny zapis i odczyt metadanych potwierdzone.
- GO dotyczy usunięcia przyczyny podciśnienia; siły są przejściowe, żadnego punktu statycznego nie zatwierdzono.
- F: {rs['disk_free_GiB']:.2f}GiB wolnego, wymagane15GiB. Launcher utrzymuje HOLD do spełnienia rezerwy; nie usuwać checkpointów w ciemno.
- START / RESUME po zapewnieniu zasobów: `F:\\ntnu\\flap_control\\START_RECOVERED_FLAP_SWEEP.cmd`.
- STOP: `F:\\ntnu\\flap_control\\STOP_CFD.cmd` (zapis na granicy kroku; potem sprawdzić STATUS).
- STATUS: `F:\\ntnu\\flap_control\\STATUS_CFD.cmd` oraz `F:\\ntnu\\flap_control\\hydro_validation_2606_20261102\\NIGHT_DASHBOARD.html`.
- Wznowienie zachowuje pola/czas/siatkę. Procedura C2: faza S5 po t0.710 rośnie0.25/s; U osiąga10 przyt4.2. Następnie stabilizacjaC0, rampa+2° przy10 i punkty10/12/14/16/18 z dotychczasowymi bramkami. Starej szybkiej rampy18→10 nie uruchamiać.
- Kontynuacja: `RECOVERED_FIXED_PLUS2_SWEEP_20261103_RUN`, makro `RecoveredFixedFlapSweep.java`, runtime `audit/RECOVERED_SWEEP_RUNTIME.properties`, zgoda `audit/RECOVERED_SWEEP_APPROVAL_20261103.json`.
- Raport: `{D/'ROOT_CAUSE_REPORT.html'}`. W kontrolerze `accept_new_jobs=false`; brak autostartu Windows.

Poniżej zachowano historyczne instrukcje; bieżący stan powyżej ma pierwszeństwo.

---

'''
instructions.write_text(head+instructions.read_text(encoding='utf8'),encoding='utf8')
q.event('pressure_root_cause_review_complete',verdict='GO_DIAGNOSTIC_REPAIR_HOLD_RESOURCES',checkpoint=cp,report=str(D/'ROOT_CAUSE_REPORT.html'),continuation_started=False)
print(json.dumps(dict(report=str(D/'ROOT_CAUSE_REPORT.html'),status=verify,forces=force),indent=2))
