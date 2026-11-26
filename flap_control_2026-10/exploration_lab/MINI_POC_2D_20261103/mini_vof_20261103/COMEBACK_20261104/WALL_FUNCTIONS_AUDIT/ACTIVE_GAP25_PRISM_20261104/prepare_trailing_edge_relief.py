from pathlib import Path
root=Path(__file__).resolve().parent
out=root/"TRAILING_EDGE_LAYER_RELIEF"
out.mkdir(exist_ok=False)
s=(root/"build_gap_mesh.py").read_text(encoding="utf8")
s=s.replace('OUT.parents[4]','OUT.parents[5]').replace('OUT.parents[5] / "hydro_validation','OUT.parents[6] / "hydro_validation')
s=s.replace("        trailing_tip = None","        prism_curves = []")
s=s.replace("            if name == 'flap':\n                trailing_tip = ids[np.argmax(poly[:,0])]\n","")
s=s.replace("                if np.linalg.norm((a + b)/2 - hinge) < .044:",
'''                if name != "flap" or max(a[0],b[0])<1.188:
                    prism_curves.append(line)
                if np.linalg.norm((a + b)/2 - hinge) < .044:''')
s=s.replace('f.setNumbers(bl, "CurvesList", wall_curves)','f.setNumbers(bl, "CurvesList", prism_curves)')
s=s.replace('        f.setNumbers(bl, "FanPointsList", [trailing_tip])\n        f.setNumbers(bl, "FanPointsSizesList", [5])\n','')
s=s.replace('source=str(SOURCE), source_sha256=','trailing_edge_layer_cutoff_m=1.188, source=str(SOURCE), source_sha256=')
(out/"build_gap_mesh.py").write_text(s,encoding="utf8")

