from pathlib import Path
R=Path(__file__).resolve().parent
s=(R/'plot_professor_fields.py').read_text()
s=s.replace("snapshots=json.loads((R/'selected_snapshots.json').read_text())\nmeshes=['M04','M07','M08']","""results=json.loads((R/'configured_mesh_results.json').read_text())['results']
snapshots={v['mesh']:{'status':'settled','time_s':v['window'][1],'velocity':str(Path(v['source_sim']).parent/'velocity_vectors.csv'),'history':str(Path(v['source_sim']).parent/'history.csv')} for v in results}
meshes=list(snapshots)""")
s=s.replace("plt.subplots(3,2,figsize=(15.4,8.5),layout='constrained')","plt.subplots(len(meshes),2,figsize=(15.4,3.55*len(meshes)),layout='constrained',squeeze=False)")
s=s.replace("Accepted saved states | Common colour scales","Second-order calm screen | 1 ms, 10 inner iterations | Accepted instantaneous states")
s=s.replace('professor_fields','configured_fields')
s=s.replace("'field_type':'Instantaneous accepted saved states","'solver_configuration':{'time_order':'SECOND_ORDER','dt_s':.001,'inner':10},'field_type':'Instantaneous accepted saved states")
compile(s,'plot_configured_fields.py','exec');(R/'plot_configured_fields.py').write_text(s)
print('Prepared separate configured-cohort field renderer')
