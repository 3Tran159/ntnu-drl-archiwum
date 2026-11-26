# NTNU – sterowanie płatem uczone przez wzmacnianie (DRL) – archiwum (zamknięte 13.11.2026)

Projekt NTNU (staż, Trondheim, X–XI 2026), prowadzący: prof. Sverre Steen. Autor: Julek.
Wątek **zamknięty** decyzją ze Sverrem 13.11.2026: DRL nie rozwijamy, dalej model fizyczny (Faltinsen) → repo [`ntnu-model-plata-mpc`](https://github.com/3Tran159/ntnu-model-plata-mpc).

Pytanie: czy sterowanie kątem płata nauczone w szybkim modelu (TD3/SAC, jak Godø 2024) obniża opór na fali regularnej także w URANS (STAR-CCM+)?

## Wynik w jednym zdaniu

Model obiecywał −68 % mocy oporu (TD3) i −69 % (MPC); URANS dał −34,7 % (TD3_GODO), **−37,1 % (TD3_C338)**, −31,5 % (MPC) przy z̈ RMS 2,5–5,3 m/s² (5–10× ponad komfort 0,49 m/s²). **Wąskim gardłem jest model, nie sieć.**

## Wyniki URANS (obciążenie 100 %, woda spokojna 61,1 W na pasek 0,02 m)

| Sterownik | ΔP oporu, 3 okresy [%] | z̈ RMS [m/s²] | P siłownika [W] | Opór + siłownik vs woda spokojna [%] | Godø NDLL 3D [%] |
|---|---|---|---|---|---|
| PID1 | −19,2 | 1,99 | 0,09 | −19,0 | −11,2 |
| PID2 | −3,4 | 2,22 | 0,16 | −3,1 | −2,45 |
| PID3 | +49,0 | 1,79 | 0,61 | +50,0 | +18,0 |
| TD3_GODO | −34,7 | 2,76 | 5,60 | −25,5 | −63,9 |
| TD3_C338 | **−37,1** | 2,47 | 3,38 | **−31,6** | – |
| MPC_WZ2 | −31,5 | 5,30 | 17,90 | −2,2 | – |

Kolumny: ΔP oporu = średnia `P_drag_W` z ostatnich 3 okresów spotkania względem wody spokojnej; z̈ RMS = przyspieszenie pionowe płata; P siłownika = średnia dodatniej mocy mechanicznej obrotu płata (bez sprawności serwa); Godø = Ocean Eng. 312 (3D). Przypadek: U 12,35 m/s, c 0,312 m, h 1,09 m, fala H 1,5 m, T 5 s. Pełne liczby i zastrzeżenia: `mini_vof_i_drl_2026-11/DRL_2026-11-13/RAPORT_ARCHIWALNY_DRL_2026-11-13.md`.

## Wnioski

1. Błąd modelu rośnie z agresywnością ruchu: PID 6–13 pkt, TD3 33 pkt, MPC 37 pkt. Siły przy zadanym ruchu model liczy dobrze (±3–4 %); myli się pętla zamknięta.
2. MPC liniowy – wynik ujemny: po doliczeniu mocy siłownika zysk netto −2,2 %.
3. Dodatek oporu ΔCD ≈ 0,0015 w overset jest także przy płacie nieruchomym (OVS_FIX_TRIM) → to nie ruch siatki; przyczyna otwarta.
4. Przebiegi `*_BLAD_PIDKp10` to błąd makra (liczył PID zamiast polityki) – nie są wynikami.

## Struktura

| Folder | Co | Okres |
|---|---|---|
| `flap_control_2026-10/` | pierwsze podejście: aktywna klapa, DRL na klapie, walidacja hydro w STAR 2606, panel projektu, laboratorium Mini-POC 2D | 28.10–06.11 |
| `siatka/` | screening siatek, geometria NACA 66-012 mod, faza 2, ustawienia siatki HF 25 mln | 28–30.10 |
| `fale/wave_depth_20261029/` | wpływ głębokości / fali (W20/W30, H12–H24) | 29.10 |
| `walidacja_XFOIL_20261104/` | XFOIL / Abbott Re 20 mln, mapa faz, porównanie W04 | 04–06.11 |
| `mini_vof_i_drl_2026-11/` | Mini-VOF (PI, PRBS, mapy FF) + **raport archiwalny DRL** | 09–13.11 |
| `td3_sac_na_modelu_wirowym/` | treningi TD3/SAC (`meta.json`, `eval.csv`, krzywe), surrogat | 10–13.11 |
| `urans_polityki_TD3/` | przebiegi URANS overset z politykami TD3 (`history.csv`, `run.properties`) | 12–13.11 |
| `td3_komfort_20261117/` | TD3 z kryterium komfortu (porównanie z MPC) | 17.11 |
| `docs/` | spis dokumentów projektu claude.ai dotyczących tego wątku | |
| `skrypty/` | `zbuduj_repo.py` (budowa repo), `pochodzenie_plikow.csv` | |
| `ARCHIWUM_DANYCH_inwentarz.csv` | ciężkie pliki (.sim, .simh, checkpointy) z pełną ścieżką i rozmiarem | |

## Co nie jest w repo

Pliki `.sim/.simh`, checkpointy sieci, klatki animacji, CSV > 0,3 MB (np. residua, pełne historie) – zostają na dyskach źródłowych: `F:\20_DANE_OBLICZEN\NTNU_flap_control_i_siatki_2026-10`, `T:\NTNU_GODO_CONTROL_20261109\90_ARCHIWUM`, `H:\10_ARCHIWUM_PROJEKTOW\NTNU_RESEARCH_ARCHIVE\Active_Flaps`. Spis: `ARCHIWUM_DANYCH_inwentarz.csv` (2480 plików, ok. 470 GB). Ścieżki w skryptach są bezwzględne (stan dysków z XI 2026).

## Wymagania

STAR-CCM+ 2602/2606 (licencja Power-on-Demand – klucza **nie ma** w repo, w logach jest `REDACTED`), Python 3.12 (numpy, torch dla TD3/SAC), laptop ThinkPad (16 rdzeni, GPU RTX PRO 3000 12 GB).

Odbudowa repo z dysków: `python skrypty/zbuduj_repo.py ntnu-drl-archiwum`.
