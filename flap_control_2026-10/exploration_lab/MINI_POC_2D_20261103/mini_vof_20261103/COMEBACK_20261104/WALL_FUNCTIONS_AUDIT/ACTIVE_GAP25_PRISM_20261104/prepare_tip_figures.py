from pathlib import Path
p=Path(__file__).resolve().parent
f=p/"plot_mesh_extrema.py"
s=f.read_text(encoding="utf8")
s=s.replace('OUTPUT = OUT/"AFT_ONLY_PRESSURE_GATE"', 'OUTPUT = Path(sys.argv[1]) if len(sys.argv)>1 else OUT/"AFT_ONLY_PRESSURE_GATE"\nGAP_MESH = OUTPUT if (OUTPUT/"plot_mesh.npz").exists() else OUT\nRUN_PREFIX = "ACTIVE_GAP25_TIP_RELIEF" if GAP_MESH==OUTPUT else "ACTIVE_GAP25_FLAP_MARGIN"')
s=s.replace('g=np.load(OUT/"plot_mesh.npz")','g=np.load(GAP_MESH/"plot_mesh.npz")')
s=s.replace('f"ACTIVE_GAP25_FLAP_MARGIN_{name}_*"','f"{RUN_PREFIX}_{name}_*"')
f.write_text(s,encoding="utf8")
f=p/"plot_aft_cycles.py"
s=f.read_text(encoding="utf8")
s=s.replace('SEALED = OUT.parents[1]','REPORT = Path(sys.argv[1]) if len(sys.argv)>1 else OUT/"AFT_ONLY_PRESSURE_GATE"\nSEALED = OUT.parents[1]')
s=s.replace('OUT/"AFT_ONLY_PRESSURE_GATE"/"RESULT.json"','REPORT/"RESULT.json"')
s=s.replace('OUT/"AFT_ONLY_PRESSURE_GATE"/"CL_CD_vs_flap_deflection_overlay_EN.png"','REPORT/"CL_CD_vs_flap_deflection_overlay_EN.png"')
s=s.replace('label+=f\' | partial ({series["time_s"][-1]:.3f} s)\'','label+=f\' | {len(series["time_s"])} steps, {1000*series["time_s"][-1]:g} ms covered\'')
s=s.replace('    mesh_figure()\n','')
f.write_text(s,encoding="utf8")
f=p/"summarize_aft_cycles.py"
s=f.read_text(encoding="utf8").replace("import statistics","import statistics\nimport sys")
s=s.replace('OUT = Path(__file__).resolve().parent','OUT = Path(__file__).resolve().parent\nREPORT = Path(sys.argv[1]) if len(sys.argv)>1 else OUT/"AFT_ONLY_PRESSURE_GATE"')
s=s.replace('OUT/"AFT_ONLY_PRESSURE_GATE"/"RESULT.json"','REPORT/"RESULT.json"').replace('OUT/"AFT_ONLY_PRESSURE_GATE"/"CYCLE_METRICS.json"','REPORT/"CYCLE_METRICS.json"')
s=s.replace('min_flap_pABS_kPa=float(data["pflap_min_Pa"].min()/1000),','min_flap_pABS_kPa=float(data["pflap_min_Pa"].min()/1000), min_flap_vapor_margin_kPa=float(data["flap_vapor_margin_Pa"].min()/1000),')
f.write_text(s,encoding="utf8")

