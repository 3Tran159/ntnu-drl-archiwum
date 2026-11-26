import csv,json,datetime,hashlib,shutil
from pathlib import Path
Q=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029")
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for block in iter(lambda:f.read(4*1024*1024),b""):h.update(block)
 return h.hexdigest()
S=read(Q/"campaign_summary.json")
assert len(S["runs"])==14 and all(x["completed"] for x in S["runs"])
for name in ["gpu.exit.json","cpu24.exit.json","gpu_m03.exit.json"]:
 assert read(Q/name)["returncode"]==0,name
assert (Q/"session_completed.txt").exists()
runs={(x["mesh"],x["run"]):x for x in S["runs"]}
out={}
for mesh in ["M02_GPU","M03_GPU"]:
 p=Q/mesh/"F18_dt1000us_long"
 with (p/"history.csv").open() as f:hist=[{k:float(v) if v else None for k,v in row.items()} for row in csv.DictReader(f)]
 start=min(hist,key=lambda x:abs(x["physical_time_s"]-.16));end=hist[-1]
 out[mesh]={"final":end,"change_0p16_to_0p20_pct":{k:100*(end[k]/start[k]-1) for k in ["CD","CL_total"]}}
 for stage in ["F18_dt500us","F18_dt1000us_long"]:
  fields=Q/mesh/stage/"fluid_final_fields.csv"
  if not fields.exists():continue
  with fields.open() as f:rows=[{k:float(v) for k,v in row.items()} for row in csv.DictReader(f)]
  alpha=next(k for k in rows[0] if "Fraction" in k);cfl=next(k for k in rows[0] if "Courant" in k)
  inter=[x for x in rows if .01<x[alpha]<.99]
  result={"global_max_CFL":max(x[cfl] for x in rows),"interface_0p01_to_0p99_cells":len(inter),"interface_max_CFL":max((x[cfl] for x in inter),default=None),"note":"Physical-step convective CFL; VOF dynamic substeps target 0.5, maximum20. This is not the substep CFL."}
  (fields.parent/"interface_cfl.json").write_text(json.dumps(result,indent=2))
  out[mesh][stage+"_cfl"]=result
