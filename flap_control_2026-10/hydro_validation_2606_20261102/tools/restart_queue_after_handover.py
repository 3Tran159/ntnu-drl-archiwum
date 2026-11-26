from pathlib import Path
import json,time,os,sys,subprocess,datetime
h=Path(__file__).resolve().parents[1];lock=h/'audit/night_queue.lock'
for i in range(45):
 if not lock.exists():break
 time.sleep(1)
assert not lock.exists(),'Existing controller did not hand over; do not duplicate it'
cfg=json.loads((h/'NIGHT_QUEUE.json').read_text(encoding='utf8'));cfg.pop('controller_exit_requested',None)
tmp=h/'NIGHT_QUEUE.json.tmp';tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');os.replace(tmp,h/'NIGHT_QUEUE.json')
with (h/'runs/night_queue_20261102_v4.stdout.log').open('w',encoding='utf8') as out,(h/'runs/night_queue_20261102_v4.stderr.log').open('w',encoding='utf8') as err:
 p=subprocess.Popen([sys.executable,'-u',str(h/'tools/night_queue.py')],stdout=out,stderr=err,cwd=h,creationflags=subprocess.CREATE_NO_WINDOW)
receipt=dict(pid=p.pid,at=datetime.datetime.now().astimezone().isoformat(),purpose='Refresh live status/dashboard; adopt currently running STAR without interruption')
(h/'audit/night_queue_controller_latest.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(kind='controller_handover',**receipt))+'\n')
print(json.dumps(receipt,indent=2))
