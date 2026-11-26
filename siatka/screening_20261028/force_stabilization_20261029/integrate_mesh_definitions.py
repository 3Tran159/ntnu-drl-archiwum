from pathlib import Path
import shutil
R=Path(r'F:\ntnu\mesh_screening_20261028\force_stabilization_20261029')
p=R/'mesh_parameter_table.py';backup=R/'mesh_parameter_table_before_definition_rows.py'
if not backup.exists():shutil.copy2(p,backup)
s=p.read_text(encoding='utf-8')
s=s.replace("def matrix(live):","def matrix(live):\n from mesh_definition import definitions,FIELDS,delta_panel\n defs=definitions()")
anchor=" labels=['Status'"
pos=s.index(anchor)
end=s.index("\n css=",pos)
s=s[:end]+"\n extra_labels=[label for key,label in FIELDS]+['Surface growth ratio','Near-foil box · x / z [m]','Free-surface box · x / z [m]','Span thickness / cells']\n labels[3:3]=extra_labels\n for col in columns:\n  spec=defs.get(col['mesh'],{})\n  col['values'][3:3]=[f(spec.get(key)*1000 if spec.get(key) is not None else None) for key,label in FIELDS]+[f(spec.get('surface_growth'),2),spec.get('near_foil_box','Pending'),spec.get('surface_box','Pending'),'20 mm / 1']"+s[end:]
s=s.replace("i in [3,7,10,17]","label in ['Outer base size [mm]','First full layer [µm]','Wall y+ · area p95','Flow time step [ms]','Median computing time / step [s]']")
s=s.replace("All current campaign meshes; new admitted variants appear automatically. Prism settings are nominal.","All current campaign meshes; new admitted variants appear automatically. Size controls are read from the actual build macros. Source hashes are recorded in the evidence snapshot. Prism settings are nominal.")
s=s.replace(" return s\ndef optimization():"," return s+delta_panel(defs)\ndef optimization():")
p.write_text(s,encoding='utf-8')
p=R/'build_dashboard_en.py';s=p.read_text(encoding='utf-8');anchor="'mesh_optimization_evidence':read(R/'mesh_optimization_evidence.json',{}),"
assert anchor in s
s=s.replace(anchor,anchor+"'mesh_definition_evidence':read(R/'mesh_definition_evidence.json',{}),")
p.write_text(s,encoding='utf-8')
print('Added actual nominal size controls and explicit M07 to M08 changes.')
