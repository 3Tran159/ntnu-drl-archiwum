# Aktualizacja03.11.2026 — ograniczona kampania etapowa

Nowa, odrębna autoryzacja: BOUNDED_FIXED_PLUS2_SWEEP_20261103. Start z C0 SPEED DOWN t0,690s; 8CPU,bez GPU,dt0,002s,50iteracji wewnętrznych. Dalej: ta sama redukcjaU→10; ustalenie0°; płynne+2°; ustalenie; sweep10/12/14/16/18. Etapy są automatyczne, z niezmienionymi progami bezpieczeństwa. StareFAIL nie zostały odblokowane.

- START / RESUME ręcznej pauzy: `F:\ntnu\flap_control\START_BOUNDED_FLAP_SWEEP.cmd`
- STOP: `F:\ntnu\flap_control\STOP_CFD.cmd`
- STATUS: `F:\ntnu\flap_control\STATUS_CFD.cmd`
- Bieżący stan: `F:\ntnu\flap_control\hydro_validation_2606_20261102\BOUNDED_SWEEP_STATUS.json`
- Dashboard: `F:\ntnu\flap_control\hydro_validation_2606_20261102\NIGHT_DASHBOARD.html`
- Pełne zasady: `hydro_validation_2606_20261102\reports\BOUNDED_FIXED_PLUS2_SWEEP_20261103\WORKFLOW.html`

START nie powtarza ukończonych lub nieudanych zadań. Po naruszeniu bezpieczeństwa pozostaje HOLD. Przed przeniesieniem komputera użyj STOP i sprawdź zapis oraz procesy; W04 jest niezależny. Starsze opisy poniżej dotyczą archiwalnych etapów, a nie zgody na ich ponowne uruchomienie.

---

# Aktualizacja 03.11.2026 — obowiązująca blokada

Stała klapka+2, sweep10–18m/s: krótki rozruch10m/s zakończył się FAIL/HOLD przyt0,002s. Nie uruchamiać rampy ani kontynuować błędnego checkpointu. START_SPEED_SWEEP_PLUS2.cmd przygotowany, lecz celowo blokuje pełny start do uzyskania poprawnego smoke. Szczegóły: [SPEED_SWEEP_PLUS2_WORKFLOW.md](SPEED_SWEEP_PLUS2_WORKFLOW.md). W04 pozostaje niezależny. Poniższy wcześniejszy opis nie jest zgodą na wznowienie błędnych przypadków.

---

# Lokalna kolejka CFD — START / STOP / RESUME / STATUS

Stan 03.11.2026: eksperyment +2° zakończony **FAIL** przy t = 0,672 s.
Checkpoint diagnostyczny, wykresy i raport są zapisane. Kolejne warianty są zablokowane.
Benchmark 8/12/16 MPI przerwano przed końcem rozgrzewki; nie wybrano zwycięzcy.
Maksymalny dopuszczalny limit: 16 CPU, bez GPU. W04 pozostaje niezależny.

Wszystkie cztery pliki poleceń znajdują się w `F:\ntnu\flap_control`.

| Polecenie | Działanie |
|---|---|
| `START_CFD.cmd` | Uruchamia istniejący kontroler w ukrytym oknie. Jeśli kontroler już działa, przejmuje jego stan bez tworzenia drugiego. Zachowuje blokady naukowe i ustawienia kolejki. |
| `STOP_CFD.cmd` | Blokuje nowe zadania i zapisuje żądanie bezpiecznego zatrzymania. Makro odczytuje je między krokami i zapisuje stan. Nie zabija procesów. Kontroler kończy pracę dopiero po zakończeniu własnego zadania. |
| `RESUME_CFD.cmd` | Dopuszcza wyłącznie wcześniej zatwierdzone, nieukończone zadania z potwierdzonymi hashami. Nie powtarza ukończonych obliczeń i nie resetuje rozwiązania. Nie usuwa blokady naukowej ani blokady bezpieczeństwa. |
| `STATUS_CFD.cmd` | Pokazuje rzeczywistą obecność kontrolera, aktywne zadanie, blokadę, najnowszy checkpoint z SHA-256, zasoby i kolejkę. |

**Obecnie RESUME celowo odmawia uruchomienia +2°.** Najpierw trzeba rozwiązać problem ujemnego ciśnienia, ocenić przygotowaną poprawkę i zatwierdzić konkretną kopię oraz makro. Polecenie RESUME nie jest sposobem pomijania tej oceny.

## Praca bez aktywnego Work

Kontroler działa lokalnie, niezależnie od sesji Work. Komputer musi pozostać włączony i nieuśpiony, a licencja dostępna. Nie zmieniono ustawień zasilania ani autostartu Windows.

