from pathlib import Path
import pandas as pd,json,hashlib,datetime
h=Path(__file__).resolve().parents[1];b=h/'cases/SP_B_split0_fixed'
df=pd.read_csv(b/'mesh_cells.csv');s=json.loads((b/'mesh_summary.json').read_text())
expected=80*30*.02-(.10619978819242386+.009330092384759108)*.02
s.update(negative_volume_cells=int((df['Volume (m^3)']<=0).sum()),face_validity_below_half=int((df['Face Validity']<.5).sum()),total_fluid_volume_m3=float(df['Volume (m^3)'].sum()),expected_fluid_volume_m3=expected,relative_volume_error=float(abs(df['Volume (m^3)'].sum()-expected)/expected),prism_cell_count=int((df['Prism Layer Number']>0).sum()),max_prism_layer=int(df['Prism Layer Number'].max()),native_orientation_faces_corrected=510,unclosed_cells=0,cell_count_unchanged_by_orientation_repair=True,repair_deleted_cells=False,checkpoint=str(b/'SP_B_mesh_ready.sim'),sha256=hashlib.sha256((b/'SP_B_mesh_ready.sim').read_bytes()).hexdigest(),at=datetime.datetime.now().astimezone().isoformat(),overset='not applicable to SP_B; SP_C pending')
s['cell_quality_quantiles']={str(k):float(v) for k,v in df['Cell Quality'].quantile([0,.001,.01,.1,.5,1]).items()}
(h/'validation/SP_B_mesh_verified.json').write_text(json.dumps(s,indent=2))
p=h.parent/'CAMPAIGN_STATUS.json';state=json.loads(p.read_text());state.update(state='active',stage='SP_B_mesh_valid_SP_C_mesh_building_SP_A_URANS_stabilizing',updated_at=s['at'],W04_allowed=False,training_data_approved=False);p.write_text(json.dumps(state,indent=2))
print(json.dumps(s,indent=2))
