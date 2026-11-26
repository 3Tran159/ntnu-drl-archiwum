from pathlib import Path
import json,datetime,hashlib,re,subprocess
h=Path(__file__).resolve().parents[1];r=h.parent
targets=[
(Path('E:/ntnu_mesh_optimization_20261030/clean_c01_campaign_20261101/C01_warm_M13_steady_rho1000_air1p2_20261101/final.sim'),'9af4857b948e0494088b5421f8ede100e66344fc2631cc00030406640d7cc295'),
(r/'flap_drl_20261102/01_reference/C01_original_copy.sim','9af4857b948e0494088b5421f8ede100e66344fc2631cc00030406640d7cc295'),
(r/'checkpoints/Flap_CFD_HOME_RESUME_20261102.sim','3c32632e41c8e14f04dfde542abf7195e03a354c7c8886abf6566d087499ab29'),
(r/'flap_poc_2606_20261102/FlapPOC_2606_working.sim','3c32632e41c8e14f04dfde542abf7195e03a354c7c8886abf6566d087499ab29')]
checks=[]
for p,expected in targets:
 sha=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):sha.update(b)
 checks.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha.hexdigest(),unchanged=sha.hexdigest()==expected))
assert all(x['unchanged'] for x in checks)
ps="Get-CimInstance Win32_Process | Select-Object -ExpandProperty ProcessId | ConvertTo-Json -Compress"
run=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,check=True);pids=set(json.loads(run.stdout))
active_logs=set()
for p in (h/'audit').glob('launch_*.json'):
 try:
  rec=json.loads(p.read_text(encoding='utf8'))
  if rec.get('pid') in pids and 'log' in rec:active_logs.add(Path(rec['log']).resolve())
 except (ValueError,KeyError):pass
dst=h/'runs/redacted';dst.mkdir(exist_ok=True);copies=0
for log in (h/'runs').glob('*.log'):
 if log.resolve() in active_logs:continue
 content=log.read_text(encoding='utf8',errors='replace')
 content=re.sub(r'(?i)(-podkey\s+)(?:"[^"]+"|\S+)',r'\1[REDACTED]',content)
 content=re.sub(r'(?i)(-xencoded-env\s+)\S+',r'\1[REDACTED]',content)
 (dst/log.name).write_text(content,encoding='utf8');copies+=1
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
evidence=dict(at=datetime.datetime.now().astimezone().isoformat(),protected_files=checks,redacted_finished_logs=copies,active_logs_skipped=len(active_logs),original_logs_preserved=True)
(h/f'audit/protected_integrity_{stamp}.json').write_text(json.dumps(evidence,indent=2),encoding='utf8')
print(json.dumps(dict(protected_all_unchanged=True,redacted_finished_logs=copies,active_logs_skipped=len(active_logs),evidence=str(h/f'audit/protected_integrity_{stamp}.json'))))
