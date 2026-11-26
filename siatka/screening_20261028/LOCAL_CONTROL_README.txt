USER HOLD - 2026-10-30T14:24:26.098931+01:00
Own C01 and wave campaign PAUSED at explicit user request. Wait for the other agent to finish mesh convergence/optimization; no automatic restart or next-stage launch.
R3 half-dt diagnostic was compiled but NOT LAUNCHED: no case directory, consumed marker, controller or locks. Prepared files preserved; do not run them during this hold.
Previous C01 r2 remains a saved physical-guard failure at t2.777s, not an accepted calm checkpoint. Diagnostic evidence remains in both dashboards.
local_control/PAUSE and campaign_hold.json record the hold. Other CPU mesh-study and HF work remain untouched. HTTP dashboard server stays available.
Resume only after user instruction following mesh review. Future unsteady-run checkpoint policy: every0.05s (implemented in prepared R3 macro; generic macro update still pending).
Earlier records below are archival and cannot override this hold.

STEROWANIE LOKALNĄ KAMPANIĄ NTNU

Otwórz F:/ntnu/mesh_screening_20261028/Open_NTNU_Control.cmd
albo http://127.0.0.1:8771/#manual-control-panel.
Przeglądarka otwarta z pliku HTML pokazuje wyniki, ale nie uruchamia obliczeń.

Obliczenia i kolejka działają lokalnie, niezależnie od limitu Work. Komputer musi pozostać włączony, bez uśpienia i na zasilaniu.
Wybierz H, długość fali oraz odległości przed i za płatem. Nowa geometria otrzymuje własny C01; zmiana wysokości na tej samej geometrii może wykorzystać ten sam zweryfikowany C01.
Każda fala kopiuje ustabilizowaną spokojną wodę. Pełna wysokość na wlocie od aktywacji, bez rampy i bez inicjalizacji fali w całej domenie.
Przyciski uruchamiania są dostępne dopiero po zgodności kompilacji, audytu API oraz testów. Szare przyciski nie oznaczają trwających obliczeń.

Queue and run: dodaje wybraną konfigurację; kolejka działa sekwencyjnie.
Build .sim only: zapisuje przygotowaną definicję z obliczonym C01, jeżeli jest dostępny; dla nowej geometrii najpierw tworzy wejście spokojnej wody bez kroków przepływu.
Queue full selected campaign: W01a, W02, W01a 3λ, następnie W03–W08. Pierwszy nierozwiązany błąd zatrzymuje kolejkę.
Stop, save and pause queue: zatrzymuje nasz przepływ na granicy kroku i zapisuje wynik. Kolejne zadania nie startują.
Cancel queued job: usuwa oczekujące zadanie z kolejki wykonania, ale zachowuje jego zapis.
Acknowledge review: archiwizuje komunikat po sprawdzeniu błędu; nie wznawia uszkodzonego pola. Continue wymaga osobnego kliknięcia.
Open .sim / Show folder: otwiera wyłącznie ukończony zapis z listy. Przy każdym pliku widać czas fizyczny. Nie myl przygotowanej definicji z wynikiem fali.

C01: porównanie średnich CD i CL w sąsiednich oknach po0,2s; obie względne zmiany<0,5%, mianownik to bezwzględna średnia z najnowszego okna.
Wykresy pokazują te zmiany, a nie różnicę między pojedynczymi krokami.
Fale: najpierw potwierdzona obecność utrzymującej się fali przy płacie, potem porównanie4pełnych cykli bez sztucznego przesuwania faz.
10okresów to orientacja, a nie minimum. Limit20okresów od aktywacji wymaga przeglądu, jeśli przebiegi nie są powtarzalne.
Powtarzalność nie zastępuje sprawdzenia siatki, kroku czasu, propagacji i odbić. Bilans masy nadal jest raportowany. Zabezpieczenie50m/s i ograniczenia fazy pozostają.

Aktualny problem 30.10.2026:
C01_W20L4_M10_calm_settle_r2 zatrzymane przez zabezpieczenie przy t=2,777s.
Powietrze osiągnęło50,162m/s w x=23,659m,z=2,019m; fala nie była aktywna.
Nie powstał zatwierdzony C01_settled.sim. final.sim jest zapisem diagnostycznym.
Kolejka W01a zatrzymała się prawidłowo. Nie uruchamiaj ponownie zakończonych kontrolerów ani tej samej próby.
W tej chwili końcowy audyt nowego przepisu pozostaje niewykonany; przyciski uruchomienia są celowo zablokowane.
Świeży stan sprawdzaj w dashboardzie i RESUME_AT_HOME.txt — ten opis jest migawką.

Wyniki HTML: F:/ntnu/mesh_screening_20261028/local_campaign_results.html
Kontrolery i opis ratunkowy: F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/
Obliczone pliki i zachowane próby: E:/ntnu/quasi2d_waves_20261029/
Osobne badanie CPU siatek i sesja HF pozostają niezależne; panel ich nie zatrzymuje.
