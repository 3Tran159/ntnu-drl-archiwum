from pathlib import Path
import json,os,datetime
h=Path(__file__).resolve().parents[1];p=h/'NIGHT_QUEUE.json';cfg=json.loads(p.read_text(encoding='utf8'));cfg.pop('controller_exit_requested',None)
tmp=p.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');os.replace(tmp,p)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),kind='controller_reload',reason='Old in-memory allowlist rejected newly added macro before exit request; no STAR job was active. Updated controller validates new explicit macro and resumes durable job state.'))+'\n')
