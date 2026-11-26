from pathlib import Path
import hashlib,json,datetime,shutil,subprocess,re
R=Path('F:/ntnu/flap_control');H=R/'hydro_validation_2606_20261102'
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
audit=H/'audit'/('home_resume_'+stamp);audit.mkdir()
hashes={}
for p,h in [(R/'checkpoints/Flap_CFD_HOME_RESUME_20261102.sim','3c32632e41c8e14f04dfde542abf7195e03a354c7c8886abf6566d087499ab29'),(R/'flap_poc_2606_20261102/FlapPOC_2606_working.sim','3c32632e41c8e14f04dfde542abf7195e03a354c7c8886abf6566d087499ab29'),(R/'flap_drl_20261102/01_reference/C01_original_copy.sim','9af4857b948e0494088b5421f8ede100e66344fc2631cc00030406640d7cc295')]:
 actual=hashlib.file_digest(p.open('rb'),'sha256').hexdigest();assert actual==h,str(p);hashes[str(p)]=actual
ps="Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(star-?ccm\\+|mpiexec|smpd)\\.exe$' } | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress"
p=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
raw=p.stdout.strip();raw=re.sub(r'(?i)(-podkey\s+)[^ \"]+',r'\1[REDACTED]',raw)
entries=json.loads(raw) if raw else []
if isinstance(entries,dict):entries=[entries]
assert not any(str(R).lower() in str(e.get('CommandLine','')).lower() for e in entries),'Owned active process'
(audit/'processes.json').write_text(json.dumps(entries,indent=2))
marker=R/'PAUSED_FOR_HOME.json'
if marker.exists(): marker.rename(audit/'PAUSED_FOR_HOME_archived.json')
cfg=json.loads((H/'config.json').read_text());cfg.update(campaign_state='resumed_model_preparation',resume_requires_explicit_user_instruction=False,W04_allowed=False,last_resume_at=datetime.datetime.now().astimezone().isoformat())
(H/'config.json').write_text(json.dumps(cfg,indent=2))
state=dict(at=cfg['last_resume_at'],authorized_by='User: resume per HOME_RESUME_INSTRUCTIONS; continue hydrodynamic flap; no W04',verified_sha256=hashes,other_star_processes=len(entries),W04_started_by_this_task=False,cpu_processes=4,gpu_compute=False,checkpoint_reinitialized=False)
(audit/'resume.json').write_text(json.dumps(state,indent=2))
(R/'CAMPAIGN_STATUS.json').write_text(json.dumps(state,indent=2))
case=H/'cases/SP_A_original_singlephase';case.mkdir(exist_ok=True)
seed=case/'C01_seed.sim'
if not seed.exists():shutil.copy2(R/'flap_drl_20261102/01_reference/C01_original_copy.sim',seed)
assert hashlib.file_digest(seed.open('rb'),'sha256').hexdigest()==hashes[str(R/'flap_drl_20261102/01_reference/C01_original_copy.sim')]
print(json.dumps(dict(status='resumed_model_preparation',audit=str(audit),seed=str(seed),checkpoint_unchanged=True,W04_allowed=False)))
