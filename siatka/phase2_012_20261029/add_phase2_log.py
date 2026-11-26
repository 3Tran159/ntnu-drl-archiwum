from pathlib import Path
p=Path(r"F:\ntnu\phase2_012_20261029\build_dashboard.py")
s=p.read_text(encoding="utf-8")
s=s.replace('if exitinfo:activity="Sekwencja zakończona" if exitinfo.get("returncode")==0 else "Sekwencja wymaga sprawdzenia — błąd wykonania"','if exitinfo:activity="Sekwencja zakończona" if exitinfo.get("returncode")==0 and (F/"sequence_completed.json").exists() else "Sekwencja wymaga sprawdzenia — błąd wykonania"')
needle='stamp=now.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")'
replacement='''events=[]
def event(path,title,detail):
    if path.exists():events.append({"time":datetime.datetime.fromtimestamp(path.stat().st_mtime,datetime.timezone.utc).isoformat(),"work":title,"finding":detail})
event(P/"project_manifest.json","Start etapu 2.0","Zweryfikowana geometria 012 i C003; wnioski ze starej geometrii zachowane jako historia.")
event(F/"attempt_01_compile/run_exit.json","Poprawka makra przed solverem","Dodano brakujący import klas diagnostycznych. Pierwsza próba zakończyła się przed wykonaniem kroków CFD.")
event(F/"process.json","Uruchomienie sekwencji 0 → 18 m/s","24 procesy CPU, osobna inicjalizacja każdego przypadku, zapis danych po każdym kroku.")
for stage in stages:
    folder=F/stage["id"]
    event(folder/"setup.json","Przygotowano "+stage["id"],"Hydrostatyczna inicjalizacja, płaska powierzchnia Calm; dt="+str(stage["setup"].get("dt_s"))+" s.")
    event(folder/"completed.json","Zakończono "+stage["id"],stage["status"]+"; historia, diagnostyka i checkpoint zapisane.")
events=sorted(events,key=lambda e:e["time"],reverse=True)
log_html="<section><h2>Dziennik pracy etapu 2.0</h2><table><tr><th>Czas lokalny</th><th>Praca i wniosek</th></tr>"+"".join("<tr><td>"+datetime.datetime.fromisoformat(e["time"]).astimezone().strftime("%H:%M:%S")+"</td><td><strong>"+esc(e["work"])+"</strong><br>"+esc(e["finding"])+"</td></tr>" for e in events)+"</table></section>"
atomic(P/"work_log.json",json.dumps(events,ensure_ascii=False,indent=2))
stamp=now.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")'''
if needle in s and "log_html=" not in s:s=s.replace(needle,replacement).replace('<footer><p>Pełne logi','{log_html}<footer><p>Pełne logi')
p.write_text(s,encoding="utf-8")
print("Phase 2 timestamped work log enabled")
