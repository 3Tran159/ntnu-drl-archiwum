# Mini-URANS–VOF · Fifth Order · plan propagacji

Model docelowy używa natywnego `FifthOrderVofWave` w STAR 2606. Metoda VOF, grawitacja, SST, siatki z jedną warstwą 20 mm i zanurzenie zawiasu 2 m pochodzą z dotychczasowego Mini. First Order pozostaje referencją archiwalną.

- H = 0,50 m, λ = 10 m, U = 18 m/s. W STAR +X to kierunek prądu i propagacji. W układzie nieruchomego płata ruch statku byłby w −X względem wody, więc fala nadchodzi od strony wlotu. Pion to +Y STAR. Woda ma głębokość 12,0213 m od średniego lustra do dna.
- kd = 7,553, H/λ = 0,05, kH/2 = 0,1571 i Ursell Hλ²/d³ = 0,0288. Zakres głębokiej wody mieści się w obszarze zastosowania Stokesa V. Natywny i teoretyczny okres spotkaniowy odczytany dla tych ustawień to 0,454537 s. Celerity względem wody ≈4,0004 m/s, względem płata ≈22,0004 m/s.
- Na pasie VOF Δx = 0,125 m, Δy = 0,0125 m, dt = 1 ms. Harmoniczne od 1 do 5 mają odpowiednio 80 / 40 / 26,7 / 20 / 16 komórek na własną długość fali oraz 455 / 227 / 152 / 114 / 91 kroków na własny okres. Oczekiwane amplitudy w głębokiej wodzie są w przybliżeniu 247,5 / 20,0 / 2,43 / 0,323 / 0,050 mm. H3–H5 są poniżej pionowego rozmiaru komórki. Odtwarzanie H4–H5 wymaga osobnej kontroli czułości siatki, nawet jeśli VOF zachowuje kształt H1–H2.
- Plan długiej propagacji od stabilnego checkpointu: 1 okres na przejścia po starcie + 3 zachowane okresy, co najmniej 1,82 s czasu fizycznego przy 1 ms. Sondy −6, −3, 0,952, 4, 8, 12 i 16 m służą do dopasowania podstawy i harmonicznych. Sondy 20,5, 24 i 27 m sprawdzają tłumienie. W fazie raportu analizujemy rzeczywisty okres, fazę, H, H1, H2, rozpad H3–H5 i dopplerowską składową przeciwną w układzie wody.
- Bramki przed analizą: H i H1 w ±10%, okres ±2%, faza ±10°, odchylenie η RMS ≤0,0375 m, odchylenie zespolonej H2 ≤ większej z 5 mm i 25% wartości natywnej, dryf H1 ≤5 mm między cyklami, przeciwna składowa do 5%. Zachowujemy bieżące progi pABS, CFL, masy i SST. Residual 0,01 rozpatrujemy niezależnie od fizycznych bramek, z porównaniem wrażliwości na dt, jeśli pozostaje jedynym odchyleniem.

Źródła: lokalny User Guide STAR-CCM+ 2606, VOF Waves, GUID-47BE8633-F9D4-42BC-8880-66D992B053D7 oraz Fenton 1985, https://johndfenton.com/Papers/Fenton85d-A-fifth-order-Stokes-theory-for-steady-waves.pdf.

