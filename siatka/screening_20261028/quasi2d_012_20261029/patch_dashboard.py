from pathlib import Path
import json,datetime,shutil
p=Path(r"F:\ntnu\phase2_012_20261029\build_dashboard.py")
backup=p.with_name("build_dashboard_before_q2d.py")
if not backup.exists():shutil.copy2(p,backup)
s=p.read_text(encoding="utf-8")
if "from q2d_panel import panel" not in s:
 s=s.replace("stamp=now.astimezone()", "from q2d_panel import panel\nq2d_html,q2d_state=panel()\nactivity=q2d_state.get('activity',activity)\nlive=q2d_state.get('live',False)\nstamp=now.astimezone()")
 s=s.replace("<section><h2>Punkt startowy na dziś</h2>","{q2d_html}\n<section><h2>Wcześniejszy test 3D · punkt odniesienia</h2>")
 p.write_text(s,encoding="utf-8")
q=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029")
(q/"status.json").write_text(json.dumps({"activity":"Quasi-2D: geometria gotowa, konfiguracja siatki wyciąganej","live":True},ensure_ascii=False),encoding="utf-8")
(q/"work_log.json").write_text(json.dumps([{"time":datetime.datetime.now().astimezone().isoformat(),"work":"Stały przekrój 012 utworzony w NX","finding":"Cięciwa 1,19 m i kształt profilu zachowane. Osobny CAD o taper=1; wycinek domeny ma szerokość 0,02 m. Przygotowanie directed mesh z jedną warstwą."}],ensure_ascii=False,indent=2),encoding="utf-8")
