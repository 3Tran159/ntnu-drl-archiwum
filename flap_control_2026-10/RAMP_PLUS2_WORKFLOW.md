# Rampa C0 → +2° — gotowy workflow lokalny

Identyfikator: `RAMP_C0_PLUS2_S5_20261103`.
Stan 03.11.2026: **krótki rozruch PASS; kontynuacja READY, jeszcze nieuruchomiona**.

## Uruchomienie

W PowerShell:

```powershell
& "F:\ntnu\flap_control\START_RAMP_PLUS2.cmd"
```

Polecenie uruchamia wyłącznie zatwierdzoną kontynuację rampy. Korzysta z istniejącego lokalnego kontrolera; nie tworzy drugiego. Nie uruchamia starego skokowego +2°.

Możesz też dwukrotnie kliknąć `START_RAMP_PLUS2.cmd`. Okno pomocnicze pozostaje ukryte.

Status:

```powershell
& "F:\ntnu\flap_control\STATUS_CFD.cmd"
```

Bezpieczny stop:

```powershell
& "F:\ntnu\flap_control\STOP_CFD.cmd"
```

STOP jest odczytywany między krokami. Makro zapisuje `paused_checkpoint.sim`, a kontroler czeka na zakończenie zapisu i procesu. Nie wyłączaj komputera przed potwierdzeniem zakończenia własnych procesów i zapisu. Inne kampanie, w tym W04, mogą nadal pracować.

Po zwykłej ręcznej pauzie ponownie użyj `START_RAMP_PLUS2.cmd`: tworzy zadanie kontynuacji z potwierdzonego checkpointu pauzy, zachowując czas i pola. Błąd fizyczny, zmienione makro lub blokada bezpieczeństwa wymagają oceny; polecenie ich nie zwalnia. Jeśli eksperyment zakończył się stabilizacją albo limitem, kolejne wywołanie nie powtarza obliczeń.

## Co zostało sprawdzone

- Kompilacja `RampPlus2Smoke.java` i `RampPlus2Run.java` z bibliotekami STAR 2606.
- Monotoniczność wielomianu, zakres 0–2°, zerowe prędkość i przyspieszenie na obu końcach rampy.
- Rzeczywisty rozruch: pięć kroków URANS SST, 8 MPI, bez GPU, od t=0,650 do 0,660 s. Przepływ i turbulencja aktywne.
- Natywny kąt i centroid klapki zgodne z funkcją; błąd centroidu ≤4,45e−16 m.
- Pełna łączność 333 939 komórek Overset kontrolowana przy każdym kroku, bez błędów i trudnej interpolacji; objętości dodatnie.
- Najmniejsze ciśnienie absolutne w teście:30 065,17 Pa. Największy względny bilans masy:2,53e−9. Liczby ograniczanych komórek k i ω:0.
- Natywny zapis checkpointu oraz SHA-256 potwierdzone. Komenda przygotowania przeszła sprawdzenie `--check` bez uruchamiania kontynuacji.
- Testy autoryzacji potwierdziły: stary FAIL pozostaje zablokowany; nowy eksperyment ma osobną zgodę; nowa awaria rampy blokuje jej kontynuację.

**Pełnej rampy i utrzymania +2° jeszcze nie przeliczono.** W krótkim teście osiągnięto tylko0,00231625° — rozruch potwierdza ciągłość i działanie mechanizmu, nie bezpieczeństwo hydrodynamiczne całej rampy. Wcześniejszy test kinematyki ±5° pozostaje osobnym dowodem mechanicznym.

## Prawo ruchu i granice eksperymentu

Dla u=(t−0,650)/0,2 ograniczonego do [0,1]:

δ(t)=2°·(10u³−15u⁴+6u⁵).

dδ/dt=10°/s·(30u²−60u³+30u⁴).

Rampa od0,650 do0,850s; później stałe+2°. Maksymalna prędkość18,75°/s. Początek C0 zachowuje pola i geometrię; nie ma skokowego przestawienia klapki, resetu czasu ani remeshingu.

