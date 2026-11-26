from pathlib import Path
p=Path(r"F:\ntnu\mesh_screening_20261028\night_20261028\update_dashboard.py")
s=p.read_text(encoding="utf-8")
old="    html=template.replace('/*__DATA__*/null',payload)"
new=old+"\n    from geometry012_panel import render_panel\n    html=html.replace('</header>','</header>'+render_panel(root),1)"
if "from geometry012_panel import render_panel" not in s:
    assert s.count(old)==1
    backup=p.with_name("update_dashboard.before_geometry012.py")
    assert not backup.exists()
    backup.write_text(s,encoding="utf-8")
    p.write_text(s.replace(old,new),encoding="utf-8")
print("Dashboard geometry panel integrated.")
