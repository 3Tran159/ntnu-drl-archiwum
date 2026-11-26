from pathlib import Path

p=Path(__file__).resolve().parent/"plot_aft_cycles.py"
s=p.read_text(encoding="utf8")
s=s.replace('    runs=[(read_history(SEALED/"single_phase.csv"),"Sealed prototype | 1.0 ms","#576979","--")]',
'''    sharp_result=OUT/"SEALED_SHARP_MATCHED_OUTER"/"RESULT.json"
    sharp=json.loads(sharp_result.read_text()).get("DT0333MS") if sharp_result.exists() else None
    if sharp and sharp.get("full_cycle"):
        path=Path(sharp["checkpoint"]).parent/"single_phase.csv"
        runs=[(read_history(path),"Sharp sealed | 0.333 ms","#576979","--")]
    else:
        runs=[(read_history(SEALED/"single_phase.csv"),"Legacy blunt sealed | 1.0 ms","#576979","--")]''')
s=s.replace('    comparison = ("Identical outer mesh | different foil-wall discretization and wall layers"\n                  if REPORT.name=="SEALED_OUTER_MESH_GAPPED" else\n                  "Different outer domains and foil-wall meshes")',
'''    comparison = ("Matched outer mesh and sharp trailing edges | local meshes differ"
                  if sharp and sharp.get("full_cycle") else
                  "Legacy sealed curve is a reference only | sharp sealed geometry has its own mesh figure")''')
p.write_text(s,encoding="utf8")