Kontynuacja zaczyna się z ukończonego krótkiego testu przy0,660s/iteracji11760. To ten sam eksperyment rozpoczęty z C0t0,650.

Ustawienia:8MPI,bez GPU,URANS SST,dt0,002s,40 iteracji wewnętrznych,warunki i numeryka C0. Maksymalny czas fizyczny1,250s; maksymalnie295 nowych kroków od checkpointu smoke. Limit czasu wykonania zadania2h. Kontroler może zatrzymać je wcześniej na bramce bezpieczeństwa. Nie zaplanowano następnych wychyleń ani fal.

## Stabilizacja i zabezpieczenia

Po zakończeniu rampy: średnie CL,CD,Mh w oknach25 kroków. Warunek kandydata stabilnego: dwie kolejne pozytywne oceny, dryf średnich <0,5%, rozstęp w ostatnim oknie <1%, co najmniej75 próbek po rampie oraz redukcja residuals ostatniego kroku do ≤1% wartości początkowej. Y-momentum na poziomie błędów zaokrągleń jest jawnie wyłączone z testu ilorazu. Pozostałe residuals są zachowane.

Warunki te oznaczają `ramp_stable_candidate`, a nie pełną walidację ilościową. Dane pozostają niezatwierdzone do DRL i analizy energetycznej bez oceny naukowej.

Progi pozostają niezmienione: p_abs>12 339,2148Pa, względny bilans masy<1e−4, zero ograniczanych komórek k/ω, lepkość turbulentna poniżej99999, brak błędów Overset/trudnej interpolacji i ujemnych objętości. Zachowano pozostałe kontrole jakości, prędkości i ruchu. Błąd powoduje zapis diagnostyczny i HOLD, bez kolejnego zadania.

Checkpointy co50 kroków globalnych, po krótkim teście oraz na końcu/pauzie/błędzie. Każde uruchomienie ma osobny katalog; poprzednie checkpointy pozostają zachowane. Historia δ,dδ/dt,Fx,Fz,CL,CD,Mh,ciśnienia i parametrów siatki zapisywana jest po każdym kroku. Pełne audyty Overset znajdują się także w logu; pliki `latest` opisują najnowszy krok. Residuals, pola i raporty wykonania są eksportowane automatycznie.

## Bez Work

**Tak — zatwierdzony przebieg wykonuje lokalny kontroler i natywne makro. Aktywna sesja Work nie jest potrzebna.** Wymagane są działający, nieuśpiony ThinkPad, dostępna licencja i zasoby. Ustawień zasilania ani autostartu Windows nie zmieniono.

Watchdog nie zabija procesu podczas zapisu ani nie naprawia samodzielnie awarii solvera. Po błędzie fizycznym potrzebna będzie ocena. Nie testowano przerwania zasilania ani natywnego wznowienia po ręcznej pauzie tej nowej rampy; jej mechanizm zapisu/odtworzenia jest przygotowany, lecz ten scenariusz nie był wykonywany na solverze.

## Źródła i dowody

Katalog: `F:\ntnu\flap_control\hydro_validation_2606_20261102`

Checkpoint startowy kontynuacji:
`cases\SP_C_split0_overset\ramp_plus2_20261103_093316\checkpoint.sim`

SHA-256: `7129bdc3f60e8b6a0d70156a7d7094fb1c5e930df85ec9dd5035f17fe2bfc68c`.

Dowody: `audit\RAMP_SMOKE_REVIEW_20261103.json`, `audit\RAMP_KINEMATIC_UNIT_TEST.json`, `audit\RAMP_GATE_TESTS_20261103.txt`, `audit\RAMP_PLUS2_EXPLICIT_APPROVAL_20261103.json`.

Stan: `NIGHT_STATUS.json`, `NIGHT_QUEUE_STATE.json`, `NIGHT_DASHBOARD.html`; raporty wykonania:`reports\automatic`.

Stary `plus2_benchmark_8cpu_20261103` nadal ma status FAILED. Nie zwolniono jego blokady ani nie zmieniono progu ciśnienia. Nowa zgoda jest przypisana wyłącznie do osobnego eksperymentu rampy.
