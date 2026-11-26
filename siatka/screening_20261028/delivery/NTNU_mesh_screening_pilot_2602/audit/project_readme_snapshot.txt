PROJEKT NTNU — CFD / NEGATIVE WAVE ADDED RESISTANCE
Wersja 02 | 2026-10-27 | pełny płat, wybór DAT, NACA 66_1-012

CO DZIAŁA
Journal pyta o plik DAT, sprawdza dane i tworzy parametryczne krzywe
przekrojów w NX. Długości w mm. Domyślnie powstaje PEŁNY płat.
Domenę CFD użytkownik przetnie sam w STAR-CCM+.
Poprzedni rdzeń importu krzywych uruchomił się poprawnie w NX użytkownika.
Nowy wybór pliku i nowe zależności geometrii wymagają pierwszego testu w NX.
Journal tworzy KRZYWE, nie gotową bryłę. Nie zapisuje .prt ani STEP.

URUCHOMIENIE
1. Rozpakuj cały ZIP do osobnego katalogu v02; zachowaj podfoldery.
2. Otwórz NOWY Model w NX w milimetrach. Zachowaj wcześniejszy .prt.
3. Journal > Play: nx_import_sections.py.
4. W oknie wyboru pliku wybierz domyślny:
   profiles/naca66_012_a08mod_camber025_reconstructed.dat
5. Powinno powstać 5 par splajnów. Obróć widok i użyj Fit.
6. Test: HF_root_chord=1300 -> c_tip=429 mm; przywróć 1190.
   HF_center_fraction=0.6 -> załamania przesuwają się na Y=+-3300 mm
   przy pełnej rozpiętości 11000 mm; przywróć 0.5.
   Te testy trzeba potwierdzić w NX, nie tylko w generatorze współrzędnych.

Jeśli okno wyboru nie jest dostępne na tym komputerze, journal poda błąd.
Można jawnie ustawić CHOOSE_PROFILE=False w journalu: wtedy używa dat_path
z foil_config.json. Nie ma automatycznego wyboru innego profilu po błędzie.
Anulowanie okna kończy import bez zmian w modelu.
Jeśli NX nie rozpoznaje folderu journala, ustaw CONFIG_PATH na pełną ścieżkę
do foil_config.json.
Błąd techniczny: zachowaj cały komunikat i numer linii.

WŁASNE PROFILE Z BAZY AIRFOILS
Pobieraj pliki współrzędnych .dat, najlepiej w formacie Selig.
Wrzucaj je do profiles albo wybierz plik z innego folderu.
Selig: opcjonalny tytuł, potem dwie kolumny x/c i y/c,
obwód TE góra -> LE -> TE dół. Separator: spacje/tabulatory.
Lednicer też jest obsługiwany: liczby punktów i dwie powierzchnie.
To mają być współrzędne profilu, nie tablice CL/CD/alpha.
Plik musi używać jednostkowej cięciwy (okolice x=0..1), nie procentów 0..100.
Nie zmieniamy automatycznie camberu, grubości ani grubości krawędzi spływu.
Niewielkie x<0 przy nosku wygiętego profilu jest dopuszczalne.
Źródło formatów: https://m-selig.ae.illinois.edu/ads.html

Zwykły NACA 66_1-012 z bazy może być SYMETRYCZNY. Nasza domyślna
rekonstrukcja ma dodatkowo a=0.8(mod) i maksymalne wygięcie 2.5% cięciwy.
Te kształty są różne. Nazwa pliku nie potwierdza geometrii; zachowuj źródło.
Wybór DAT używa jego kształtu bez przeróbek. NACA 66-010 zachowano jako
starszy profil do porównań. Pliki *_full401.dat służą kontroli kształtu;
z 5 stacjami przekraczają limit punktów journala. Zacznij od kompaktowego DAT.

