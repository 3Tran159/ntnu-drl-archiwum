from pathlib import Path
import json,datetime,py_compile,shutil
h=Path(__file__).resolve().parents[1];stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
changes={}
p=h/'tools/night_native.py';s=p.read_text(encoding='utf8');old="'C0InnerIterationTest.java':8}"
assert old in s;changes[p]=s.replace(old,"'C0InnerIterationTest.java':8,'C0DistanceInterpolationTest.java':8}")
p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8')
old="'ResumeC0Qualified.java','C0InnerIterationTest.java'}";assert old in s;s=s.replace(old,"'ResumeC0Qualified.java','C0InnerIterationTest.java','C0DistanceInterpolationTest.java'}")
old="return H/'cases/SP_C_split0_overset'/(('c0_inner40_' if receipt['macro']=='C0InnerIterationTest.java' else 'c0_resume_')+receipt['run_id'])"
new="prefix={'C0InnerIterationTest.java':'c0_inner40_','C0DistanceInterpolationTest.java':'c0_distance_','ResumeC0Qualified.java':'c0_resume_'}[receipt['macro']]\n return H/'cases/SP_C_split0_overset'/(prefix+receipt['run_id'])"
assert old in s;s=s.replace(old,new)
old="'overset_error_cells','difficult_interpolation_cells']:";assert old in s;s=s.replace(old,"'overset_error_cells','difficult_interpolation_cells','omega_floor_cells','k_floor_cells','max_turbulent_viscosity_ratio']:")
changes[p]=s
p=h/'tools/night_dashboard.py';s=p.read_text(encoding='utf8')
old="case='C0 — klapka 0°, test 40 iteracji/krok' if a and a['macro']=='C0InnerIterationTest.java' else (a['macro'] if a else 'C0 — ocena wyników')"
new="case={'C0InnerIterationTest.java':'C0 — klapka 0°, test 40 iteracji/krok','C0DistanceInterpolationTest.java':'C0 — klapka 0°, test interpolacji odległościowej'}.get(a['macro'],a['macro']) if a else 'C0 — ocena wyników'"
assert old in s;s=s.replace(old,new)
s=s.replace('Trwa kontrolowany test liczby iteracji wewnętrznych 15 → 40 na tej samej siatce.','Test 15 → 40 iteracji na krok nie wyjaśnił rozbieżności. Work zezwala wyłącznie na kontrolowane testy diagnostyczne 0°; geometria, siatka i fizyka pozostają takie same.')
s=s.replace('Dalszy test diagnostyczny dopiero po decyzji Work.','Test interpolacji odległościowej oceni związek między interpolacją, ograniczeniami turbulencji i błędem sił. Samo zbliżenie CL/CD nie oznacza akceptacji.')
changes[p]=s
for p,s in changes.items():
 backup=h/'runs/controller_snapshots'/stamp/p.name;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,backup);p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
print('Prepared queue/launcher support; existing controller still runs old loaded code. No job added or launched. Reload only after checkpoint and process checks.')
