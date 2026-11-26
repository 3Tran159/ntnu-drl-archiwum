# Mini-URANS–VOF · bramka dzienna 04.11.2026 · Europe/Oslo

## Stan na teraz

| Element | Stan | Dowód |
|---|---|---|
| Pusta domena, natywna fala A = 0,05 m | DIAGNOSTIC | 20 ukończonych kroków 0,051–0,070 s z poprzedniej próby. 41 280 komórek, dt = 1 ms. Amplituda z dopasowania przestrzennego 49,64–49,86 mm. RMSE η 1,51 mm względem Airy’ego. Okres i odbicia nieweryfikowalne z tego okna. |
| Płat sealed w quasi-2D | HOLD, oczekuje na start | Istniejąca siatka 44 442 komórek, span 20 mm, zanurzenie zawiasu 2 m. Natywny import i pierwsze siły są bramką I0. |
| Kinematyka ±2° | Mapa ruchu PASS offline, STAR oczekuje | 41 położeń sprawdzonych. Zero ujemnych objętości. Najmniejsza objętość 1,99e-12 m³. Najmniejszy stosunek pola do stanu 0° = 0,875. Main i zewnętrzne granice nieruchome. |
| Batch | Kompilacja PASS, wykonanie oczekuje | Osobny serwer i klient na 127.0.0.1. Brak GUI i poleceń zewnętrznych do solvera co krok. PID, heartbeat, timeout, STOP po kroku, checkpoint i niezależny odczyt zapisanych pól. W06 zablokował preflight. |
| WAVE/ACTIVE i noc | HOLD | Brak zintegrowanego wyniku i rzeczywistych czasów modeli z płatem. Zero zaakceptowanych trajektorii. |

## Geometria i bramki

Zawias x/c = 0,80, dodatni kąt opuszcza krawędź spływu. Główny płat pozostaje nieruchomy. Uszczelniony model wymaga przejścia na pierwszych 35 mm klapki za zawiasem. Pozostała część klapki obraca się sztywno. Wyniki są osobną klasą geometrii SEALED względem szczeliny 2,5 mm. Natywny test mierzy położenia wierzchołków i kąt spływu. Akceptacja kinematyczna wymaga dodatnich objętości, Face Validity ≥0,5, Cell Quality >0, błędu kąta ≤0,08° i zgodności chmur wierzchołków z mapą w granicy 20 μm.

U = 18 m/s, λ = 10 m, Te = 0,455553 s, natywna fala First Order. Długość wymuszania 4 m, pochłaniania 8 m, zapis dodatkowych sond w strefie pochłaniania x = 20,5, 24 i 27 m. Do propagacji stosujemy sondy x = −6, −3, 0,952, 4, 8, 12 i 16 m poza strefami. Nie oceniono jeszcze tłumienia. Dopplerowska składowa o przeciwnej propagacji własnej również konwektuje w dół domeny. Współczynnik drugiej składowej jest miarą zanieczyszczenia propagacji i wymaga osobnej interpretacji przy płacie.

Przed oceną obowiązują pABS ≥ 12,3392148 kPa, CFL interfejsu ≤ 0,5, CFL globalny ≤25, względny bilans masy ≤1e-4 po 5 krokach rozruchu, brak komórek odwróconych i limitów SST. Kryteria fali z poprzedniej kolejki pozostają ustalone: amplituda ±10%, okres/częstotliwość ±2%, faza ±10°, reszta η RMS ≤15% amplitudy, składowa przeciwna ≤5%, stabilność amplitudy i średniej η pomiędzy cyklami ≤2% amplitudy. Dla sił drift średniej ≤1% i amplitudy ≤5% w trzech pełnych cyklach po rozruchu. Próg końcowego continuity 0,01 pozostaje osobno raportowany. Jeśli tylko on nie przejdzie, przypadek zostaje do oceny na podstawie redukcji w kroku, zamknięcia masy oraz porównania z dt/2 przy tej samej fazie, bez automatycznego zaliczenia ani diagnozy błędu fizyki.

Dotychczasowa pusta domena: pABS min 101,302 kPa, CFL interfejsu 0,155, maksymalny względny bilans masy po 5 krokach 6,10e-7. Końcowy continuity 0,0190–0,0603, oddzielnie od bilansu. Wyniki wyłącznie diagnostyczne.

## Wydajność i noc

