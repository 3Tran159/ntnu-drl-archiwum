"""Project 2.0: current 012 baseline, short tests, and retained lessons only."""
import json,csv,math,datetime,sys,subprocess
from pathlib import Path
from html import escape as esc
P=Path(r"F:\ntnu\phase2_012_20261029")
R=Path(r"F:\ntnu\mesh_screening_20261028")
F=R/"flow012_short_20261029"
def read(p,default=None):
    try:return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError,ValueError):return default
def atomic(p,s):
    q=p.with_suffix(p.suffix+".new");q.write_text(s,encoding="utf-8");q.replace(p)
def history(p):
    try:
        with p.open() as f:rows=list(csv.DictReader(f))
        return [{k:float(v) if v not in ("",None) else None for k,v in row.items()} for row in rows if None not in row and all(row.get(k) for k in ["wall_seconds","physical_time_s","max_velocity_m_s","buoyancy_error_pct"])]
    except (OSError,ValueError):return []
def fmt(v,n=4):
    return "—" if v is None or not math.isfinite(v) else f"{v:,.{n}g}"
def chart(rows,key,title,unit,color):
    pts=[(r["physical_time_s"],r[key]) for r in rows if r.get(key) is not None and math.isfinite(r[key])]
    if len(pts)<2:return ""
    x0,x1=pts[0][0],pts[-1][0];lo=min(v for _,v in pts);hi=max(v for _,v in pts);pad=max((hi-lo)*.1,abs(hi)*.001,1e-9);lo-=pad;hi+=pad
    line=" ".join(f"{55+385*(x-x0)/max(x1-x0,1e-12):.2f},{150-115*(y-lo)/(hi-lo):.2f}" for x,y in pts)
    return f'<figure><figcaption>{esc(title)} [{unit}]</figcaption><svg viewBox="0 0 460 190" role="img" aria-label="{esc(title)}"><path d="M55 30V150H445" fill="none" stroke="#9aadc2"/><polyline points="{line}" fill="none" stroke="{color}" stroke-width="2.5"/><text x="4" y="40">{fmt(hi,3)}</text><text x="4" y="150">{fmt(lo,3)}</text><text x="55" y="171">{fmt(x0,3)}</text><text x="365" y="171">{fmt(x1,3)} s</text></svg></figure>'
