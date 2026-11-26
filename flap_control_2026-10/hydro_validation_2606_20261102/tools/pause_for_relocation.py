from pathlib import Path
import json,datetime,os,shutil
h=Path(__file__).resolve().parents[1];root=h.parent;at=datetime.datetime.now().astimezone().isoformat();stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
archive=root/'checkpoints'/('RELOCATION_'+stamp);archive.mkdir(parents=True,exist_ok=False)
pause=dict(at=at,source='explicit_user_relocation_pause',reason='ThinkPad relocation within15minutes. Do not start new experiments or automatically resume.',requires_explicit_user_resume=True,archive=str(archive),campaign=str(h))
for name in ['NIGHT_QUEUE.json','NIGHT_QUEUE_STATE.json','WORK_CURRENT_REVIEW.json']:shutil.copy2(h/name,archive/('before_pause_'+name))
for name in ['STOP_OWNED_CFD.json','PAUSED_FOR_HOME.json']:
 p=root/name
 if p.exists():shutil.copy2(p,archive/('previous_'+name))
 tmp=p.with_suffix('.relocation_tmp');tmp.write_text(json.dumps(pause,indent=2),encoding='utf8');os.replace(tmp,p)
p=h/'NIGHT_QUEUE.json';cfg=json.loads(p.read_text(encoding='utf8'));cfg['controller_exit_requested']=True;cfg['relocation_pause']=pause;cfg['accept_new_jobs']=False
tmp=p.with_suffix('.relocation_tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');os.replace(tmp,p)
(h/'audit/RELOCATION_CURRENT.json').write_text(json.dumps(pause,indent=2),encoding='utf8')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(kind='user_relocation_pause_requested',**pause))+'\n')
print(json.dumps(pause,indent=2))
