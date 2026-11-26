# Mini‑URANS–VOF · SST i wariant wall functions

## Decyzja i dane

Zostaje SST k–ω Mentera z All y+ Wall Treatment. Takie modele zawiera konfiguracja VOF używana przez Mini. Nowa kopia siatki zmienia położenie węzłów w pasie do 30 mm od płata. Kształt, topologia, liczba komórek (44 442), rozpiętość 20 mm i wszystkie węzły pasa VOF są identyczne. Model sealed i model ze szczeliną 2,5 mm są odrębnymi poziomami fizyki.

Na siatce bieżącej mediana odległości geometrycznej środka komórki to 10 µm, pełna pierwsza warstwa 20 µm, 12 rzędów i wzrost ok. 1,20. Mapę rzeczywistego STAR y+ odtworzono z eksportu sealed 0° przy U=18 m/s na poprzedniej jednofazowej siatce 2D. Powierzchnie ważono długością ściany × 20 mm, po dopasowaniu środków ścian z błędem poniżej 2e−15 m. Archiwum zachowuje status HOLD_TIME_BUDGET. Mapa jest diagnostyką warstw, bez kwalifikowania sił do walidacji. Bezpośredni pomiar y+ quasi‑2D VOF pozostaje do wykonania.

| Obszar | y+ P05 / P50 / P95, archiwum STAR 0° | Projekcja P50 nowej siatki przy tej samej wartości naprężenia |
|---|---:|---:|
| Całość | 2,87 / 3,82 / 6,92 | 51,68 |
| Główna ssąca | 3,64 / 4,17 / 6,55 | 56,24 |
| Główna ciśnieniowa | 2,83 / 3,55 / 5,62 | 47,91 |
| Klapka ssąca | 2,66 / 3,05 / 3,49 | 44,07 |
| Klapka ciśnieniowa | 3,40 / 3,61 / 3,77 | 51,41 |
| Natarcie, x/c≤0,05 | 6,49 / 7,29 / 9,25 | 63,47 |
| Zawias, 0,77≤x/c≤0,83 | 3,38 / 3,67 / 3,95 | 49,52 |
| Spływ, x/c≥0,97 | 2,56 / 3,36 / 3,74 | 36,28 |

0% pola powierzchni archiwalnej jest w przedziale 30–100. Projekcja z nieruchomego 0° daje 97,9% w 30–100 i 51,5% w 50–70. To obliczenie geometryczne z zachowaniem uτ, nie wynik CFD. Na nosie lokalne minimum y+ wynosi 0,73, choć mediana całej strefy natarcia jest wyższa. Nie wymuszamy log‑law w stagnacji. Przy zawiasie i spływie do oceny separacji potrzebny jest znak naprężenia stycznego oraz przebieg Cp. Samo y+ separacji nie identyfikuje.

## Dobór warstwy

ρ=1000 kg/m³, μ=0,001 Pa·s, ν=1,00e−6 m²/s, U=18 m/s, c=1,19 m i Re=2,142e7. Korelacja ITTC‑1957 Cf=0,075/(log10(Re)−2)² daje 0,002639 i uτ=0,654 m/s. To skala orientacyjna dla gładkiej powierzchni. Dla y+=50–70 otrzymujemy odległość środka 76–107 µm i pełną warstwę 153–214 µm dla prawie prostokątnego przekroju. Dla y+=60 są to 91,8 i 183,5 µm. Projektowy zakres 30–100 daje 45,9–152,9 µm do środka i 91,8–305,9 µm pełnej warstwy.

