# Mini-URANS 2D z klapką
## Domknięcie cyklu, szczelina 2,5 mm i projekt warstwy przyściennej

### Co pokazuje zarejestrowany cykl

| Stan | t [s] | Zmierzone δ [°] | CL | CD |
|---|---:|---:|---:|---:|
| Pierwsza próbka URANS | 0,001 | −0,00016 | 0,30798 | 0,01163 |
| Przejście przez zero | 0,100 | 0 | 0,30909 | 0,01195 |
| Powrót do zera | 0,200 | 0 | 0,33871 | 0,01111 |

Kąt się domknął, lecz CL na końcu jest wyższe o 0,03072, czyli 9,98% względem pierwszej próbki. Tuż przed startem URANS ostatnia próbka ustalania przepływu dawała CL = 0,28610. W jej pobliżu wciąż widać dryf CL i CD. Pierwszy cykl obejmuje więc odpowiedź na ruch oraz przejście ze stanu bazowego do przebiegu nieustalonego. Zależność CL od kierunku i historii ruchu jest możliwa fizycznie, a jeden cykl nie pozwala oddzielić jej od rozruchu i potwierdzić powtarzalnej pętli. Po ustaleniu warunków porównać kolejne pełne cykle na tej samej fazie i odcinkach ruchu, w tym CL, CD i Mh przy powrocie do 0°. [Dane solvera](single_phase.csv)

### Warstwy przyścienne

Przebieg 13 597 komórek miał SST k–ω i All y+ Wall Treatment. Siatka miała 205 odcinków ściany płata i klapki, bez dedykowanych warstw przyściennych. W prawdziwym 2D odpowiednikiem pryzmatów są pasy czworokątów przy ścianie.

Przy U = 18 m/s, c = 1,19 m i ν = 10⁻⁶ m²/s uzyskujemy Re = 2,142×10⁷. Wstępny szacunek z linii ITTC-1957 daje Cf = 0,00264 i uτ ≈ 0,654 m/s. Z y+ = uτ y/ν wynika:

| Projektowe y+ | Odległość środka komórki od ściany [mm] | Przybliżona pełna wysokość pierwszej warstwy [mm] |
|---:|---:|---:|
| 30 | 0,046 | 0,092 |
| 50 | 0,076 | 0,153 |
| 60 | 0,092 | 0,184 |
| 70 | 0,107 | 0,214 |
| 100 | 0,153 | 0,306 |

Przybliżenie wysokości jako 2y dotyczy prawie regularnej pierwszej warstwy. Na zewnętrznych powierzchniach zacząć od 0,15–0,21 mm, 8–10 warstw i wzrostu około 1,18. Dla pierwszej warstwy 0,184 mm łączna grubość wynosi około 2,8–4,3 mm. Pełne pasy po obu stronach nie zmieszczą się w szczelinie. Lokalny punkt startowy to po trzy warstwy o pierwszej wysokości 0,15–0,18 mm, wzrost 1,15 oraz 3–4 komórki w rdzeniu. W szczelinie projektowe y+ zależy od lokalnego ścinania i wymaga osobnej oceny. Raportować rozkład ważony długością ściany dla płata, klapki i szczeliny przy 0° oraz ±2°. W strefach stagnacji, separacji i silnego gradientu ciśnienia interpretować wyniki wall functions ostrożnie. [ITTC 7.5-03-02-03, sekcje 2.3.5 i 3.2](https://ittc.info/media/11958/75-03-02-03.pdf)

### Szczelina i budżet siatki

Na zapisanych obrysach rzeczywistej klapki obrót o ±2° sprawdzony w 41 położeniach daje minimalny prześwit około 2,497 mm. Jest to odległość między konturami na próbkowanej geometrii. Ocena nie obejmuje jakości siatki w ruchu.

Przy zachowaniu zewnętrznej domeny i lokalnej rafinacji orientacyjne budżety prawdziwego 2D to:

| Wariant | Budżet komórek | Status |
|---|---:|---|
| Sealed z warstwami | 15–17 tys. | Szacunek z ok. 1,6–2,1 tys. komórek w pasach przy 205 odcinkach ściany, przed zmianą przejścia do rdzenia |
| Szczelina 2,5 mm, osobne statyczne siatki | 16–22 tys. | Budżet projektowy z lokalnym zagęszczeniem prześwitu i krótkiego śladu |
| Szczelina 2,5 mm, klapka ruchoma | 18–30 tys. | Budżet projektowy zależny od deformacji albo nakładania siatek |

Wcześniejsze statyczne siatki ze szczeliną miały 89 750 i 90 198 komórek. Zastosowano w nich pierwszą warstwę 20 µm oraz szerzej rozciągnięte zagęszczenie wokół płata i szczeliny. Te liczby opisują poprzednie warianty. Nowe budżety trzeba zweryfikować po wygenerowaniu siatek. Porównanie wpływu szczeliny wymaga zgodnego zewnętrznego konturu w obu wariantach, w tym spływu i rejonu zawiasu. Obecny sealed z tępym spływem 6 mm pozostaje referencją kinematyczną.

### Krok czasowy

Obecny sealed osiągnął globalny CFL 4,62 przy dt = 1 ms. Dla szczeliny użyć wstępnej skali C ≈ |u − wsiatki| Δt / ℓ w kierunku lokalnego przepływu, a decyzję podjąć z natywnego CFL i porównania odpowiedzi. Nominalne 2,5 mm prześwitu i wysokość pierwszej warstwy same nie wyznaczają ℓ. Dla przykładowej długości komórki 0,50 mm przy 1 ms otrzymujemy C ≈ 10, 20 i 36 przy prędkości względnej odpowiednio 5, 10 i 18 m/s. Próg 25 w dotychczasowym Mini jest bramką bezpieczeństwa projektu. Zbieżność czasową trzeba ocenić oddzielnie.

Najkrótsza sekwencja kontrolna:

1. Wariant sealed z warstwami, kontrola y+ i zachowania dotychczasowego kroku 1 ms.
2. Statyczne 0°, −2° i +2° ze szczeliną, kontrola geometrii, strugi w szczelinie, pABS i sił. 
3. Dopiero po sprawdzeniu siatki w pełnym ruchu porównać 0,5 i 1 ms w tych samych chwilach lub fazach. Zachować dotychczasowy próg pABS 12,339 kPa, CFL 25 i bramki siatki oraz bilansu masy. Sprawdzić rozbieżność amplitud, faz i średnich CL, CD, Mh oraz przepływu przez szczelinę. Wariant 0,25 ms uruchamiać, jeśli 0,5 ms nie daje wiarygodnego odniesienia albo potrzebny jest punkt rozstrzygający.

Wniosek projektowy. Budżet kilkunastu do kilkudziesięciu tysięcy komórek jest możliwy do sprawdzenia w 2D. Krok 1 ms jest kandydatem. O jego użyteczności zdecydują pomiary lokalnej strugi i test wrażliwości czasowej. W ramach tej oceny nie uruchomiono nowego solvera.

