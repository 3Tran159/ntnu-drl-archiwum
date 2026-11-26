# Stokes V — plan nocnego zbioru trajektorii

**HOLD. Zgoda na nocne uruchomienie nie została udzielona.**

Wspólny model: STAR-CCM+ 2606, VOF woda–powietrze, SST k–ω, 44 442 komórki w jednej warstwie 20 mm, sealed NACA 66-012 MOD, zawias x/c=0,80 i zanurzenie 2 m. λ=10 m, H=0,50 m, U=18 m/s, Tₑ=0,454537 s. dt=1 ms jest wartością startową do potwierdzenia z CFL na siatce płata.

## Aktualizacja po diagnostyce H = 0,10 m

Status N01–N05: HOLD. Wcześniejsze czasy poniżej pochodzą z pustej domeny i nie wyznaczają budżetu dla płata. Pierwszy I1 na V2 wykonał jeden odrzucony krok w 3,01 s solvera (3,18 s z raportowaniem) przy dt = 25 µs, a rozruch STAR trwał 118,6 s. Okres 0,4555 s wymagałby przy tym dt około 18 221 kroków. Ekstrapolacja pojedynczego odrzuconego kroku nie kwalifikuje konfiguracji ani czasu nocnego. Mapowany start poprawił globalny CFL z 40,63 do 15,12, lecz bramka pABS zatrzymała pierwszy krok przy -5,89 MPa. I2 pozostał HOLD. Aktualny wynik do decyzji o zasobach: zero potwierdzonych cykli.

- EXPLORATORY: przejście twardych kontroli i wiarygodny przebieg diagnostyczny. Izolowany residual ciągłości oceniamy wraz z redukcją wewnątrz kroku, bilansem masy i zachowaniem VOF.
- ACCEPTED_FOR_SURROGATE: odrzucony rozruch, powtarzalne cykle, stałe definicje sił i efekt sterowania większy od rozrzutu między cyklami i wpływu kroku czasowego. Oznaczyć poziom fidelity i odłożyć całe trajektorie na test.
- VALIDATED: osobne porównania siatkowe i czasowe oraz niezależne odniesienie fizyczne. Ten status nie jest warunkiem krótkiej eksploracji.


**Recovery V2 CALM.** Rampa z jawnym tłem SST ukończyła 40 kroków diagnostycznych. Wznowienie zatrzymało się po 11 kolejnych krokach przy t = 5,1 ms i U zadanym 0,213 m/s, z pABS = -4,57 kPa w dwóch komórkach wody przy krawędzi natarcia. Brak CALM/FIXED przy U = 18 m/s. Etapy falowe pozostają HOLD.

**Recovery V3 C01.** C01 odczytano na kopii bez kroków solvera. Mapowany start Mini przy 18 m/s przeszedł kontrole początkowe. Po jednym kroku 50 µs uzyskano HOLD_CFL (31,74 przy krawędzi spływu), z dodatnim impulsem ciśnienia do 10,70 MPa. CALM/FIXED pozostaje HOLD.

**Czysty CALM, większe komórki.** Natywne jednorodne 18 m/s, płaski VOF i grawitacja, bez wymuszania objętościowego. Trzy próby kończą się na ciśnieniu po pierwszym kroku. Najgrubszy wariant 6 613 komórek i dt 14,5 ms spełnił limity CFL (20,10 globalnie, 0,483 na interfejsie), ale pABS,min wyniosło -12,76 kPa w domenie i -71,83 kPa na klapce. N01–N05 HOLD.

## Kolejność

