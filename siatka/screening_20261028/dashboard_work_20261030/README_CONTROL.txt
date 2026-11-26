NTNU — robocze kopie dashboardow i sterowanie lokalne

Na spotkaniu korzystaj z dashboard.html oraz professor_dashboard.html w glownym katalogu mesh_screening_20261028. Zostaly zamrozone; ta podteczka zawiera nowe kopie robocze.

Aby otworzyc sterowanie bez Work: uruchom Open_NTNU_Control.cmd z tego katalogu. Panel: http://127.0.0.1:8771/
Otwarcie panelu NIE rozpoczyna obliczen. Wybierz gotowy przypadek, czas fizyczny konca [s] i limit rzeczywistego czasu pracy komputera [min], potem Start new case. Kazdy Start tworzy NOWA kopie od t=0, nie nadpisuje i nie wznawia poprzedniego przebiegu.
Stop and save zatrzymuje na granicy kroku i zapisuje policzone pola. Mozna tez ustawic stop przy czasie fizycznym albo za podana liczbe minut; wygrywa najwczesniejszy limit. Obecnego targetu nie da sie tym wydluzyc.
Do zakonczenia zapisu pozostaw komputer wlaczony. Zamkniecie karty przegladarki nie zatrzymuje kontrolera ani obliczen. Serwer lokalny i kontroler nie potrzebuja aktywnej sesji Work. Licencja STAR, zasilanie i zasoby komputera nadal sa potrzebne.
Teraz W01 jest ZATRZYMANY i zapisany przy0.168s. STAR pozostal otwarty do podgladu na Twoje zyczenie, dlatego kolejka jest zajeta i przyciski startu sa zablokowane. Nie zamykamy tego serwera automatycznie.
Po spotkaniu i ponownym podlaczeniu zasilania zdecydujemy o dalszych obliczeniach. Brak automatycznego wznowienia.
W panelu sa sciezki do katalogu i do final.sim/checkpointow z rzeczywistym dodatnim czasem obliczen. Plik z0s nie jest wynikiem. Otwieranie scen nie rozpoczyna obliczen.
Mozesz zmieniac domene w STAR, ale wtedy potrzebna jest nowa siatka, poprawione strefy falowe/diagnostyka wylotu i dopasowany spokojny przypadek. Zmodyfikowane pliki zrodlowe sa odrzucane przez kontrole tozsamosci. Warianty lambda10/30/40 czekaja na przygotowanie odpowiednich domen.
Makro skompilowano; logike przyciskow i blokad przetestowano bez uruchamiania solvera. Nowe warianty wymagaja pierwszego kontrolowanego uruchomienia. Wyniki falowe sa eksploracyjne; rozruchowe CL/CD nie sa srednimi po ustalonych cyklach.