now=datetime.datetime.now(datetime.timezone.utc)
exitinfo=read(F/"run_exit.json");live=(F/"process.json").exists() and not exitinfo
stages=[];sections=[]
observations=read(P/"observations.json",{})
for name,label,u in [("H0_0ms","2.1 · Woda nieruchoma · 0 m/s",0),("F18_18ms","2.2 · Przepływ bez fal · 18 m/s",18)]:
    d=F/name;setup=read(d/"setup.json",{});done=read(d/"completed.json");rows=history(d/"history.csv");last=rows[-1] if rows else {};peak=max((r["max_velocity_m_s"] for r in rows),default=None)
    if done:status="Zakończony test diagnostyczny" if done.get("guard_passed") else "Przerwany — wymaga kontroli"
    elif rows:status="Trwa obliczanie" if live else "Przerwany / brak potwierdzenia zakończenia"
    elif setup:status="Inicjalizacja" if live else "Nie ukończono inicjalizacji"
    elif u==18 and (F/"F18_SKIPPED.txt").exists():status="Wstrzymany po teście 0 m/s"
    else:status="Oczekuje" if not exitinfo else "Nie wykonano"
    stats=[("Status",status),("Liczba kroków",str(len(rows))),("Czas fizyczny [s]",fmt(last.get("physical_time_s"))),("Krok dt [s]",fmt(setup.get("dt_s"))),("Czas pracy solvera [s]",fmt(last.get("wall_seconds"))),("Średnio [s/krok]",fmt(last.get("wall_seconds",0)/len(rows)) if rows else "—"),("Maks. prędkość na końcu [m/s]",fmt(last.get("max_velocity_m_s"))),("Największa prędkość w przebiegu [m/s]",fmt(peak)),("Maks. CFL na końcu",fmt(last.get("max_convective_CFL"))),("Fx połowy płata [N]",fmt(last.get("Fx_half_N"))),("Fz połowy płata, z wyporem [N]",fmt(last.get("Fz_half_N"))),("y+ średnie po polu / min / max"," / ".join(fmt(last.get(k)) for k in ["foil_mean_yplus","foil_min_yplus","foil_max_yplus"]))]
    if u:
        stats += [("CD",fmt(last.get("CD"),6)),("CL całkowite, z wyporem",fmt(last.get("CL_total"),6)),("CL po odjęciu nominalnego wyporu",fmt(last.get("CL_buoyancy_subtracted"),6))]
    else:
        stats += [("Oczekiwany wypór połowy płata [N]",fmt(setup.get("expected_hydrostatic_Fz_N"))),("Odchylenie Fz od wyporu [%]",fmt(last.get("buoyancy_error_pct"))),("CL / CD","Nie definiujemy dla U = 0")]
    table="".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k,v in stats)
    note="Kontrola hydrostatyki i prędkości pasożytniczych; y+ przy U=0 nie służy do doboru warstw dla 18 m/s." if not u else "Wartości rozruchowe. CL po odjęciu nominalnego wyporu jest diagnostyką, a nie osobno zwalidowaną siłą hydrodynamiczną."
    note += "<ul>"+"".join("<li>"+esc(t)+"</li>" for t in observations.get(name,[]))+"</ul>"
    force_rows=rows[4:] if u and len(rows)>5 else rows
    note += "<p>Wykresy sił dla 18 m/s pokazują kroki od 5. Pełny impuls rozruchowy pozostaje w history.csv.</p>" if u and len(rows)>5 else ""
    plots=chart(force_rows,"Fx_half_N","Siła Fx"+(" · krok 5+" if u and len(rows)>5 else ""),"N","#246bce")+chart(force_rows,"Fz_half_N","Siła Fz, z wyporem"+(" · krok 5+" if u and len(rows)>5 else ""),"N","#148464")+chart(rows,"max_convective_CFL","Maksymalny CFL","–","#ba5e18")+(chart(rows,"foil_mean_yplus","Średnie y+ po powierzchni","–","#7951bd") if u else chart(rows,"max_velocity_m_s","Maksymalna prędkość pasożytnicza","m/s","#7951bd"))
    checkpoint=f"<p><code>{esc(str(d/'checkpoint.sim'))}</code></p>" if (d/"checkpoint.sim").exists() else ""
    sections.append(f'<section><h2>{label}</h2><p class="badge">{status}</p><div class="columns"><table>{table}</table><div><p>{note}</p><p>24 procesy CPU; niezależna inicjalizacja. Ustawienie cofającej się fazy na wylocie powiązano z płaską powierzchnią Calm.</p>{checkpoint}</div></div><div class="plots">{plots}</div></section>')
    stages.append({"id":name,"speed_m_s":u,"status":status,"setup":setup,"completed":done,"latest":last,"history_rows":len(rows)})
lessons=[
("Geometria przed solverem","Przed siatkowaniem sprawdzamy źródło DAT/CAD, t/c, camber, skalę, przekroje i przypisanie ściany. Poprzedni HF_v2 miał 10%, mimo założenia 12%."),
("Siatkowanie jest wykonalne","Poprzedni etap potwierdził, że automatyzacja i generowanie siatek z pryzmami działają. Nie potwierdził dokładności rozwiązania dla docelowego płata 012."),
("Koszt decyduje o planie","Siatki około 14–16 mln komórek były zbyt kosztowne na tym komputerze. Około 20 dni było ekstrapolacją tempa rozruchu na jeden czas c/U, a nie prognozą osiągnięcia zbieżności."),
("Pryzmy nie są jedynym kryterium","Kontrolujemy lokalne zanikanie warstw, y+, jakość, skewness, volume change, CFL i historię sił. 99,9% pełnych warstw to cel roboczy, nie samodzielny dowód poprawności."),
("Mała siatka bez skalowania płata","C003 ma 1 165 391 komórek przy zachowaniu skali geometrycznej. Nadal wymaga testu solvera i późniejszej oceny wpływu rozdzielczości."),
("Wyniki starej geometrii pozostają historyczne","Siły, CL/CD i y+ z nocnych D001–D004 nie są wynikami etapu 2.0. Nie przenosimy ich do aktualnych wykresów ani nie przeliczamy nowym polem odniesienia.")
]
li="".join(f"<li><strong>{esc(a)}.</strong> {esc(b)}</li>" for a,b in lessons)
activity=next((x["status"]+" · "+x["id"] for x in reversed(stages) if x["setup"]),"Uruchamianie STAR / oczekiwanie na licencję")
if exitinfo:activity="Sekwencja zakończona" if exitinfo.get("returncode")==0 and (F/"sequence_completed.json").exists() else "Sekwencja wymaga sprawdzenia — błąd wykonania"
events=[]
def event(path,title,detail):
    if path.exists():events.append({"time":datetime.datetime.fromtimestamp(path.stat().st_mtime,datetime.timezone.utc).isoformat(),"work":title,"finding":detail})
