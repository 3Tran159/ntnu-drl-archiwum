import json
from pathlib import Path
p=Path(r"F:\ntnu\phase2_012_20261029")
f=p/"observations.json";d=json.loads(f.read_text(encoding="utf-8"))
d["F18_18ms"]=[
"Zakończono 15 kroków po 0,00001 s: 0,00015 s czasu fizycznego i około 301 s wykonania. Zakończenie nastąpiło przez limit czasu, bez błędu solvera.",
"Na końcu: Fx = 21 532,91 N, Fz = 123 290,58 N; CD = 0,0243869, CL całkowite = 0,139632. To wartości rozruchowe, nie ustalone współczynniki.",
"Średnie y+ po polu = 80,57; zakres 4,56–199,49. Nie dobieramy jeszcze nowej pierwszej warstwy na podstawie tak krótkiego rozruchu.",
"Maksymalny CFL osiągnął 8,07, potem spadł do 4,61. Największa prędkość osiągnęła 100,68 m/s, na końcu wyniosła 71,82 m/s. To lokalne sygnały do kontroli; nie stwierdzono trwałej rozbieżności w tym krótkim oknie.",
"Zmierzono około 20,0 s na krok przy 24 procesach CPU. Przy dt=1e-5 s ekstrapolacja tego tempa do jednego c/U daje około 36,8 h. To koszt rozruchowy, nie prognoza czasu do zbieżności; trzeba jeszcze poprawić tempo osiągania użytecznego czasu fizycznego."
]
f.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
f=p/"build_dashboard.py";s=f.read_text(encoding="utf-8")
s=s.replace('plots=chart(rows,"Fx_half_N","Siła Fx","N","#246bce")+chart(rows,"Fz_half_N","Siła Fz, z wyporem","N","#148464")',
'force_rows=rows[4:] if u and len(rows)>5 else rows\n    note += "<p>Wykresy sił dla 18 m/s pokazują kroki od 5. Pełny impuls rozruchowy pozostaje w history.csv.</p>" if u and len(rows)>5 else ""\n    plots=chart(force_rows,"Fx_half_N","Siła Fx"+(" · krok 5+" if u and len(rows)>5 else ""),"N","#246bce")+chart(force_rows,"Fz_half_N","Siła Fz, z wyporem"+(" · krok 5+" if u and len(rows)>5 else ""),"N","#148464")')
f.write_text(s,encoding="utf-8")
print("Final startup findings and readable force plots saved")
