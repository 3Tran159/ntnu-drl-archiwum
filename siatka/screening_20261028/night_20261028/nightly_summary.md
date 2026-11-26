# Nocne próby CFD — automatyczne podsumowanie

Aktualizacja: 2026-10-29T06:20:59.940031+00:00

Cel: rozruch, stabilność i koszt obliczeń. Wyniki nie potwierdzają zbieżności sił ani niezależności od siatki.

Przypadki z ukończonym krokiem: 4/4. Wspólny czas fizyczny dostępnych prób: 0.0002 s.

| Przypadek | Status | Kroki | Czas fizyczny [s] | Min. wolny RAM [GiB] | Śr. czas kroku [s] |
|---|---|---:|---:|---:|---:|
| D001 | completed | 20 | 0.0002 | 15.477466583251953 | 370.12849985 |
| D002 | completed | 21 | 0.00021 | 17.543537139892578 | 345.7340230476191 |
| D003 | completed | 21 | 0.00021 | 16.228103637695312 | 355.6026999666667 |
| D004 | completed | 22 | 0.00022 | 18.371490478515625 | 328.40905958636364 |

## Odczyty przy wspólnym czasie

| Przypadek | t [s] | Fx_half [N] | Fz_half [N] | max CFL | Śr. y+ |
|---|---:|---:|---:|---:|---:|
| D001 | 0.0002 | 20058.778984737408 | 127984.95709167476 | 14.267768223091162 | 86.20355490924149 |
| D002 | 0.0002 | 20872.522510772906 | 128868.3344852041 | 14.266083943388757 | 86.19272419576613 |
| D003 | 0.0002 | 20169.618314205127 | 128831.944832058 | 31.867074415001547 | 86.19893610193999 |
| D004 | 0.0002 | 21148.47644089484 | 127882.90647441086 | 38.98633043955089 | 86.19124044708097 |

Porównanie obejmuje tylko próby z zapisanym postępem. Jeśli nie wszystkie cztery mają postęp, nie jest to pełne porównanie. Sprawdź logi residuali, lokalne y+, CFL i checkpointy. Pokrycie pełnymi pryzmami nadal wymaga oceny lokalnej.