| Run ID | Start i warunki | Faza | Plan minimum | Czas orientacyjny* |
|---|---|---:|---:|---:|
| N01_STOKES5_FIXED | Zweryfikowany checkpoint fixed H=0,50 m z ustalonym przebiegiem przy płacie | δ=0° | 1 cykl odrzucony + 3 powtarzalne | 88,8 min |
| N02_STOKES5_ACTIVE_P000 | Kopia zaakceptowanego checkpointu N01, ciągłość fazy i pól, rampa sterowania | 0° | 2 odrzucone + 3 powtarzalne | 111,0 min |
| N03_STOKES5_ACTIVE_P090 | Ta sama kopia N01, po PASS N02 | 90° | 2 + 3 | 111,0 min |
| N04_STOKES5_ACTIVE_P180 | Ta sama kopia N01, po PASS N03 | 180° | 2 + 3 | 111,0 min |
| N05_STOKES5_ACTIVE_P270 | Ta sama kopia N01, po PASS N04 | 270° | 2 + 3 | 111,0 min |

*Ekstrapolacja zmierzonego 2,93 s/krok pustej domeny, obejmuje raportowanie kroku. N01+N02 to około 3 h 20 min pracy krokowej, wszystkie pięć około 8 h 53 min. Rozruch procesu Mini na pustej domenie wyniósł około 119 s do gotowości serwera. Koszt zmiany konfiguracji, rozruchu przepływu i zapisu nie jest ujęty. Wyznaczyć osobne czasy WAVE/FIXED i WAVE/ACTIVE na siatce płata przed wyborem realistycznego zakresu nocy. Przebieg N01 ma pierwszeństwo, potem N02. Jeśli brakuje czasu na kompletny cykl analizy, nowy etap nie startuje.

## Definicja fazy i bramki

Dopasować podstawową harmoniczną η w lokalnej sondzie x=0,952 m po rozruchu. Faza θ przyjmuje 0° na grzbiecie podstawowej harmonicznej i maleje w czasie w przyjętym zapisie kx−ωₑt. Sterowanie δ=2° sin(θ+φ) z rampą S5 przy uruchamianiu. Zachować offset i czas odniesienia z N01. Fazy 0/90/180/270° odnoszą się do tej konwencji.

Przed N01 wymagane PASS propagacji pustej domeny, PASS aktywnego URANS, diagnostyczny PASS integracji przy H=0,10 m i bezpieczny pilot integracji H=0,50 m. Zaliczenie cykli wymaga trzech pełnych zachowanych okresów z dryfem średnich CL/CD/Mh ≤1% i amplitud ≤5%. Wymagane pABS >12,3392148 kPa, CFL interfejsu ≤0,5, względny błąd masy ≤1e−4 po rozruchu, dodatnie objętości, Face Validity ≥0,5, Cell Quality >0, pola SST z dala od limitów, poprawna kinematyka i stan wejściowy potwierdzony hashem. Przy współbieżnym W06 lokalny STOP Mini po przekroczeniu 15% spowolnienia według mediany siedmiu kroków.

ACCEPTED oznacza zweryfikowany checkpoint i pełny okresowy fragment bez rozruchu. DIAGNOSTIC obejmuje smoke, rampy oraz kompletne próbki bez potwierdzonej okresowości. FAILED/HOLD zachowuje dane i przyczynę, lecz blokuje następną gałąź. Podział treningowy wykonuje się po pełnych run_id i warunkach fali. Zachować odrębnie poziom sealed i ewentualny model ze szczeliną.

## Zapisy

Każdy run ma odrębny folder, kopię wejściowego checkpointu lub zweryfikowaną ścieżkę i SHA, checkpoint na koniec pełnych cykli i FINAL, monitor reszt oraz wspólne CSV/JSON. Ująć η w sondach, fazę lokalną, zadany i rzeczywisty kąt, dδ/dt w rad/s, CL/CD, Fx/Fz całkowite, odniesienie hydrostatyczne, Mh względem osi −Z STAR w Nm dla 20 mm, podpisaną moc płynu na klapce, pABS i położenia minimów, CFL, bilans masy, siatkę i koszt kroku. Porównania zachowują CL=(Fz−stały wypór odniesienia)/qS, CD=Fx/qS. Obliczyć dodatkowo wypór geometryczny ze zmierzonej wyporności, bez zastępowania nim istniejącej definicji CL.

