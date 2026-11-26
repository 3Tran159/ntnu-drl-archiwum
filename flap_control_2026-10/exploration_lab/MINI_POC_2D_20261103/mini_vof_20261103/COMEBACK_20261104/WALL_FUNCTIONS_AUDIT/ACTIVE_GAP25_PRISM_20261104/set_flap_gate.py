from pathlib import Path

d = Path(__file__).resolve().parent/"AFT_ONLY_PRESSURE_GATE"
p = d/"MiniVofStokes.java"
s = p.read_text(encoding="utf8")
old = '''  if(Math.min(Math.min(cells,wall),Math.min(flap,gap))<=FLAP_LIMIT)
   return "HOLD_AFT_PRESSURE_MARGIN";'''
new = '''  if(flap<=FLAP_LIMIT)return "HOLD_FLAP_PRESSURE_MARGIN";'''
assert s.count(old)==1
s=s.replace(old,new)
s=s.replace('"limit_Pa",FLAP_LIMIT,"full_foil_cavitation_assessment",false,',
            '"limit_Pa",FLAP_LIMIT,"gate_surface","flap_wall_only","full_foil_cavitation_assessment",false,')
s=s.replace("pflap_min_Pa,pgap_min_Pa\\n","pflap_min_Pa,pgap_min_Pa,flap_vapor_margin_Pa\\n")
s=s.replace('+maxLoc("CFL",1)+","+pflap+","+pgap+"\\n");',
            '+maxLoc("CFL",1)+","+pflap+","+pgap+","+(pflap-2339.214766776897)+"\\n");')
p.write_text(s,encoding="utf8")

