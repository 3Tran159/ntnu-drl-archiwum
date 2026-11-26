# NTNU CFD · niezależny audyt startu +2° przy 10 m/s

Status: 2026-11-03. Tylko diagnostyka i przygotowanie nowego wariantu, bez rozpoczęcia nowych obliczeń.

## Zaobserwowane dane
- Przed startem: równomierny przepływ 10 m/s, pABS min 42 741.746 Pa, k=0.00015, ω=15/s, fizyczny czas 0.
- Pierwszy krok t=0.002 s: Umax=28 509.9609 m/s, pABS min=-66 751 874 017 Pa, mass imbalance=8.8455e-4, siły rzędu milionów N.
- Najgorsze ciśnienie na nieruchomej części przy LE, x=0.004314 m, z=-0.006626 m. Lokalny Overset: 0 błędów, 0 trudnych interpolacji, wszystkie objętości dodatnie.
- Makro SpeedSweepPlus2Smoke.java wywołuje clearSolution(Histories,Fields), initializeSolution i natywną inicjalizację ciągłości z jednorodnego pola.

Wniosek: wynik to niefizyczna rozbieżność numeryczna zimnego startu. Ustalony +2°/10 m/s NIE został policzony. Dokładny mechanizm niestabilności nie został dowiedziony.

## Preferowany eksperyment zastępczy
1. C0: poprawny zapis 0°, 18 m/s, t=0.650 s, iteracja 11560; zachować wszystkie pola.
2. Przy nieporuszanej klapce 0° płynnie obniżyć prędkość wlotu 18→10 m/s, spójnie aktualizując qS i bilans masy; zbadać okres przejściowy.
3. Ustalić przepływ przy 10 m/s, skontrolować pABS, k/ω, residuals, siły i warunki brzegowe.
4. Dopiero potem rampa klapki 0→+2°, a po stabilizacji ewentualny sweep do wyższych U.

## Przygotowany kandydat (NIE WYKONANY)
- C0SpeedDownSmoke.java skompilowany pod STAR 2606; kontrola statyczna 10/10 PASS.
- Start wyłącznie z C0_recovered_t065.sim i przy t=.650 s/iter 11560.
- 20 kroków dt=.002 s, 8 MPI; docelowa funkcja quintic 18→10 m/s przez .4 s. W ograniczonym teście osiągnąłby dopiero około 17.93152 m/s przy t=.690 s.
- Klapka stoi 0°, bez resetowania przepływu, stare progi bezpieczeństwa bez zmian; zapis historii U, qS, pABS, CL/CD, sił i Overset.
- Makro wymaga dodatkowej autoryzacji lokalnego mechanizmu uruchomieniowego. To NIE jest zatwierdzony launcher.

## Stan infrastruktury po kontroli
Próba integracji z istniejącym kontrolerem natrafiła na blokadę uprawnień przed startem. Nie próbowano jej obchodzić. Zmiany do trzech źródeł kontrolera i NIGHT_QUEUE.json zostały cofnięte z backupu. STATUS_CFD potwierdza: kontroler działa, solver STOPPED, active=null, HOLD po SPEED_SWEEP_PLUS2_20261103_SMOKE, accept_new_jobs=false, pending=[].

Nie używać START_SPEED_SWEEP_PLUS2.cmd do ponownego uruchomienia błędnego przypadku. Nie uruchamiać C0SpeedDownSmoke bez zintegrowanego, uprawnionego kontrolera i natywnego testu wznowienia.

## Źródła
F:\\ntnu\\flap_control\\hydro_validation_2606_20261102\\reports\\SPEED_SWEEP_PLUS2_20261103\\REPORT.json
F:\\ntnu\\flap_control\\hydro_validation_2606_20261102\\cases\\SP_C_split0_overset\\speed_plus2_20261103_102948\\fields_{readback,failure}.txt
F:\\ntnu\\flap_control\\hydro_validation_2606_20261102\\cases\\SP_C_split0_overset\\speed_plus2_20261103_102948\\pressure_zones.csv
