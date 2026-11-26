# Stokes V · wynik pierwszego testu i ukierunkowana naprawa

## W06 i licencja

W06 ma jeden proces MPI i GPU. W pomiarze bazowym native rank zużywał 0,895 rdzenia, a klient 0,311, razem 1,21 rdzenia CPU. Suma ich pamięci roboczych około 4,0 GB, pamięć wolna systemu 42,05 GiB. Oba procesy mają affinity 12598275, poza E4. GPU zarejestrowało PID W06, globalne wykorzystanie 42–62% w próbkach, użycie VRAM 2767 MiB. Narzędzie nie udostępniało przydziału VRAM per proces w tym trybie Windows.

W06 uruchomiono z PoD i jedną rangą GPU. Mini 2606 pobrał oddzielne ccmppower przy aktywnym W06. Mini miał jedną rangę CPU, maskę E4 = 16 i bez GPU, osobne procesy, port 48863 i katalog. W06 nie modyfikowano. Dotychczasowa blokada była polityką kolejki. Nie zaobserwowano twardego konfliktu licencji ani zasobów w zmierzonym oknie.

Baseline 60 kroków W06: mediana 1,65784 s, średnia 1,66406 s. Podczas rozwiązania Mini, z 24 odstępów W06 pomiędzy wskazaniami kroku 740 i 764, mediana 1,73062 s (+4,39%), średnia 1,69904 s (+2,11%). Najwyższa obserwowana mediana ruchoma 7 kroków +9,43%. Twardy STOP Mini pozostaje 15%, co działa po zamknięciu bieżącego kroku. Zasoby przeszły obserwację krótkiego okna. Pełna próba fizyczna zatrzymała się wcześniej.

## Mechanizm HOLD

Natywny FifthOrderVofWave dał odczyt Te=0,4545374193 s po kroku i faktycznie wykonał 14 kroków przy dt=1 ms. Przy t=0,014 s sześć komórek powietrza w trzech powtarzalnych grupach oddalonych o λ, przy x≈−1,5625, 8,4375 i 18,4375 m, doszło do μt/μ=100000. Minimum ω=1,47e−10 s⁻¹. W polu startowym, w miejscu pierwszej grupy, pionowa prędkość sąsiednich komórek zmienia się z −0,554 m/s w komórce częściowo zalanej do 0 m/s w powietrzu na Δy=12,5 mm. Po 14 krokach do powietrza weszła strefa k rzędu 1–5 m²/s. Wraz z powtarzalnością przestrzenną stanowi to dowód, że problem jest związany z warstwą interfejsu przy globalnej inicjalizacji pełnej fali. Czy narasta również po płynnym rozruchu, pozostaje do sprawdzenia.

CFL interfejsu max 0,19655, pABS min 57,578 kPa w pierwszym kroku i >100 kPa w pozostałych, względny bilans masy max po 5 krokach 2,893e−5. Próg turbulencji i pozostałe bramki zachowane. RMSE η względem natywnej fali 0,255 mm w oknie 13 ms. Stan jest diagnostyczny. Odbicia, pełne okresy i siły na płacie pozostają do pomiaru.

Koszt po rozgrzaniu 2,807 s/krok dla solvera, 2,930 s/krok łącznie z raportami, inicjalizacja serwera 119 s. Ekstrapolacja pustej domeny przy 1 ms: 22,2 / 66,6 / 111,0 min dla 1 / 3 / 5 okresów, bez dodatkowych zapisów i rozruchu.

## Następny test fizyki

Usunąć początkowy skok przez inicjalizację obu faz jako spokojna woda i powietrze przy tej samej U oraz wprowadzenie fali Stokesa V przez wlot i strefę wymuszania. Łagodna rampa S5 od H≈0 do H=0,50 m przez 2 Te, bez zmian SST, VOF, geometrii, siatki lub progów. Obserwować k, ω i μt/μ w tych samych komórkach przy przejściu czoła i po osiągnięciu docelowej amplitudy. Kod inicjalizacji i rampy skompilowany. Pełny przebieg propagacyjny nie został uruchomiony. Zarchiwizowany checkpoint HOLD nie służy do wznowienia.

