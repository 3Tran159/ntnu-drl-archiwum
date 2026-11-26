from pathlib import Path
import json,datetime,hashlib
h=Path(__file__).resolve().parents[1];run=h/'cases/SP_C_split0_overset/c0_first_order_20261103_010758'
p=run/'checkpoint_readback.txt';text=p.read_text(encoding='utf8');assert 'source_iteration=430' in text and all(x in text for x in ['Fx_N=','Fz_N=','Mh_Nm=','CL_hydro=','CD='])
source=h/'cases/SP_C_split0_overset/c0_relaxed_init_20261103_005648/steady_checkpoint.sim'
digest=hashlib.file_digest(source.open('rb'),'sha256').hexdigest();assert digest=='945353bf97a01ea6b57148c99c073db548cdbf24c9aa33ccd5130ecaf684c09a'
o=dict(at=datetime.datetime.now().astimezone().isoformat(),input=str(source),bytes=source.stat().st_size,sha256=digest,native_reopen_verified=True,saved_time_s=0,saved_iteration=430,force_readback_pass=True,evidence=str(p),reset_solution=False,scientific_approved=False,scope='Recoverability verified, hydrodynamic validity not approved')
(run/'source_checkpoint_integrity.json').write_text(json.dumps(o,indent=2),encoding='utf8')
(h/'audit/relaxed_checkpoint_native_readback_20261103_0110.json').write_text(json.dumps(o,indent=2),encoding='utf8')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(kind='native_checkpoint_readback_verified',**o))+'\n')
print(json.dumps(o,indent=2))