PARAMETRY GŁÓWNE W EXPRESSIONS
HF_span              pełna rozpiętość, nie połowa
HF_root_chord        cięciwa środkowa
HF_taper             stosunek cięciwy końcowej do środkowej
HF_center_fraction   udział stałej cięciwy w pełnej rozpiętości; 0.5
HF_sweep_deg         skos osi 1/4 cięciwy
HF_dihedral_deg      wznios (przesunięcie stacji w Z)
HF_incidence_deg     kąt ustawienia, dodatni nos do góry
HF_tip_twist_deg     dodatkowe skręcenie końcówki
HF_pivot_xc          pozostaw 0.25
Inne HF_s... to wyrażenia zależne. Nie edytuj ich ręcznie.
Zachowaj dodatnie długości/taper i 0<HF_center_fraction<1.
Zmiana pliku profilu/liczby stacji wymaga importu do nowej części.
Zmiana parametrów głównych aktualizuje istniejące krzywe po Update.

ROZKŁAD CIĘCIWY W PRACY 2024
Godø, Steen, Faltinsen, A resistance model for hydrofoil fast ferries with
fully submerged foil systems, Ocean Engineering 301 (2024), 117503.
https://doi.org/10.1016/j.oceaneng.2024.117503
Sekcja 2.1: NACA 66_1-012 + NACA a=0.8(modified).
Sekcja 2.2: główny płat ma stałą cięciwę w środkowej połowie rozpiętości;
zewnętrzne części zwężają się liniowo. Table 1: taper=0.33.
Płat tylny ma odcinek stałej cięciwy o długości 33% pełnej rozpiętości.
Sekcja 2.3: camber i twist są dobierane po rozpiętości do rozkładu
cyrkulacji; niniejszy model nie odtwarza tej optymalizacji.

Dla b=pełna rozpiętość, eta=2*abs(y)/b, f=0.5 i lambda=0.33:
  c/c_root=1                                  gdy eta<=f
  c/c_root=1+(lambda-1)*(eta-f)/(1-f)           gdy eta>f
Pozycje załamania: y=+-b/4.

OBECNE WYMIARY SĄ PRZYKŁADEM CAD
b=11000 mm i c_root=1190 mm zachowano jako edytowalne wymiary robocze
z wcześniejszego modelu. NIE przypisujemy ich konkretnemu promowi z pracy
2024. Profil i prawo cięciwy są według nowego wyboru. Nie jest to HFF1 1:1.
Stacje Y: -5500, -2750, 0, 2750, 5500 mm.
Cięciwy: 392.7, 1190, 1190, 1190, 392.7 mm.
Stałe maksymalne wygięcie 2.5%, zerowe skręcenie, skos i wznios to
ustawienia demonstracyjne; nie są rozkładem odczytanym z pracy 2024.

OD KRZYWYCH DO BRYŁY
W wariancie prostym bez skręcenia wykonaj oddzielne Through Curves:
lewy tip -> lewe załamanie; środkowy panel między załamaniami;
prawe załamanie -> prawy tip. Każdy przekrój to pełny zamknięty obwód.
Dobierz wynik solid, zgodną orientację LE/TE i liniowy przebieg paneli,
następnie Unite. Gładki loft przez wszystkie stacje może zaokrąglić
załamania obrysu. Sprawdź wspólną styczną góra/dół przy LE i odchyłkę
splajnów od danych. Po skręceniu sprawdź liczbę stacji i interpolację.
Przed eksportem: poprawność bryły, objętość, brak wolnych krawędzi.

CFD
Pełny CAD pozostaje pełny. Przy domenie połowy płata y=0 jest płaszczyzną
symetrii, nie fizyczną końcówką płata. Symetria wymaga symetrycznych
warunków/geometrii/ruchu; fale skośne, roll lub niesymetryczne klapy ją łamią.
Do współczynników sił używaj pola odpowiadającego analizowanej połowie;
pełna siła=2*siła połowy przy zachowanej symetrii.

GENERATOR POZA NX — OPCJONALNIE
  python foil_sections.py foil_config.json sections_output
  python -m unittest discover -v
NX journal działa w interpreterze NX. Generator współrzędnych wymaga
Python 3.8+ i nie wymaga zewnętrznych bibliotek.
Źródła, metadane i walidacja profili są w profiles.
Testy poza NX nie zastępują kontroli krzywych i bryły ani walidacji CFD.
