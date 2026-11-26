# NTNU SCIENCE — Project Control Center

Stan: 3 listopada 2026. Dashboard istnieje i działa niezależnie od sesji ChatGPT Work.

## Jak otworzyć na ThinkPadzie

1. W przeglądarce wpisz: http://127.0.0.1:8787
2. Jeśli serwer nie odpowiada, uruchom plik `START_DASHBOARD.cmd` w tym katalogu.
3. Plik `OPEN_DASHBOARD.cmd` otwiera lokalny widok. Zamknięcie przeglądarki nie zatrzymuje serwera.
4. Po ponownym uruchomieniu Windows uruchom ponownie `START_DASHBOARD.cmd`. Nie instalowano usługi autostartu poza tym katalogiem.

## Dostęp z telefonu (prywatny i bezpieczny)

**Aktualnie działający adres HTTPS przez Tailscale Serve:** https://thinkpad-lucjan.tailcea0dc.ts.net/#ramp (zakładka Flap Live). Oba urządzenia muszą należeć do Twojego tailnetu. Link HTTPS został sprawdzony na ThinkPadzie; nie wymaga publicznego otwierania portów.


Aktualnie ThinkPad i iPhone znajdują się w tailnecie `serkieza@gmail.com`. Tailscale Serve udostępnia dashboard prywatnie przez HTTPS. Używaj powyższego adresu HTTPS zamiast bezpośredniego portu 8787, który może być blokowany przez zaporę Windows. Publiczne udostępnienie portu 8787 jest zabronione.

1. Włącz Tailscale na iPhonie, pozostając w tailnecie `serkieza@gmail.com`.
2. Otwórz w Safari `https://thinkpad-lucjan.tailcea0dc.ts.net/#ramp`.
3. Po restarcie ThinkPada, jeżeli strona nie działa, uruchom lokalny `START_DASHBOARD.cmd`. Nie trzeba zmieniać ustawień Tailscale Serve.

`PHONE_ACCESS.ps1` służy obecnie jedynie pomocniczo do diagnostyki adresu prywatnego IP; bezpośredni HTTP port 8787 może być blokowany przez zaporę. Nie przekierowuj portów na routerze.

## Co pokazuje

Overview: stan eksperymentu, fazę, ostatni checkpoint, decyzję i blokadę, status źródeł oraz porównanie B/C.

CFD Live: przebiegi rzeczywistych próbek CSV, CL, CD, siły, moment, residuals i kontrole jakości (o ile dostępne).

Validation: B0/C0 i dokładne okna fizycznego czasu, średnie z 25 próbek, delta CL/CD oraz pochodzenie danych.

Mesh & Overset: rzeczywiste raporty i eksportowane obrazy siatek z STAR.

Waves: osobne dane W01/W02/W03/PRE_W04, CL(t), sondy eta(t), bez uruchamiania obliczeń.

Active Flap: geometria i 100 zapisanych kroków kinematyki K0 +/-5 stopni z zamrożonym przepływem.

NDLL vs URANS / Surrogate & DRL: świadomie oznaczone jako planowane lub bez danych do czasu naukowej weryfikacji.

Computation: sprzęt Windows/RTX, dostępne pomiary; nieznane odczyty jako N/A.

Research Log: historia raportów i decyzji z plików kampanii.

## Wyniki weryfikacji 03.11.2026

- Testy źródeł, CSV, API, zabezpieczeń i integralności: **49/49 PASS**.
- Testy Chrome desktop 1440x950 i mobile 390x844: **19/19 PASS**.
- Na telefonie kluczowe metryki mieszczą się na pierwszym ekranie (koniec ok. 413 px z 844 px).
- B0: CL = 0.3266109805, CD = 0.0071911070 (okno 0.452–0.500 s).
- C0: CL = 0.3256194878, CD = 0.0072459371 (okno 0.602–0.650 s).
- ΔCL = -0.30357%; ΔCD = +0.76247%. To wyłącznie **diagnostyka PoC**, nie walidacja eksperymentalna ani niezależność siatkowa.
- K0 potwierdza **ruch geometryczny**, nie poprawę sił, mocy ani bilansu energii.
- Pierwsza próba hydrodynamiczna +2° zatrzymana z powodu przekroczenia progu ciśnienia; brak zatwierdzonych wyników tej konfiguracji.

## Pliki i testy

Katalog aplikacji: `F:\ntnu\flap_control\project_dashboard`.

Screenshoty: `screenshots\desktop_overview_cdp.png`, `screenshots\desktop_validation.png`, `screenshots\mobile_overview_390.png`, `screenshots\mobile_waves_390.png`, oraz pozostałe widoki desktop/mobile.

Raporty: `TEST_REPORT.json`, `BROWSER_TEST_REPORT.json`, `ACCEPTANCE_REPORT.md`.

Powtórzenie testów (PowerShell z katalogu aplikacji):

```powershell
python .\test_dashboard.py
node .\browser_test.mjs
```

Zatrzymanie **tylko dashboardu**: `stop_dashboard.ps1`. Nie zatrzymuje to STAR-CCM+.

## Zasady bezpieczeństwa

Serwer nie ma endpointów modyfikujących, nie uruchamia STAR-CCM+, nie edytuje .sim/.simh ani kolejki Work. Pliki źródłowe są wyłącznie czytane. Bezpieczeństwo telefonu wymaga prywatnej sieci Tailscale; nie używaj publicznego dostępu do portu.
