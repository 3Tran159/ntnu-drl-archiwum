from pathlib import Path
p=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029\verify_section.py")
s=p.read_text().replace("chord=xmax-xmin","extent=xmax-xmin;chord=1190.0")
s=s.replace('"chord_m":chord/1000','"chord_m":chord/1000,"x_extent_m":extent/1000,"chord_convention":"Nominal CAD/DAT chord, not x bounding-box width; cambered profile nose extends slightly ahead of nominal LE"')
p.write_text(s)
exec(compile(s,str(p),"exec"))