Zamknięcie Work nie zatrzymuje kontrolera. Po ponownym połączeniu zacznij od STATUS; nie odtwarzaj ręcznie listy starych zadań.

Kolejka wykonuje zatwierdzone zadania kolejno. Po naruszeniu kryterium fizycznego, błędzie wykonania lub braku potwierdzonego zapisu przechodzi w HOLD. Sam sukces procesu nie zatwierdza wyniku naukowego.

Po restarcie samego kontrolera aktywne zadanie jest przejmowane z zachowanego stanu. Zapisano również zamiar startu przed uruchomieniem STAR; jeśli kontroler zniknie między uruchomieniem procesu i zapisem stanu, odtwarza powiązanie z potwierdzenia startu. Niepewny start powoduje HOLD zamiast ponownego uruchomienia.

**Wznowienie po zatrzymaniu solvera wymaga zatwierdzonego zadania kontynuacji**, którego input wskazuje konkretny zapisany checkpoint, a makro obsługuje jego czas i konfigurację. Obecne makra mają ścisłe warunki wejścia; kontroler nie przerabia ich samodzielnie ani nie uruchamia ponownie od początkowych pól. Automatyczne przejęcie działającego procesu i automatyczne odtworzenie utraconego rozwiązania to różne operacje.

## Zabezpieczenia

- Limit 16 CPU; brak GPU w kampanii klapki.
- Jedno zadanie STAR tej kampanii naraz; niezależne kampanie pozostają nietknięte.
- Przed nowym startem: zatwierdzenie zadania, dozwolone makro, SHA-256 wejściowego `.sim` i makra, ścieżka wewnątrz katalogu przypadków.
- Start wymaga co najmniej 8 GiB wolnej pamięci i 15 GiB miejsca na dysku. Poniżej 4 GiB RAM lub 5 GiB miejsca podczas pracy: żądanie łagodnego zatrzymania.
- Brak zmiany czasu/iteracji przez 900 s: żądanie zatrzymania. Nie wystarcza samo dopisywanie komunikatów do logu.
- Zapis trwający ponad 1800 s: HOLD i zachowanie procesu; bez wymuszonego zabijania podczas zapisu.
- Domyślny limit czasu zadania: 8 godzin; zadanie może mieć jawnie zatwierdzony inny limit.
- Bieżące makra kontrolują ciśnienie, k/ω, masę i siatkę przy granicach kroków. Progi pozostają niezmienione.
- Zapis jest uznawany za kompletny po natywnym komunikacie zakończenia i potwierdzeniu stabilności pliku; obliczany jest SHA-256. To nie zastępuje pełnego natywnego ponownego otwarcia.
- Po każdym zadaniu automatycznie powstaje raport JSON/HTML i zredagowana kopia logu.

Watchdog nie naprawia zawieszonego STAR przez force-kill. Jeśli solver przestanie odpowiadać i nie dojdzie do granicy kroku, potrzebna będzie interwencja; STATUS/raport pokaże blokadę. Zachowany ostatni checkpoint jest wtedy podstawą dalszej decyzji.

## Pliki

Katalog kampanii: `F:\ntnu\flap_control\hydro_validation_2606_20261102`

- `NIGHT_QUEUE.json` — zatwierdzenia i bramki.
- `NIGHT_QUEUE_STATE.json` — wykonane zadania i aktywny proces.
- `NIGHT_STATUS.json`, `NIGHT_DASHBOARD.html` — stan lokalny.
- `NIGHT_DECISIONS.jsonl` — historia decyzji, uruchomień i błędów.
- `reports\automatic` — automatyczne raporty wykonania.
- `runs\controller_*.log` — wyjście kontrolera; `runs\redacted` — logi solvera bez klucza licencji.
- `reports\STATIC_PLUS2_20261103\REPORT.html` — naukowy raport nieudanej próby +2°.
- `audit\QUEUE_SAFETY_TESTS_20261103.txt` — testy zabezpieczeń.

## Zakres testów

Przeprowadzono osiem izolowanych testów z atrapą wyniku solvera: integralność wejścia, limit CPU, ścieżka spoza kampanii, brak postępu, ochrona zapisu, przejęcie potwierdzonego startu, blokada niepewnego startu, checkpoint i raportowanie. Nie uruchamiały CFD.

Na rzeczywistej zatrzymanej kolejce sprawdzono START, powtórny START bez duplikatu, STOP, STATUS i odmowę RESUME przy blokadzie naukowej. Rzeczywista próba +2° wcześniej potwierdziła zatrzymanie po błędzie fizycznym, zapis checkpointu i brak startu następnej konfiguracji.

Nie testowano wymuszonej awarii systemu, przerwania zapisu ani odtwarzania pełnego solvera po utracie zasilania. Nie ma obietnicy automatycznej naprawy takich zdarzeń.