a=out["M02_GPU"]["final"];b=out["M03_GPU"]["final"]
out["M02_relative_to_M03_at_0p2s_pct"]={k:100*(a[k]/b[k]-1) for k in ["CD","CL_total"]}
out["M03_GPU_speedup_vs_CPU8"]=runs[("M03","F18_dt500us")]["seconds_per_step"]/runs[("M03_GPU","F18_dt500us")]["seconds_per_step"]
out["M03_GPU_speedup_vs_CPU24"]=runs[("M03_CPU24","F18_dt500us")]["seconds_per_step"]/runs[("M03_GPU","F18_dt500us")]["seconds_per_step"]
src=Q/"M03_GPU/Q2D_012_review.sim";dest=Path(r"F:\ntnu\Q2D_012_20261029.sim")
assert read(Q/"M03_GPU/review_settings.json")["gpu_count"]==1
if not dest.exists():shutil.copy2(src,dest)
assert sha(src)==sha(dest)
cad=Path(r"F:\ntnu\geometry_012_20261029\HF_012_v3.prt")
cad_hash=sha(cad);assert cad_hash=="044d97c2a3f9cd5dd816b5a20d2c9e257e61fceb9fc8f80f343d7470917e5000"
baseline=Path(r"F:\ntnu\geometry_012_20261029\HF_012_baseline_unmeshed.sim")
baseline_hash=sha(baseline);assert baseline_hash==sha(Q/"source_copy.sim")
out["saved_sim"]=str(dest);out["saved_sim_sha256"]=sha(dest)
out["original_corrected_cad_sha256"]=cad_hash;out["original_baseline_sim_sha256"]=baseline_hash
out["originals_unchanged"]=True
out["review_settings"]=read(Q/"M03_GPU/review_settings.json")
out["run_count"]=len(S["runs"])
(Q/"final_summary.json").write_text(json.dumps(out,indent=2))
conclusions=[
"Zakończono 14 prób na 3 siatkach (37 411 / 66 707 / 123 256 komórek), przy 0 i 18 m/s. Zachowano cięciwę 1,19 m i grubość 12%; bez skalowania fizycznej geometrii.",
"W każdej siatce dokładnie jedna warstwa przez szerokość. Zero ujemnych, niezamkniętych i zdegenerowanych komórek; min quality 0,149–0,188, min volume change 0,0186–0,0651, max skew 46,7–52,6°. Są to wskaźniki diagnostyczne, a nie dowód dokładności sił.",
"Co najmniej 15 kolejnych regularnych warstw: M01 97,07%, M02 97,97%, M03 98,53%. Niedobory skupione przy ostrej krawędzi spływu; 100% obwodu ma przynajmniej jedną warstwę. Kryterium 99,9% samo nie przesądza o przydatności mesha.",
"Na M01 dt 0,1 → 0,5 ms zmienia CD o +0,14%, CL o −0,13% przy t=0,02 s; na M02 dt 0,25 → 0,5 ms około −0,08% dla obu. Dłuższy przebieg z dt=1 ms pozostaje próbą rozruchową bez osobnego testu niezależności czasowej na t=0,2 s.",
"GPU rzeczywiście aktywne (1 GPU potwierdzone przez STAR). M03, 40 kroków dt=0,5 ms: CPU8 107,9 s, CPU24 75,2 s, GPU 53,3 s. GPU jest 2,02× szybsze od CPU8 i 1,41× od CPU24. Czasy obejmują solver i raportowanie; uruchamianie GPU dodaje narzut.",
"Dłuższe próby GPU, 200 kroków dt=1 ms do t=0,2 s: M02 172,3 s; M03 280,0 s. M03: Fx=67,345 N, Fz=950,313 N na wycinek 0,02 m; CD=0,017467, CL=0,246476 (z wyporem), CL bez nominalnego wyporu=0,240584.",
"Brak niezależności od siatki: przy t=0,2 s M02 ma CD=0,028035, M03 CD=0,017467 (M02 około 60,5% wyżej). CL odpowiednio 0,229725 i 0,246476. Siły wciąż ewoluują. M03 to roboczy kandydat do dalszej diagnostyki, nie zaakceptowany wynik NWAR.",
"M03 GPU przy t=0,2 s: y+ średnie=44,93, min=4,64, max=255,17. To nie siatka z y+≈1. Lokalne rozkłady y+ i krawędź spływu wymagają uwzględnienia przy wyborze sposobu traktowania ściany.",
"Test 0 m/s M02: przy profilu max |U|≈0,00021 m/s; globalne 0,427 m/s dotyczy niemal czystego powietrza przy powierzchni. W niemal czystej wodzie max≈0,0149 m/s, w interfejsie≈0,179 m/s. Przed falami potrzebna kontrola spoczynkowej powierzchni.",
"CFL globalny w cienkich komórkach przy ścianie i CFL interfejsu są osobnymi diagnostykami. Pliki interface_cfl.json podają oba; aktywne subkroki VOF z celem 0,5. Duże globalne CFL nie jest samodzielnym dowodem błędu ani dokładności.",
"Gotowy plik roboczy: F:\\ntnu\\Q2D_012_20261029.sim. Zapisany przy t=0,2 s; limit dalszego biegu ustawiony na t=0,25 s. Oryginalny CAD i bazowy SIM sprawdzone sumami SHA-256, bez zmian.",
"Następna praca: wyjaśnić różnicę oporu M02/M03 (LE, ciśnienie, rozruch), potwierdzić stabilizację sił i dt, sprawdzić interfejs; dopiero potem porównywać warunki spokojnej wody i fal. Quasi-2D opisuje przekrój, bez wirów końcowych i oporu indukowanego całego płata."
]
(Q/"conclusions.json").write_text(json.dumps(conclusions,ensure_ascii=False,indent=2),encoding="utf-8")
events=read(Q/"work_log.json")
new=[
("2026-10-29T14:00:00+01:00","Podsumowanie testów: audyt mesha","Trzy siatki z prawidłową jednowarstwową topologią. Przejście CAD powoduje maks. przesunięcie x/z między bokami 0,152 mm; to quasi-2D, nie idealnie identyczna ekstrudowana siatka."),
]
now=datetime.datetime.now().astimezone().isoformat(timespec="seconds")
# Record actual completion now; individual test timestamps are derived by dashboard from completion files.
for work,finding in [
("Podsumowanie audytu mesha","Trzy siatki, jedna warstwa przez span, zero ujemnych objętości. Minima jakości zlokalizowane; niedobory regularnych warstw przy TE. Maks. różnica x/z boków po projekcji CAD 0,152 mm."),
("Zakończono porównanie CPU8 / CPU24 / GPU","M03 przy identycznym dt i liczbie kroków: 107,9 / 75,2 / 53,3 s. Jedna karta aktywna potwierdzona przez API STAR; wszystkie zadania kolejno."),
("Dłuższe testy GPU i ograniczenia wniosków","M02 i M03 doszły do t=0,2 s. Opór różni się o około 60,5% względem M03; nie potwierdzono niezależności sił od siatki. Na razie bez fal."),
("Zapis końcowy i przekazanie projektu","14 prób ukończonych. Gotowy Q2D_012_20261029.sim, limit t=0,25 s; zachowane wszystkie checkpointy, CSV i makra. Oryginalny poprawiony CAD i bazowy SIM niezmienione.")]:
 if not any(x["work"]==work for x in events):events.append({"time":now,"work":work,"finding":finding})
