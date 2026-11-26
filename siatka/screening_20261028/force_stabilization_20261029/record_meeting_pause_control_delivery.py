import json,datetime,shutil
from pathlib import Path
import manual_control_common as c
R=c.R;B=R.parent;D=B/'dashboard_work_20261030';now=datetime.datetime.now().astimezone();tag=now.strftime('%Y%m%d_%H%M%S')
s=c.read(R/'wave_foil_run_state.json');case=c.safe_case(s['directory']);done=c.read(case/'completed.json')
freeze=c.read(R/'meeting_dashboard_freeze_20261030.json')
assert all(c.digest(B/n)==freeze['sha256'][n] for n in ('dashboard.html','professor_dashboard.html'))
assert done['status']=='stopped_by_marker' and abs(done['time_s']-.168)<1e-8
record=dict(updated_at=now.isoformat(),status='paused_by_user_until_after_meeting_and_power_connection',no_automatic_resume=True,case=case.name,physical_time_s=done['time_s'],computed_sim=str(case/'final.sim'),computed_sim_bytes=(case/'final.sim').stat().st_size,server_kept_open=True,server_launcher_pid=s.get('launcher_pid'),holder_pid=s.get('controller_pid'),local_control_server_pid=c.read(R/'manual_control_server.lock').get('pid'),original_dashboards_frozen=True,working_directory=str(D),qa='manual_panel_ui_review_20261030.json',control_tests='manual_control_test_review.json',manual_macro='manual_macro_build_receipt.json',limitation='Manual presets compiled and control logic tested with a mocked launcher. No new CFD run executed after user pause. Every manual Start uses a fresh source; continuation of paused fields is separate.',separate_HF_untouched=True)
(R/'manual_control_delivery_20261030.json').write_text(json.dumps(record,indent=2),encoding='utf8')
for name in ('overnight_plan_20261029.json','wave_numerical_review_current.json'):
 p=R/name;shutil.copy2(p,R/(p.stem+'.before_meeting_pause_'+tag+'.json'));v=c.read(p)
 v['updated_at']=now.isoformat();v['execution']='PAUSED by user for meeting and unplugged computer. Resume only after explicit user signal following meeting and power reconnection. No automatic solver launch.'
 v['current_pause']=record
 if name=='wave_numerical_review_current.json':v['status']='exploratory_W01_paused_saved_server_open'
 p.write_text(json.dumps(v,indent=2),encoding='utf8')
