from pathlib import Path

root=Path(__file__).resolve().parent
d=root/"SEALED_SHARP_MATCHED_OUTER"
source=root/"SEALED_OUTER_MESH_GAPPED"
s=(source/"MiniVofStokes.java").read_text(encoding="utf8")
start=s.index("  String radial=smooth(")
end=s.index("  UserFieldFunction f=",start)
s=s[:start]+'''  String a="("+command+"*"+smooth(x+"/<.035 m>")+"*"+smooth("(<1.40 m>-"+radius+")/<1.10 m>")+")";
'''+s[end:]
s=s.replace("Rigid gapped flap with local mesh deformation","Sharp sealed flap with localized transition")
(d/"MiniVofStokes.java").write_text(s,encoding="utf8")
p=(source/"run_gap.py").read_text(encoding="utf8").replace("ACTIVE_GAP25_MATCHED_OUTER_","ACTIVE_SHARP_SEALED_MATCHED_")
p=p.replace('            ("DT050MS",dict(seeded_single_phase=True, dt=.0005, steps=400)),\n            ("DT100MS",dict(seeded_single_phase=True, dt=.001, steps=200)),',
            '            ("DT0333MS",dict(seeded_single_phase=True, dt=.2/600, steps=600)),')
(d/"run_sharp_sealed.py").write_text(p,encoding="utf8")

