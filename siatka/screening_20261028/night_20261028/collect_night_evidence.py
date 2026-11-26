from pathlib import Path
import json,re
root=Path(r'F:\ntnu\mesh_screening_20261028\night_20261028')
files={}
for case in ['B001','B002','B003','D001','D002','D003','D004']:
 for name in ['job.json','star.log','launch.json','measurement.json']:
  p=root/case/name
  if p.exists():
   text=p.read_text(encoding='utf-8-sig',errors='replace')
   text=re.sub(r'(?i)(-podkey\s+)(?:"[^"]*"|\S+)',r'\1REDACTED',text)
   files['results/'+case+'/'+name]=text
for name in ['work_log.json','current_activity.json','automatic_work_log.json','work_log_export.json','all_measured_meshes.json','overnight_supervisor.json','resource_mesh_queue_finished.json']:
 p=root/name
 if p.exists():files[name]=p.read_text(encoding='utf-8-sig')
for name in ['overnight_manifest.json','D001_cfd_job.json','D002_cfd_job.json','D003_cfd_job.json','D004_cfd_job.json','original_source_verified.json']:
 p=root/name
 if p.exists():files[name]=p.read_text(encoding='utf-8-sig')
for case in ['probe_A001','probe_D001_np24','D001']:
 for name in ['controller_result.json','completed.json','process.json','runtime_job.json','history.csv','resources.json','setup.json','star.log']:
  p=Path(r'E:\ntnu_cfd_night_20261028')/case/name
  if p.exists():
   text=p.read_text(encoding='utf-8-sig',errors='replace')
   text=re.sub(r'(?i)(-podkey\s+)(?:"[^"]*"|\S+)',r'\1REDACTED',text)
   files['cfd/'+case+'/'+name]=text
for name in ['active_job.json','queue_status.json','queue_finished.json']:
 p=Path(r'E:\ntnu_cfd_night_20261028\overnight_queue')/name
 if p.exists():files['cfd/overnight_queue/'+name]=p.read_text(encoding='utf-8-sig')
(root/'portable_evidence.json').write_text(json.dumps(files),encoding='utf-8')
print('Evidence files',len(files))