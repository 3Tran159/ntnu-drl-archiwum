from pathlib import Path
p=Path(__file__).resolve().parent
f=p/"plot_aft_cycles.py"
s=f.read_text(encoding="utf8")
s=s.replace('    runs=[','    diagnostic=REPORT/"RESULT_DT0333MS.json"\n    if diagnostic.exists():\n        result.update(json.loads(diagnostic.read_text()))\n    runs=[',1)
s=s.replace('("DT100MS","1.0","#c56732")','("DT100MS","1.0","#c56732"),("DT0333MS","0.333","#824378")')
f.write_text(s,encoding="utf8")
f=p/"plot_mesh_extrema.py"
s=f.read_text(encoding="utf8").replace('(("DT050MS",100,300),("DT100MS",50,150))','(("DT0333MS",150,450),("DT050MS",100,300),("DT100MS",50,150))')
f.write_text(s,encoding="utf8")
f=p/"summarize_aft_cycles.py"
s=f.read_text(encoding="utf8")
s=s.replace('    combined = {}','    diagnostic=REPORT/"RESULT_DT0333MS.json"\n    if diagnostic.exists():\n        result.update(json.loads(diagnostic.read_text()))\n    combined = {}')
s=s.replace('for tag in ("DT050MS","DT100MS"):', 'for tag in ("DT050MS","DT100MS","DT0333MS"):')
s=s.replace('    if len(combined)==2:','    if {"DT050MS","DT100MS"}<=combined.keys():')
f.write_text(s,encoding="utf8")

