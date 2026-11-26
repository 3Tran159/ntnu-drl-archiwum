from pathlib import Path

d=Path(__file__).resolve().parent
p=d/"MATCHED_FIXED_PROTOCOL"/"MiniVofStokes.java"
s=p.read_text(encoding="utf8")
old='  String a="("+command+"*"+smooth(x+"/<.035 m>")+"*"+smooth("(<1.40 m>-"+radius+")/<1.10 m>")+")";'
new='''  String blend=smooth(x+"/<.035 m>");
  if(b("fixed_protocol")&&b("seeded_single_phase")){
   String radial=smooth("(<.03755 m>-"+radius+")/<.00235 m>");
   String aft=smooth("("+x+"+<.00745 m>)/<.00745 m>");
   blend="max("+radial+","+aft+")";
  }
  String a="("+command+"*"+blend+"*"+smooth("(<1.40 m>-"+radius+")/<1.10 m>")+")";'''
assert s.count(old)==1
p.write_text(s.replace(old,new),encoding="utf8")
p=d/"plot_aft_cycles.py"
s=p.read_text(encoding="utf8")
s=s.replace('runs=[(read_history(SEALED/"single_phase.csv"),"Legacy blunt sealed | 1.0 ms","#576979","--")]','runs=[]')
s=s.replace('    if len(runs)==1:\n        return','    if not runs:\n        return')
s=s.replace('Legacy sealed curve is a reference only | sharp sealed geometry has its own mesh figure','Gapped exploratory trajectory | stopped at the flap pressure margin')
p.write_text(s,encoding="utf8")

