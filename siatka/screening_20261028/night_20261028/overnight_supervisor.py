"""Start the four-case night queue only after the real 24-worker probe passes."""
from pathlib import Path
import json,time,sys,subprocess,hashlib
from datetime import datetime,timezone
root=Path(r'F:\ntnu\mesh_screening_20261028\night_20261028')
dest=Path(r'E:\ntnu_cfd_night_20261028')
result_path=dest/'probe_D001_np24/controller_result.json'
state=root/'overnight_supervisor.json'
def status(value,**kw):
 data=dict(status=value,updated_at=datetime.now(timezone.utc).isoformat(),**kw)
 temp=state.with_suffix('.new');temp.write_text(json.dumps(data,indent=2));temp.replace(state)
def note(id,work,finding,challenge,next_step):
 p=root/'work_log.json';entries=json.loads(p.read_text(encoding='utf-8-sig'))
 if id not in {x['id'] for x in entries}:
  entries.append(dict(id=id,time=datetime.now(timezone.utc).isoformat(),kind='queue',work=work,finding=finding,challenge=challenge,next_step=next_step))
  temp=p.with_suffix('.new');temp.write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(p)
status('waiting_for_probe')
deadline=time.time()+3600
while not result_path.exists() and time.time()<deadline:
 if (dest/'STOP_ALL').exists():status('stopped_by_marker');sys.exit(0)
 time.sleep(10)
r=json.loads(result_path.read_text()) if result_path.exists() else {}
m=r.get('measurement',{})
if r.get('status')!='completed' or m.get('physical_time_s',0)<1.99e-5 or r.get('min_free_gib',0)<12:
 status('blocked_probe_not_qualified',probe=r)
 note('overnight-blocked','Kolejka nocna nie wystartowała','Próba nie spełniła bramki: ukończenie, co najmniej dwa kroki czasowe i 12 GiB rezerwy RAM.',str(r.get('status','timeout')),'Sprawdzić log próby przed kolejnym startem.')
 sys.exit(2)
jobs=[]
for case in ['D001','D002','D003','D004']:
 source=root/case/'mesh.sim'
 h=hashlib.sha256()
 with source.open('rb') as stream:
  for block in iter(lambda:stream.read(8*1024*1024),b''):h.update(block)
 job=dict(source=str(source),source_sha256=h.hexdigest(),output=str(dest/case),macro=str(root/'NightCFD.java'),processes=24,wall_seconds=7200,max_steps=10000000)
 p=root/(case+'_cfd_job.json');p.write_text(json.dumps(job,indent=2));jobs.append(str(p))
manifest=dict(jobs=jobs,status_dir=str(dest/'overnight_queue'),required_free_gib=40,wait_for_memory_s=900,soft_reserve_gib=10,hard_reserve_gib=6,timeout_grace_s=1800)
p=root/'overnight_manifest.json';p.write_text(json.dumps(manifest,indent=2))
status('running_sequential_queue',manifest=str(p))
note('overnight-started','Start nocnej kolejki D001 → D002 → D003 → D004','Po 2 h czasu solvera na przypadek, 24 procesy CPU, 18 m/s, Double, dt=1e-5 s. Checkpoint co około 15 min między krokami.','Początkowa stabilność i koszt obliczeń; pełne pokrycie pryzmów nadal około 98,76%, dokładność CFD niepotwierdzona.','Automatycznie przechodzić do następnego przypadku; przerwać kolejkę przy braku RAM lub przekroczeniu limitu wykonania.')
(root/'current_activity.json').write_text(json.dumps(dict(updated_at=datetime.now(timezone.utc).isoformat(),text='Nocna kolejka D001–D004 uruchomiona sekwencyjnie. Bieżący przypadek i postęp widoczne w tabeli CFD. 2 h solvera na przypadek; 24 procesy, 18 m/s, Double.'),ensure_ascii=False),encoding='utf-8')
rc=subprocess.call([sys.executable,str(root/'night_queue.py'),str(p)])
status('queue_process_exited',returncode=rc)
note('overnight-ended','Proces kolejki nocnej zakończony','Kod zakończenia procesu: '+str(rc)+'. Szczegółowe statusy w tabeli CFD oraz queue_finished.json.','Zakończenie procesu nie oznacza zaliczenia wszystkich przypadków.','Porównać historię, RAM i checkpointy przy wspólnym czasie fizycznym.')
(root/'current_activity.json').write_text(json.dumps(dict(updated_at=datetime.now(timezone.utc).isoformat(),text='Proces kolejki nocnej zakończony. Sprawdź indywidualne statusy prób i czas fizyczny w tabeli CFD; zakończenie nie oznacza zbieżności.'),ensure_ascii=False),encoding='utf-8')