event(P/"project_manifest.json","Start etapu 2.0","Zweryfikowana geometria 012 i C003; wnioski ze starej geometrii zachowane jako historia.")
event(F/"attempt_01_compile/run_exit.json","Poprawka makra przed solverem","Dodano brakujący import klas diagnostycznych. Pierwsza próba zakończyła się przed wykonaniem kroków CFD.")
event(F/"postprocess/hotspot_summary.json","Lokalna kontrola końcowego pola","8 komórek z prędkością >36 m/s przy y≈4,06 m; CFL >2: 6 komórek tam i 2 przy y≈5,50 m. Bez kolejnych kroków solvera.")
event(F/"process.json","Uruchomienie sekwencji 0 → 18 m/s","24 procesy CPU, osobna inicjalizacja każdego przypadku, zapis danych po każdym kroku.")
for stage in stages:
    folder=F/stage["id"]
    event(folder/"setup.json","Przygotowano "+stage["id"],"Hydrostatyczna inicjalizacja, płaska powierzchnia Calm; dt="+str(stage["setup"].get("dt_s"))+" s.")
    event(folder/"completed.json","Zakończono "+stage["id"],stage["status"]+"; historia, diagnostyka i checkpoint zapisane.")
events=sorted(events,key=lambda e:e["time"],reverse=True)
log_html="<section><h2>Dziennik pracy etapu 2.0</h2><table><tr><th>Czas lokalny</th><th>Praca i wniosek</th></tr>"+"".join("<tr><td>"+datetime.datetime.fromisoformat(e["time"]).astimezone().strftime("%H:%M:%S")+"</td><td><strong>"+esc(e["work"])+"</strong><br>"+esc(e["finding"])+"</td></tr>" for e in events)+"</table></section>"
atomic(P/"work_log.json",json.dumps(events,ensure_ascii=False,indent=2))
from q2d_panel import panel
q2d_html,q2d_state=panel()
activity=q2d_state.get('activity',activity)
live=q2d_state.get('live',False)
stamp=now.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
refresh='<meta http-equiv="refresh" content="15">' if live else ""
html=f"""<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{refresh}<title>NWAR 2.0 — geometria 012</title><style>
:root{{font-family:Segoe UI,Arial,sans-serif;color:#152c43;background:#edf2f7}}body{{max-width:1180px;margin:32px auto;padding:0 20px}}header{{background:#132f4b;color:white;padding:28px;border-radius:14px}}h1{{margin:6px 0 12px;font-size:32px}}h2{{font-size:22px}}p,li{{line-height:1.55}}section{{background:white;padding:24px;margin:20px 0;border:1px solid #dce4ed;border-radius:12px}}.eyebrow{{text-transform:uppercase;letter-spacing:2px;color:#7ce0c4;font-size:12px}}.badge{{display:inline-block;padding:5px 11px;border-radius:7px;background:#e9f0f8;color:#234568}}.metrics,.columns,.plots{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}.metrics{{grid-template-columns:repeat(4,1fr)}}.metric strong{{font-size:26px;display:block}}small,.muted{{color:#586c80}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:8px 5px;border-bottom:1px solid #e6edf4;text-align:left}}th{{font-weight:500}}td{{font-variant-numeric:tabular-nums}}code{{overflow-wrap:anywhere;font-size:12px}}figure{{margin:0;background:#f7f9fc;padding:12px;border-radius:8px}}figcaption{{font-weight:600}}svg{{width:100%;font-size:12px;fill:#53667c}}li{{margin-bottom:12px}}a{{color:#1368b3}}header a{{color:#8ee0cc}}@media(max-width:750px){{.columns,.plots,.metrics{{grid-template-columns:1fr}}}}
</style></head><body><header><div class="eyebrow">NTNU · Negative wave-added resistance</div><h1>Etap 2.0 · Zweryfikowana geometria 012</h1><p>{esc(activity)}</p><p>Aktualizacja: {stamp}. Dane zapisane w HTML; podczas pracy strona odświeża się co 15 s.</p></header>
{q2d_html}
<section><h2>Wcześniejszy test 3D · punkt odniesienia</h2><div class="metrics"><div class="metric"><strong>11,998%</strong><small>zmierzona grubość / cięciwa</small></div><div class="metric"><strong>2,500%</strong><small>wygięcie profilu</small></div><div class="metric"><strong>1 165 391</strong><small>komórki · C003</small></div><div class="metric"><strong>94,56%</strong><small>powierzchnia z pełnymi 15 pryzmami</small></div></div>
<p>Rozpiętość 11 m, cięciwa root 1,19 m, S połowy płata 5,450434 m². Zgodność z wybranym rekonstruowanym DAT sprawdzona w 7 przekrojach w NX i STAR. Nie jest to jeszcze niezależna walidacja profilu z publikacji.</p><p>Siatka: zero ujemnych objętości, otwartych i zdegenerowanych komórek; dowolne pryzmy na 100% powierzchni. Do lokalnej kontroli: 187 komórek z quality &lt;0,01 i 283 ze skewness &gt;80°.</p>
<p><code>F:\\ntnu\\geometry_012_20261029\\HF_012_v3.x_t</code><br><code>F:\\ntnu\\mesh_screening_20261028\\coarse012_C003\\HF_012_C003_mesh.sim</code></p></section>
{''.join(sections)}
<section><h2>2.3 · Plan po wcześniejszym teście 3D — historia</h2><p>Najpierw lokalna kontrola pryzm przy krawędzi natarcia (y około 4,06 m) i końcówce płata, ocena rozruchu i dobór kroku czasowego względem kosztu. Następnie kalibracja fali i domeny, porównywalna baza bez fal oraz seria do obliczenia różnicy oporu. Te krótkie testy nie potwierdzają jeszcze zbieżności sił.</p></section>
<section><h2>Lekcje z etapu 1.0 · noc 28–29 października</h2><ol>{li}</ol><p><a href="file:///F:/ntnu/mesh_screening_20261028/phase1_dashboard.html">Archiwum poprzedniego dashboardu i wyników 010</a></p></section>
{log_html}<footer><p>Pełne logi, historie i checkpointy: <code>{esc(str(F))}</code>. Główny punkt wejścia 2.0: <code>{esc(str(P/'dashboard.html'))}</code>.</p></footer></body></html>"""
atomic(P/"dashboard.html",html)
summary={"project_phase":"2.0","updated_at":now.isoformat(),"geometry":"HF_012_v3","mesh":"C003_012","activity":activity,"stages":stages,"lessons":[{"title":a,"conclusion":b} for a,b in lessons]}
atomic(P/"status.json",json.dumps(summary,ensure_ascii=False,indent=2))
atomic(R/"night_20261028/current_activity.json",json.dumps({"updated_at":now.isoformat(),"text":"ETAP 2.0 — "+activity+"; aktualne dane w F:/ntnu/phase2_012_20261029/dashboard.html"},ensure_ascii=False))
# The established entry points now open the clean phase-2 view; the old generator retains the archive.
for dest in [R/"dashboard.html",R/"results/dashboard.html"]:
    atomic(dest,html)
if (R/"delivery").exists():
    for dest in (R/"delivery").glob("NTNU_mesh_screening*/dashboard.html"):atomic(dest,html)
print(json.dumps({"phase":"2.0","stages":[{"id":s["id"],"status":s["status"],"rows":s["history_rows"]} for s in stages]}))