Kopia V2 korzysta dodatkowo z archiwalnego rozkładu uτ. Mediana pełnej warstwy wynosi ok. 270 µm, środka ok. 135 µm. Na dużej części klapki pełna warstwa jest ok. 287 µm. Dwanaście rzędów i wzrost nominalnie 1,12 poza zachowanym nosem. W pierwszej próbie pogrubienie samego nosa odwróciło osiem komórek, więc zachowano stare węzły w bezpośrednim sąsiedztwie nosa i płynne przejście. Na V2 wszystkie 44 442 komórki i narożniki pozostały dodatnie w 41 sprawdzonych położeniach ±2°. Min. objętość 1,55e−11 m³, min. narożnikowy jakobian 7,73e−10 m², min. Gmsh SICN przy 0° 0,0146. Import i pomiar STAR tej kopii są osobną bramką. Natywne PASS kinematyki dotyczy wcześniejszej siatki.

## Interfejs Stokesa V

W wersji z globalną inicjalizacją H=0,50 m sześć komórek z μt/μ=100000 znajdowało się po stronie powietrza, w powtarzających się punktach oddalonych o 10 m. Ustalono to w pustej domenie. W polu startowym maks. |wirowość| powietrza ~29 s⁻¹ i moduł odkształcenia ~36 s⁻¹ w pasie pomiarowym. Po 14 krokach maks. k powietrza 5,88 m²/s² i min. ω 1,47e−10 s⁻¹. Pole startowe spokojnej wody ma k=4,86e−4 m²/s², ω powietrza 3,24 s⁻¹ i ω wody 48,6 s⁻¹, µt/µ=10 w obu. Łagodna rampa do t=0,040 s utrzymała µt/µ w pasie poniżej 10,12, ale osiągnęła dopiero H≈0,000399 m na wlocie. Vorticity Limiter był aktywny według natywnego SETUP_READBACK. Interface Turbulence Damping pozostaje kandydatem na osobny test A/B w razie powrotu nadprodukcji przy interfejsie. Pomiar gradientów z istniejących pól wykonano różnicami centralnymi w pasie VOF.

## Porównanie po odblokowaniu przepływu

Na tym samym fixed foil 0° porównać starą i V2 przy tych samych SST All y+, H, U, dt, warunkach brzegowych i fazie. Zachować tylko jeden czynnik różniący parę, czyli odległości w warstwie. Makro na kopii eksportuje całkowite Fx oraz osobno ciśnienie i ścinanie, Fz, Mh, mapę ciśnienia i y+. Obliczyć Cp z tym samym ciśnieniem referencyjnym, z jawną korekcją hydrostatyczną. Zestawić średnie, harmoniczne, znaki ścinania i koszt fizycznego kroku. Później jedna dokładniejsza kopia y+≈1, orientacyjnie środek 1,53 µm i pełna warstwa 3,06 µm według tego samego Cf, z weryfikacją a posteriori.

## Źródła

- Portal‑Porras i in., 2023. STAR‑CCM+, URANS SST, Overset i RL stanowią odniesienie architektoniczne dla sterowania. [Artykuł](https://addi.ehu.es/bitstream/handle/10810/65807/1-s2.0-S0029801823021595-main.pdf?sequence=3)
- Kumar i Shin, 2019. SST/VOF, Stokes drugiego rzędu i y+≈1 dają punkt odniesienia dla późniejszego porównania rozdzielczości przyściennej. [Artykuł](https://www.mdpi.com/2077-1312/7/11/396)
- De Carlini i in., 2025. Przykład All y+ i y+=30–130 dla kadłuba w URANS/VOF. [Artykuł](https://journals.sagepub.com/doi/full/10.3233/PMST250045)
- ITTC 2024, §2.3.6 i §3.2. Projektowy zakres 30–100, wzrost 1,2, około 15 punktów i ograniczenia w silnym niekorzystnym gradiencie ciśnienia. [Wytyczne](https://ittc.info/media/11958/75-03-02-03.pdf)
- Larsen i Fuhrman, 2018. Diagnostyka nadprodukcji turbulencji w obszarach niemal potencjalnych z odkształceniem. Zastosowanie Vorticity Limiter w STAR jest odrębną decyzją modelową. [Artykuł](https://doi.org/10.1017/jfm.2018.577)

