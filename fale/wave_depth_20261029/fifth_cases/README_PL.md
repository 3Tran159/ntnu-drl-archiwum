# NTNU | 10 gotowych modeli rozruchowych fal Stokesa V rzędu

Katalog: `F:\ntnu\wave_depth_20261029\fifth_cases`

**STATUS: zbudowano, wygenerowano siatkę, poprawnie zainicjalizowano STAR-CCM+ 2602.**
Wszystkie modele powstały z osobnej czystej kopii i mają zerowy czas fizyczny.
**Nie oznacza to jeszcze, że fala została poprawnie przeliczona przez wiele okresów.**

W każdym folderze przypadku:
- `built.sim` : siatka, modele VOF, FifthOrderVofWave, forcing/damping, drugi rząd czasowy, poprawna inicjalizacja;
- `mesh_report.txt` : informacje o jakości siatki;
- `verified_setup.txt` : λ, h, długość i szerokość domeny, dt, liczba komórek;
- `SUCCESS.txt` : potwierdzenie zapisu.

Wariacje h: 12, 16, 24m przy λ20 i λ30 m.
Wariacje długości: 3λ oraz 4λ dla h16 m.
Wariacje dt: 0.001, 0.002, 0.004 s przy λ20/h16/3λ.
W każdym przypadku H=0.5 m, +18 m/s current, waterline z=+2m, dno z=2-h, slab y=20..20.8m.
Siatka HF_wave w pobliżu wolnej powierzchni: dx~0.2048m, dy~0.4096m, dz~0.0256m.
Przed pełną kampanią wykonaj test gauge w folderze referencyjnym, nie uruchamiaj wszystkich modeli naraz na przeciążonej stacji.

Uwaga: poprzednie 10 przypadków w katalogu nadrzędnym korzystało z `FirstOrderVofWave` i z powodu błędu schematu STAR nie przechodziło inicjalizacji. Piąty rząd jest obejściem, nie dokładnie tą samą teorią. Referencje `analytic_summary.csv` i `theoretical_wave_probes.csv` w folderze nadrzędnym bazują na przybliżeniu liniowym, używaj ich weryfikacyjnie z uwzględnieniem wyższych harmonicznych fali Stokesa V rzędu.

Skrypty:
- `..\WaveTankBatchFifth.java` : generator 10 przypadków;
- `..\WaveGaugeRun.java` : dwie sondy poziomu wody, maks. CFL, prędkość maks.;
- `..\gauge_runner.py` : bezpieczny, odrębny test kilku kroków na wybranym przypadku.

Krótki test sond: **W20_H16_X3 ukończył 8 rzeczywistych kroków Δt=0.002 s**; pliki `gauge.log`, `gauge_history.csv`, `GAUGE_SMOKE_OK.txt`, `gauge_checkpoint.sim`. Max CFL około 0.217; vmax około 18.48 m/s. Jest to test rozruchu, **nie walidacja propagacji ani amplitudy**. Sonda w x=λ/2 nie osiągnęła jeszcze przebiegu fali po 0.016 s, co wymaga weryfikacji podczas kilku okresów spotkaniowych.
Uwaga: odziedziczone monitory sił na pustym płacie (`Fx_half`, `Fz_half`) generują `NaN` w logu, ale solver oraz sondy falowe wykonały wszystkie kroki. W zaktualizowanym `WaveGaugeRun.java` wyłączono automatyczne nagrywanie odziedziczonej historii rozwiązania. Przed długim testem wyłączyć również oba stare monitory sił.
Kolejny etap: test kilku lub więcej okresów spotkaniowych, porównanie amplitudy/fazy i odbić, dopiero potem wybór głębokości.
