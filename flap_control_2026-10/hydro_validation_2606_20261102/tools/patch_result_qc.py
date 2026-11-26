from pathlib import Path
import shutil,datetime
h=Path(__file__).resolve().parents[1];p=h/'tools/record_static_result.py';s=p.read_text(encoding='utf8')
shutil.copy2(p,h/'audit'/('record_static_before_QC_'+datetime.datetime.now().strftime('%H%M%S')+'.py'))
s=s.replace("last=df.tail(25);angle=meta.get('static_angle_deg',0)","""assert len(df)==state['steps'] and not df.select_dtypes('number').isna().any().any()
assert (df.time_s.diff().dropna()>0).all() and abs(df.time_s.iloc[-1]-state['saved_time_s'])<1e-8
assert (df.overset_error_cells==0).all() and (df.min_face_validity>.5).all() and (df.min_cell_quality>0).all()
assert (df.tail(75).mass_imbalance_relative<1e-4).all()
windows=[line.split(',') for line in (run/'force_windows.csv').read_text().splitlines() if line.strip()]
assert len(windows)>=3 and int(windows[-1][-1])>=3
last=df.tail(25);angle=meta.get('static_angle_deg',0)
assert (df.flap_angle_deg-angle).abs().max()<.01""")
s=s.replace("if 'overset_error_cells' in df:", """if variant=='SP_C':
 b=json.loads((h/'validation/SP_B_stabilized_result.json').read_text())
 summary.update(CL_vs_B_percent=float((last.CL_hydro.mean()/b['CL_mean']-1)*100),CD_vs_B_percent=float((last.CD.mean()/b['CD_mean']-1)*100))
if 'overset_error_cells' in df:""")
p.write_text(s,encoding='utf8')
p=h/'tools/refresh_resume_instructions.py';s=p.read_text(encoding='utf8').replace("['sha256','saved_time_s','time_s','dt_s','cells','CL_mean','CD_mean']","['checkpoint_sha256','saved_time_s','time_s','saved_dt_s','dt_s','cells','CL_mean','CD_mean']")
p.write_text(s,encoding='utf8');print('postprocessing QC strengthened; no solver changes')
