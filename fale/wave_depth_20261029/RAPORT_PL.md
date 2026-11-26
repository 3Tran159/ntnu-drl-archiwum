# NTNU | Wave-depth and domain screening | 29.10.2026

## Zakres

Odrębny zestaw regularnych fal VOF (bez płata, bez kadłuba i wsporników):
- Fale lambda 20 i 30 m, H 0.50 m, prąd 18 m/s w +X (ruch fali w +X).
- Głębokości wody h=12,16,24 m, referencja: 24 m.
- Domena długości 3 lambda i 4 lambda, porównanie dla h16.
- dt 0.001, 0.002 (bazowe) i 0.004 s przy lambda20, h16, 3 lambda.
- Układ współrzędnych: z=+2 m linia wody, dno z=2-h, góra z=12. Cienka 3D domena y=20..20.8 m, poza istniejącą geometrią płata.
- Siatka Trimmer, HF_wave: dx=0.2048 m, dy=0.4096 m, dz=0.0256 m, drugi rząd czasowy. HF_fine wyłączone w testach bez płata.
- Wlot: zadane pole VOF fali pierwszego rzędu, region VOF Wave Forcing/Damping, zakresy 1 lambda przy wlocie i wylocie.

## Rzeczywiste wykonanie

Wszystkie 10 wariantów wygenerowano i zapisano jako `<ID>/built.sim`.
Każdy ma `<ID>/mesh_report.txt`, `verified_setup.txt`, `SUCCESS.txt`. Liczba komórek: zobacz `status.csv`.
Makro sprawdza negative volume / unclosed / degenerated cells; w wykonanych raportach brak błędów.
Modele generowano w 2602 build 21.02.007 i nie wykonano w nich żadnego kroku obliczeniowego.

**Istotny błąd STAR-CCM+ 2602 w FirstOrderVofWave:** pierwsze 10 siatek w folderze głównym zapisano, ale ich inicjalizacja kończy się wewnętrznym błędem:
`Schama FirstOrderVofWave declares property on line 124 without the corresponding define_property in the schema`.
Warianty bez forcing/damping oraz z polami płaskiej wody dały ten sam błąd. Szczegóły w `W20_H16_X3/smoke.log` i `diagnose_*.log`.

**Sprawdzone obejście:** wszystkie 10 przypadków przebudowano od czystego źródła z `FifthOrderVofWave` i zapisano po poprawnej inicjalizacji. Są w `fifth_cases/<case>/built.sim`; `fifth_cases/batch_build.log` kończy się kodem 0. **Test rzeczywisty W20_H16_X3:** 8 kroków, Δt=0.002 s, max CFL do 0.217, max prędkość do 18.48 m/s, zapisano `gauge_history.csv` i `gauge_checkpoint.sim` (exit code 0). To tylko 0.016 s, nie walidacja propagacji fali; należy dalej policzyć pełne okresy spotkaniowe. Monitory starego płata Fx/Fz zwracają NaN, gdyż w domenie nie ma płata; nie oznacza to awarii VOF. Porównania z `analytic_summary.csv` (teoria liniowa) traktować jako przybliżenie, bo V rząd Stokesa zawiera dodatkowe harmoniczne.

## Uzasadnienie dt

Dla lambda20, h16, prędkość fazowa względem wody c = 5.5878 m/s. Fala mijana przez nieruchomy płat w układzie z prądem U=18 m/s ma T_e = lambda/(U+c) = 0.84790 s.
Przy dt=0.002 s: 424 kroki/okres spotkaniowy; nominalny CFLx=18*0.002/0.2048 = 0.176.
Warianty dt 0.001/0.004 s dają 848/212 kroków/okres, nominalny CFLx ~0.088/0.352.
Dla lambda30 h16 T_e = 1.20795 s, czyli 604 kroki/okres przy 0.002 s.
Nominalny CFLx nie zastępuje `max Courant Number` obliczonego w STAR; wartość zaakceptować dopiero po rzeczywistym rozruchu.

## Co porównać po naprawie

1. Pomiary eta(t) w x=0 oraz x=lambda/2, odtworzone z całki z alpha_water na przekroju x=const.
2. Analityczna eta(t)=H/2*cos(k*x-(sqrt(g*k*tanh(k*h))+k*U)*t), `theoretical_wave_probes.csv`.
3. Błąd amplitudy i przesunięcia fazowego, po rozruchu i minimum kilku okresach spotkaniowych; kontrola odbić od wylotu.
4. Wpływ h przy stałych lambda,H,U, porównywanie z prawidłową dyspersją skończonej głębokości.
5. Wpływ długości domeny 3λ→4λ na eta(t) w x=0, weryfikacja stref tłumienia.
6. Niezależność czasowa 1/2/4 ms przy niezmienionej siatce.
7. Dopiero po potwierdzeniu propagacji bez płata przenieść ustawienia do modelu z płatem i porównać Fx,Fz i harmoniki.

## Pliki

- `cases.csv`, `cases.json`: konfiguracje wejściowe
- `analytic_summary.csv`: dyspersja, okresy spotkaniowe, lokalny ruch orbitalny, nominalne CFL
- `theoretical_wave_probes.csv`: analityczne przebiegi eta, u, w dla wszystkich przypadków
- `batch_build.log`: log meshowania 10 przypadków
- `WaveTankBatch.java`: generator modeli
- `WaveTankSmoke.java`: test 8 kroków
- `README.md`: szczegóły techniczne po angielsku

Źródła do konsultacji: Siemens VOF Waves Guidelines 2406; dokumentacja modelu VOF Waves; procedury ITTC weryfikacji fal.
