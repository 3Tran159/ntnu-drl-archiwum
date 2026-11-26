from pathlib import Path
import json,datetime,hashlib,py_compile
h=Path(__file__).resolve().parents[1]
for name in ['design_tight_cage_v1.py','design_tight_cage_v2.py','prepare_tight_cage_patch_mesh.py','review_tight_cage_mesh.py']:
 p=h/'tools'/name;s=p.read_text(encoding='utf8').replace('.read_text()',".read_text(encoding='utf8')")
 if name=='review_tight_cage_mesh.py':s=s.replace("startswith('c0_tight_cage_v1_')","startswith(('c0_tight_cage_v1_','c0_tight_cage_v2_'))")
 p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
a=json.loads((h/'geometry/c0_tight_cage_v1/geometry_screen.json').read_text(encoding='utf8'))
b=json.loads((h/'geometry/c0_tight_cage_v2/geometry_screen.json').read_text(encoding='utf8'))
assert a['cage_polygon']==b['cage_polygon'] and a['physical_geometry_sha256']==b['physical_geometry_sha256']
assert b['native_main_screened'] and b['native_flap_screened'] and b['patch_change_only']
assert hashlib.sha256((h/'geometry/c0_tight_cage_v2/Hydro_TightCage.stl').read_bytes()).hexdigest()==b['cage_stl_sha256']
p=h/'WORK_CURRENT_REVIEW.json';v=json.loads(p.read_text(encoding='utf8'))
v.update(at=datetime.datetime.now().astimezone().isoformat(),decision='HOLD — wyniki C0 pozostają niezatwierdzone. Wszystkie kolejne wychylenia zablokowane.',summary='Około 94% nadwyżki siły nośnej C względem B pochodziło ze stałego płata. Zwiększenie liczby iteracji na krok z 15 do 40 i sama zmiana interpolacji nie usunęły różnicy. Pierwszy rząd pędu i SST usunął ograniczanie k/omega; przywrócenie drugiego rzędu wyłącznie pędu odtworzyło anomalie przy interfejsie i obniżyło pabs do 7192,6 Pa po 90 iteracjach, przy zerowym ograniczaniu k/omega. Przebieg zatrzymano. Cała rozbieżność CL/CD nie została jeszcze ilościowo wyjaśniona.',mesh='579468 komórek w źródłowej siatce. Ochrona wybranych warstw nie odsunęła interfejsu w miejscach anomalii. Nowy ciaśniejszy obszar Overset ma około 1,25 mm prześwitu od obu ciał. Pierwsza próba jego siatkowania nie przeszła kontroli powierzchni prowadzących; zapisano stan błędu przed obliczeniami przepływu.',next='Ponowna próba siatkowania dokładnie tego samego obszaru po podziale powierzchni bocznej w istniejących narożnikach. Osiem CPU, bez przepływu. Potem pełny audyt siatki tła i łączności.',obstacle='Anomalie drugiego rzędu przy interfejsie w warstwie przyściennej. Nowa domena Overset wymaga najpierw poprawnej siatki; błąd sił 0° nadal nierozstrzygnięty.')
p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
ev=dict(at=v['at'],kind='cage_v2_geometry_verified',same_cage_coordinates=True,physical_geometry_unchanged=True,patch_triangles=b['patch_triangles'],note='Geometry/STL completed successfully. Only final dashboard write in generator failed due Windows default text encoding; UTF-8 made explicit and review updated. No geometry regeneration was required.',scientific_approved=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
print(json.dumps(ev,indent=2))