hand=R/'RESUME_AT_HOME.txt';shutil.copy2(hand,R/('handover_history_'+tag+'.txt'))
header=f"""USER PAUSE + MEETING DASHBOARD FREEZE — {now.isoformat()}
Do not launch any calculation until the user explicitly resumes after the meeting and reconnecting power.
W01 stopped by marker at t={done['time_s']:.3f}s, 148 main steps after40 startup halfsteps. final.sim {record['computed_sim_bytes']}bytes contains computed fields, not a template:
{record['computed_sim']}
STAR launcher{s.get('launcher_pid')} remains open because user opened the simulation interactively and asked not to close it. New run_hold_wave_server.py owner{s.get('controller_pid')} holds root queue.lock; previous supervisor32956 was terminated ALONE after completed save to prevent its time budget from killing the stopped server. Never kill server or duplicate this holder. No further steps are running under our controller. SeparateHF untouched.
Original B/dashboard.html and professor_dashboard.html are FROZEN for meeting. dashboard monitor1972 exited via STOP_DASHBOARD_MONITOR; do not run original builders/update_status or restart monitor while frozen. Preserve meeting_dashboard_freeze_20261030.json hashes.
All new presentation is in B/dashboard_work_20261030. Local control URL http://127.0.0.1:8771/ serves only copies. Service PID{record['local_control_server_pid']} refreshes copy-only telemetry/builds every25s, no auto-solve. Open_NTNU_Control.cmd in that working directory reopens service/browser independently of Work.
ManualFoilWave.java compiled with STARjars; source fingerprint recorded. Prepared selectable C01/W01 M09+M10, plus fresh H.25/.75 L20 exploratory variants. L10/L30/L40 disabled until correctdomains/inputs prepared. Target .05–12s / wall10–720min, graceful stop and saved stop schedules; never arbitrary sourcepaths. EachStart is FRESHt0, not a continuation. Rootlock/ownprocess/resource/sourceguards retained. Actual new variant flow runs NOT tested because user paused; only compile and mocked HTTP/stopfile tests passed. User accepts prior observedmass residual for exploration; historical.01% flags and scientificlimits retained.
Both copied views passed1920/1360/390 andprint. Current W01 saved sample CD.0105728,CL.2082086 at.168 is startup instantaneous, not mean. R14.750s explicitly historical no-foil. Currentcomputed.sim paths visible; nozero-time template offeredasresult.
Automation ntnu-dob-r-siatki-i-fale remains PAUSED (automation.toml verified). No automatic overnight resumption.
See manual_control_delivery_20261030.json, manual_panel_ui_review_20261030.json, manual_control_test_review.json.
Prior notes below are historical.

"""
hand.write_text(header+hand.read_text(encoding='utf8'),encoding='utf8')
(D/'README_CONTROL.txt').write_text("""NTNU — robocze kopie dashboardow i sterowanie lokalne

Na spotkaniu korzystaj z dashboard.html oraz professor_dashboard.html w glownym katalogu mesh_screening_20261028. Zostaly zamrozone; ta podteczka zawiera nowe kopie robocze.

Aby otworzyc sterowanie bez Work: uruchom Open_NTNU_Control.cmd z tego katalogu. Panel: http://127.0.0.1:8771/
Otwarcie panelu NIE rozpoczyna obliczen. Wybierz gotowy przypadek, czas fizyczny konca [s] i limit rzeczywistego czasu pracy komputera [min], potem Start new case. Kazdy Start tworzy NOWA kopie od t=0, nie nadpisuje i nie wznawia poprzedniego przebiegu.
Stop and save zatrzymuje na granicy kroku i zapisuje policzone pola. Mozna tez ustawic stop przy czasie fizycznym albo za podana liczbe minut; wygrywa najwczesniejszy limit. Obecnego targetu nie da sie tym wydluzyc.
Do zakonczenia zapisu pozostaw komputer wlaczony. Zamkniecie karty przegladarki nie zatrzymuje kontrolera ani obliczen. Serwer lokalny i kontroler nie potrzebuja aktywnej sesji Work. Licencja STAR, zasilanie i zasoby komputera nadal sa potrzebne.
Teraz W01 jest ZATRZYMANY i zapisany przy0.168s. STAR pozostal otwarty do podgladu na Twoje zyczenie, dlatego kolejka jest zajeta i przyciski startu sa zablokowane. Nie zamykamy tego serwera automatycznie.
Po spotkaniu i ponownym podlaczeniu zasilania zdecydujemy o dalszych obliczeniach. Brak automatycznego wznowienia.
W panelu sa sciezki do katalogu i do final.sim/checkpointow z rzeczywistym dodatnim czasem obliczen. Plik z0s nie jest wynikiem. Otwieranie scen nie rozpoczyna obliczen.
Mozesz zmieniac domene w STAR, ale wtedy potrzebna jest nowa siatka, poprawione strefy falowe/diagnostyka wylotu i dopasowany spokojny przypadek. Zmodyfikowane pliki zrodlowe sa odrzucane przez kontrole tozsamosci. Warianty lambda10/30/40 czekaja na przygotowanie odpowiednich domen.
Makro skompilowano; logike przyciskow i blokad przetestowano bez uruchamiania solvera. Nowe warianty wymagaja pierwszego kontrolowanego uruchomienia. Wyniki falowe sa eksploracyjne; rozruchowe CL/CD nie sa srednimi po ustalonych cyklach.
""",encoding='utf8')
print(json.dumps({k:record[k] for k in ('status','physical_time_s','computed_sim_bytes','original_dashboards_frozen','working_directory')},indent=2))
