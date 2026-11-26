from pathlib import Path
import shutil,datetime
R=Path('F:/ntnu/flap_control/hydro_validation_2606_20261102')
p=R/'tools/native_launch.py';t=p.read_text()
t=t.replace("import subprocess,json,re,sys,datetime,os,shutil","import subprocess,json,re,sys,datetime,os,shutil,hashlib")
t=t.replace("args.extend(['-batch',str(macro)]);args.extend([] if new else [str(sim)])","")
t=t.replace("env={**os.environ", "snapshot=R/'runs'/'macro_snapshots'/stamp/macro.name;snapshot.parent.mkdir(parents=True,exist_ok=False);shutil.copy2(macro,snapshot)\nargs.extend(['-batch',str(snapshot)]);args.extend([] if new else [str(sim)])\nenv={**os.environ")
t=t.replace("receipt=dict(pid=p.pid,macro=str(macro),","receipt=dict(pid=p.pid,macro=str(macro),executed_macro=str(snapshot),macro_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),")
p.write_text(t)
print('Future launches preserve exact macro source snapshot.')
