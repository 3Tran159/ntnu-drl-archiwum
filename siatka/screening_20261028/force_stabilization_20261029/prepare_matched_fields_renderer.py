from pathlib import Path
R=Path(__file__).resolve().parent;p=R/'plot_matched_fields.py'
if p.exists():raise RuntimeError('Prepared renderer exists')
s=(R/'plot_configured_fields.py').read_text().replace('configured_mesh_results.json','matched_endpoint_results.json').replace('configured_fields','matched_fields')
s=s.replace("snapshots={v['mesh']", "results=[v for v in results if v.get('source_unchanged') and v.get('all_saved_fields_finite') and v.get('settling_check_pass')]\nassert {v['mesh'] for v in results}=={'M07','M08','M09'},'Incomplete accepted common-endpoint cohort'\nsnapshots={v['mesh']")
s=s.replace('meshes=list(snapshots)',"meshes=['M09','M08','M07']")
s=s.replace('Second-order calm screen | 1 ms, 10 inner iterations | Accepted instantaneous states','Common-endpoint calm comparison | 1 ms, 10 inner iterations | t = 2.040 s')
s=s.replace("'field_type':'Instantaneous accepted saved states, not time-averaged fields.","'cohort':'matched_endpoint_20261029','field_type':'Instantaneous accepted common-endpoint saved states, not time-averaged fields.")
p.write_text(s);compile(s,str(p),'exec');print('Common-endpoint field renderer prepared; original cohort figures preserved.')
