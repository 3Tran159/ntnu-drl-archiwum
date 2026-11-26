# Bieżący stan — autonomiczna rampa +2°, 03.11.2026

RAMP_C0_PLUS2_S5_20261103: SMOKE PASS, kontynuacja READY, nieuruchomiona.

Dokładna komenda PowerShell:
& "F:\ntnu\flap_control\START_RAMP_PLUS2.cmd"

Instrukcja: F:\ntnu\flap_control\RAMP_PLUS2_WORKFLOW.md
Status: F:\ntnu\flap_control\STATUS_CFD.cmd
Stop: F:\ntnu\flap_control\STOP_CFD.cmd

Istnieje jeden lokalny kontroler. Nie twórz drugiego. Kontroler ma accept_new_jobs=false; dedykowana komenda START_RAMP_PLUS2 włączy wyłącznie zatwierdzoną kontynuację. Work nie musi pozostać aktywny.

Eksperyment rozpoczęto z prawidłowego C0 t0,650 / iter11560. Pięć kroków aktywnego URANS przeprowadziło go do0,660 / iter11760, bez resetu pól lub czasu. P_min30065,17Pa; Overset bez błędów; geometria podąża za smoothstep. Dalszy start:
F:\ntnu\flap_control\hydro_validation_2606_20261102\cases\SP_C_split0_overset\ramp_plus2_20261103_093316\checkpoint.sim
SHA256:7129bdc3f60e8b6a0d70156a7d7094fb1c5e930df85ec9dd5035f17fe2bfc68c

Rampa2°*(10u^3−15u^4+6u^5),u=(t−0,650)/0,2 ograniczone do[0,1]. Od0,850s stałe+2°. dt0,002s;8CPU;bez GPU;40inner;fizyka/BC C0 zachowane.

Maksymalny czas fizyczny1,250s. Lokalna kontrola okien25kroków, residuals, ciśnienia, masy, k/omega i pełnego Overset. Checkpointy co50kroków i na zakończenie/pauzę/błąd. Wynik stabilny to kandydat do oceny,nie automatyczne zatwierdzenie danych do DRL lub analizy energetycznej.

Stary skokowy+2 pozostaje FAIL przy0,672s. Jego blokada NIE została zwolniona. Nowy eksperyment jest odrębnie autoryzowany w audit\RAMP_PLUS2_EXPLICIT_APPROVAL_20261103.json. Nowa awaria rampy blokuje jej kontynuację.

Pełnej rampy ani utrzymania+2 nie uruchamiano. Nie wykonywać benchmarków ani kolejnych wychyleń/fal. W04 i pozostałe kampanie nietknięte.

Dowody i stan w F:\ntnu\flap_control\hydro_validation_2606_20261102:
audit\RAMP_SMOKE_REVIEW_20261103.json
audit\RAMP_KINEMATIC_UNIT_TEST.json
audit\RAMP_GATE_TESTS_20261103.txt
audit\RAMP_LOCAL_START_CHECK_20261103.json
NIGHT_QUEUE.json,NIGHT_QUEUE_STATE.json,NIGHT_STATUS.json,NIGHT_DASHBOARD.html

Zasilanie/nieusypianie i dostęp do licencji pozostają warunkami lokalnej pracy. Brak autostartu Windows. Po ręcznej pauzie rampy użyj ponownie START_RAMP_PLUS2; nie używaj starego launchera relokacji ani generycznego RESUME do zwalniania blokady naukowej.