Koszt pustej domeny: po odrzuceniu pięciu kroków średnio 2,483 s/krok, mediana 2,226, maksimum 3,557. Przeliczenie dla dt = 1 ms daje 18,9 / 56,6 / 94,3 min dla 1 / 3 / 5 okresów pracy solvera. To nie są prognozy dla płata ani czasy obejmujące start, raportowanie, zapis i rozruch. W06 ma pierwszeństwo. Nowa kampania nie ma pomiaru wydajności ani wpływu na inne obliczenia.

| run_id | Zależność | Przebieg | Plan minimalny | Stan |
|---|---|---|---|---|
| N01 | PASS I1, I2 i odczyt checkpointu | WAVE/FIXED, δ=0°, λ=10 m, A=0,25 m, U=18 m/s | 1 cykl odrzucony + 3 zatrzymane | HOLD |
| N02 | N01 PASS | ±2°, 0° względem dopasowanej lokalnej fazy η | 2 cykle rozruchu z rampą S5 + 3 zatrzymane | HOLD |
| N03 | N02 PASS | ±2°, +90°, ten sam checkpoint N01 | 2 cykle rozruchu + 3 zatrzymane | HOLD |
| N04 | Wymaga osobnej kwalifikacji i czasu | Ograniczone wieloczęstotliwościowe wymuszenie | Brak w launcherze | Opcjonalne |

Prognoza nocna wymaga osobno zmierzonego czasu kroku fixed i active, kosztu startu i zapisu, oraz okna pozostałego do 06:50 Oslo. Wniosek na teraz: 0 potwierdzonych okresów nocnych możliwych do zatwierdzenia. Przyspieszenie z testu pustego zbiornika nie może zastąpić pomiarów modeli z płatem.

Launcher `START_NIGHT.cmd` wymaga `NIGHT_READY.json` z dowodami i sumami SHA oraz `NIGHT_APPROVAL_20261104.json` po decyzji użytkownika. Plan nie tworzy tych plików automatycznie. `STATUS_MINI.cmd` czyta stan, a `STOP_MINI.cmd` prosi o bezpieczne zatrzymanie własnej kolejki. Pliki wynikowe to SIM, historie sił, η, ruchu, jakości, residuals i czasu, CSV z metadanymi, oraz nakładki cykli po spełnieniu bramek. Podpisana moc Mh·δdot opisuje przepływ mocy od płynu do klapki przy osi zgodnej z δ, bez interpretacji jako pobór elektryczny.

Najbliższe pytanie naukowe po odblokowaniu ruchu: czy przy tej samej fali zmiana fazy ±2° istotnie zmienia harmoniczne CL i Mh oraz średnią podpisaną moc klapki przy zachowanym marginesie pABS?


## Lokalna kolejka dzienna

Kontroler oczekuje na wolne zasoby maksymalnie przez dwie godziny od uruchomienia. Wykonuje jedynie ograniczone testy dzienne, po ponownym sprawdzeniu procesów i kolejki niezależnej. Schemat: A05 40 kroków → ponowny odczyt pól checkpointu. Niezależna gałąź: natywna kinematyka ±2° → 40 kroków jednofazowego SST URANS przy U=10 m/s. Niższa prędkość w gałęzi jednofazowej służy wyłącznie sprawdzeniu działania ruchu z przepływem. I0 spokojny VOF fixed przy U=18 m/s jest osobną bramką. Po pozytywnych bramkach możliwe są krótkie diagnostyki I1 i I2 przy A=0,05 m. I1 jest inicjalizowany globalną falą na siatce płata, żeby krótki test objął falę przy płacie. I2 kontynuuje pola i czas I1, z łagodnym rozruchem klapki. Pełne okresy A=0,05 i 0,25 pozostają odrębnymi etapami walidacji propagacji. Dzienna kolejka nie daje uprawnień nocnej.

Dodatkowa kontrola offline ruchu: przy wszystkich 41 położeniach każdy narożnik elementu zachował dodatni dyskretny jakobian. Najmniejsza wartość 1,9905e-10 m². STAR musi potwierdzić swoje natywne wskaźniki na tej samej siatce.

Testy launcherów ograniczyły się do kompilacji, odczytu statusu i odmowy preflight przy W06. Pełna niezawodność procesu batch, ponowny odczyt nowego rozwiązania i poprawność gałęzi nocnej pozostają do sprawdzenia w wykonaniu.
