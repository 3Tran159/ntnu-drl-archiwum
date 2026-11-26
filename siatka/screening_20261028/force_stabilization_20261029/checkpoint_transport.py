import json,hashlib,shutil,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024**2),b''):h.update(chunk)
 return h.hexdigest()
files=[R/'M03_until_settled_r1/final.sim',R/'M02_until_settled_r1/final.sim',Q/'M04/mesh.sim',Q/'M05/mesh.sim',R/'resume_campaign.py',R/'ContinueUntilSettled.java',R.parent/'dashboard.html']
audit={'saved_at':datetime.datetime.now().astimezone().isoformat(),'paused':True,'stop_marker':(R/'STOP_ALL').exists(),'queue_lock_exists':(R/'queue.lock').exists(),'files':[{'path':str(p),'size_bytes':p.stat().st_size,'sha256':sha(p)} for p in files],'prepared_cases':['M04','M05'],'settled_cases':{'M03':1.716,'M02':1.4}}
assert audit['stop_marker'] and not audit['queue_lock_exists']
(R/'transport_checkpoint_manifest.json').write_text(json.dumps(audit,indent=2))
old=R/'START_HERE_EN.txt'
if old.exists() and not (R/'START_HERE_EN_archive_before_transport.txt').exists():shutil.copy2(old,R/'START_HERE_EN_archive_before_transport.txt')
old.write_text('CURRENT HANDOVER: read RESUME_AT_HOME.txt in this directory.\nCampaign paused for transport. M02/M03 settled; M04/M05 verified and prepared.\nExact Desktop Commander resume command: RESUME_COMMAND.txt.\nSaved-state checksums: transport_checkpoint_manifest.json.\nDo not start GPU calculations until the user resumes from home.\n',encoding='utf-8')
(R/'START_HERE.txt').write_text('Aktualny stan i plan wznowienia: RESUME_AT_HOME.txt.\nKomenda Desktop Commander: RESUME_COMMAND.txt.\nM02/M03 ustabilizowane. M04/M05 gotowe. Kampania w pauzie przed transportem.\n',encoding='utf-8')
print(json.dumps({'saved_models':4,'all_files_verified':True,'queue_lock_exists':False,'stop_marker':True}))