(Q/"work_log.json").write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8")
(Q/"status.json").write_text(json.dumps({"activity":"Zakończono 14 prób quasi-2D; wyniki rozruchowe, brak potwierdzonej niezależności sił od siatki","live":False,"updated":now},ensure_ascii=False,indent=2),encoding="utf-8")
readme=r"""QUASI-2D / PHASE 2.4 — 29 OCTOBER 2026
START HERE
Working STAR-CCM+ 2602 Double simulation:
F:\\ntnu\\Q2D_012_20261029.sim
Dashboard (self-contained; open directly in browser):
F:\\ntnu\\phase2_012_20261029\\dashboard.html

Three meshes and 14 pilot runs completed, including hydrostatic checks,
18 m/s starts, two short timestep comparisons, CPU8/CPU24/GPU benchmarks.
Final working file: M03, 123256 cells, exactly one spanwise layer,
b=0.02 m, chord=1.19 m, verified t/c=0.119979, camber/c=0.025003.
Original corrected CAD and baseline SIM are unchanged (SHA-256 checked).
This slice models a constant section; it does not resolve finite-span tip effects.
No incident waves have been run.

Open the working file for inspection. It contains the GPU result at t=0.2 s.
Physical stopping time is 0.25 s, intentionally bounded.
Restart compute hardware is selected when launching the STAR server.
Measured GPU configuration: -np 1 -gpgpu auto:1. GPU count was 1.
All pilot runs used first-order time integration and 20 inner iterations.

Final M03 GPU endpoint: Fx=67.344507 N, Fz=950.313431 N on the 2 cm slice.
CD=0.017466674, CL_total=0.246476147, CL_minus_nominal_buoyancy=0.240583889.
rho=1000 kg/m3; Sref=0.0238 m2; Uref=18 m/s. Divide slice force by 0.02 for N/m.
y+ area mean=44.9251, min=4.6390, max=255.1713.
These are STARTUP VALUES, NOT converged or mesh-independent NWAR results.

40 steps, dt=0.0005 s, M03: CPU8 107.9 s / CPU24 75.2 s / GPU 53.3 s.
200 steps, dt=0.001 s, GPU: M02 172.3 s / M03 280.0 s.
Runtime excludes launching/licensing, meshing and final save.
The complete M03 GPU batch, including both tests and overhead, took 558.1 s.

Do not label the meshes accepted solely from quality statistics.
At t=0.2 s CD differs by 60.5% (M02 relative to M03); CL is still changing.
15 consecutive regular layers: M01 97.07%, M02 97.97%, M03 98.53%;
shortfalls at the sharp trailing edge. Directed sweep drops PrismLayerNumber metadata.
Global near-wall CFL differs from interface CFL; inspect interface_cfl.json.
Review hydrostatic surface noise and local y+ before introducing waves.
Next: resolve mesh-dependent drag, establish force settling and timestep sensitivity;
then compare calm-water and wave cases using the same verified section setup.

Full evidence:
campaign_summary.json — all run endpoints, timing, short dt comparisons
final_summary.json — final comparisons, drift, hashes and review settings
M01/M02/M03 — mesh.sim, mesh.CGNS, quality and topology audits
M*_GPU, M03_CPU24 — backend benchmarks, checkpoint.sim, CSV histories
plots — actual mesh, pressure and force-history figures
work_log.json — activity and findings
Scripts/macros are preserved for reproducibility.
"""
(Q/"START_HERE.txt").write_text(readme,encoding="utf-8")
Path(r"F:\ntnu\Q2D_012_20261029_START_HERE.txt").write_text(readme,encoding="utf-8")
with (Q/"all_run_endpoints.csv").open("w",newline="",encoding="utf-8") as f:
 fields=["mesh","run","steps","seconds_per_step",*S["runs"][0]["last"].keys()]
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
 for x in S["runs"]:w.writerow({k:x[k] for k in ["mesh","run","steps","seconds_per_step"]}|x["last"])
print(json.dumps(out,indent=2))
