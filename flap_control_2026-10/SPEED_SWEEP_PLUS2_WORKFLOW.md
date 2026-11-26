# Stała klapka +2° — autonomiczny sweep prędkości

Stan 03.11.2026: **FAIL/HOLD po krótkim rozruchu10m/s; pełny sweep nie jest dopuszczony do startu.**

Nowy identyfikator: SPEED_SWEEP_PLUS2_20261103. Osobne zatwierdzenie: hydro_validation_2606_20261102\audit\SPEED_PLUS2_EXPLICIT_APPROVAL_20261103.json. Nie zwalnia ono nieudanego RAMP_C0_PLUS2_S5_20261103_RUN ani skokowego+2. Żadnego wyniku statycznego nie zaakceptowano.

| Operacja | Polecenie z F:\ntnu\flap_control |
|---|---|
| START | START_SPEED_SWEEP_PLUS2.cmd — obecnie bezpieczna odmowa: native smoke nie przeszedł |
| STOP | STOP_CFD.cmd — koniec przy bezpiecznej granicy kroku, checkpoint, brak następnego zadania |
| RESUME po ręcznej pauzie | START_SPEED_SWEEP_PLUS2.cmd — tylko zweryfikowany paused_checkpoint.sim tego eksperymentu; nigdy FAIL |
| STATUS | STATUS_CFD.cmd; NIGHT_DASHBOARD.html i SPEED_SWEEP_STATUS.json w katalogu kampanii |

Launcher wykorzystuje istniejący kontroler. Nie instaluje autostartu ani nowej kolejki. Nie powtarza ukończonych/nieudanych zadań. Wynik startu jest w runs\speed_start_console.log; błędy w speed_start_error.log.

Przygotowany dalszy workflow (skompilowany, hydrodynamicznie nieprzetestowany): po udanym rozruchu stałe10m/s, potem12,14,16,18m/s. Zmiany U trwają0,2s według smoothstep5. Klapka pozostaje+2°, bez ruchu. Inlet i qS=0,5ρU²S aktualizowane w każdym kroku, S=0,0238m². CL z dotychczasową korektą wyporu22,6669635388N. Bilans masy względem bieżącego strumienia wlotowego. SST, hydrostatyczne granice ciśnieniowe i Overset pozostają niezmienione.

Do przejścia potrzeba co najmniej200 kroków przy stałym U, dwóch kolejnych kontroli okien25kroków: dryf CL/CD/Mh<0,5%, rozstęp<1%; redukcja residuals końcowe/początkowe≤0,01 w40iteracjach (Y-momentum pomijany jak wcześniej, z powodu poziomu zaokrągleń). Najwyżej500kroków ustalania danego U; brak stabilizacji daje HOLD. Próg pabs12339,2147668Pa, masa<1e-4, k/ω floor0, Overset error0, dodatnie V i jakość, face validity≥0,5, μt/μ<99999, Umax≤180m/s. Progi nie są obniżone.

Historia zmian U jest zachowana oddzielnie od tabeli statycznej. Tabela statyczna używa ostatniego zaakceptowanego okna25kroków. Ciśnienia mają osobne minima i współrzędne dla płata, klapki, szczeliny, otoczenia i całej cieczy. Akceptacja automatyczna dotyczy kontroli numerycznej POC, nie pełnej walidacji ilościowej ani danych treningowych.

Checkpointy: co100kroków, po zaakceptowanym U, na końcu i przy STOP/FAIL. Każdy zapis ma SHA-256 i metadane czasu/etapu. W nowym katalogu RUN zachowywane będą dwie ostatnie kopie okresowe; starsza kopia okresowa może być usunięta dopiero po zakończeniu i sprawdzeniu nowego zapisu. Wszystkie checkpointy etapowe, końcowe oraz istniejące wcześniejsze checkpointy są zachowywane. Przed kolejnym krokiem wymagane7GiB wolnego miejsca, aby zostawić miejsce na zapis; istniejące progi kontrolera niezmienione. Wznowienie od ręcznej pauzy zachowuje pola, czas, bieżący etap i wyniki ukończonych U, a ponownie zbiera okna stabilizacji.

Dashboard: NIGHT_DASHBOARD.html, SPEED_SWEEP_STATUS.json, SPEED_SWEEP_HISTORY.csv, SPEED_SWEEP_PRESSURE_HISTORY.csv, SPEED_SWEEP_STATIC_RESULTS.csv; po ustaleniu także SPEED_SWEEP_STATIC_PRESSURES.csv. Obecnie tabele statyczne są puste z powodu FAIL.

Kontroler może działać bez Work, jeśli komputer i licencja są dostępne. **Obecnego eksperymentu nie wolno jednak uruchomić autonomicznie:** brakuje stabilnego stanu startowego10m/s. START celowo blokuje ten przypadek. Nie edytować passed/failure_hold ani progów, aby go uruchomić. W04 pozostaje niezależny.

Raport: hydro_validation_2606_20261102\reports\SPEED_SWEEP_PLUS2_20261103\REPORT.html. Testy: audit\SPEED_WORKFLOW_TESTS_20261103.txt (19PASS). Natywny test:1krok, FAIL i checkpoint; pełne przejście pięciu U nie było liczone. Testowana była logika zakończenia kolejki na atrapach, a nie pięć poprawnych rozwiązań CFD.
