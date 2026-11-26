from pathlib import Path

root=Path(__file__).resolve().parent
d=root/"TRAILING_EDGE_LAYER_RELIEF"
original=root/"AFT_ONLY_PRESSURE_GATE"
p=(original/"run_gap.py").read_text(encoding="utf8")
start=p.index("    audit =")
end=p.index("    macro =",start)
p=p[:start]+'''    audit = json.loads((OUT/"MESH_AUDIT.json").read_text())
    mesh = OUT/"mesh_2d.msh"
'''+p[end:]
start=p.index('            ("BASELINE",')
end=p.index('            ("DT050MS",',start)
p=p[:start]+'''            ("BASELINE",dict(fresh=True,gap_baseline_only=True,dt=.0005,steps=0,
                             steady_ramp_iterations=200,u_initial_m_s=.10,steady_max_iterations=1550,
                             mesh_override=mesh.as_posix(),mesh_override_sha256=audit["mesh_sha256"])),
'''+p[end:]
p=p.replace('ACTIVE_GAP25_FLAP_MARGIN_','ACTIVE_GAP25_TIP_RELIEF_')
(d/"run_gap.py").write_text(p,encoding="utf8")
(d/"MiniVofStokes.java").write_text((original/"MiniVofStokes.java").read_text(encoding="utf8"),encoding="utf8")

