from pathlib import Path
import json,re,hashlib,datetime
h=Path(__file__).resolve().parents[1];st=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text());a=st.get('active');assert a
run=Path(a['output']);source=Path(a['input']);proof=run/'checkpoint_readback.txt';loaded=proof.read_text()
match=re.search(r'source_iteration=(\d+)',loaded);assert match and all(x in loaded for x in ['Fx_N=','Fz_N=','Mh_Nm=','CL_hydro=','CD='])
cache=st['checkpoint_integrity'][str(source)]
digest=hashlib.file_digest(source.open('rb'),'sha256').hexdigest();assert digest==cache['sha256']
o=dict(at=datetime.datetime.now().astimezone().isoformat(),input=str(source),sha256=digest,bytes=source.stat().st_size,native_reopen_verified=True,saved_time_s=0,saved_native_iteration=int(match[1]),force_readback_pass=True,reset_solution=False,evidence=str(proof),scientific_approved=False)
target=run/'source_checkpoint_integrity.json'
if not target.exists():
 target.write_text(json.dumps(o,indent=2),encoding='utf8')
 with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(kind='native_checkpoint_readback_verified',**o))+'\n')
print(json.dumps(o,indent=2))
p=h/'tools/refresh_current_resume.py';s=p.read_text(encoding='utf8');needle="p=h/'cases/SP_C_split0_overset/c0_first_order_20261103_010758/work_conclusion.json'"
if needle in s:s=s[:s.index(needle)]+"print(json.dumps(dict(at=now,active_job=active['id'],input=str(source)),indent=2))\n";p.write_text(s,encoding='utf8')
