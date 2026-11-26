from pathlib import Path
import os,shutil
H=Path(r"F:\ntnu\flap_control\hydro_validation_2606_20261102")
D=H.parent/"independent_cfd_diagnostics"/"C0_speed_down_20261103"
p=H/"tools/night_native.py";text=p.read_text(encoding="utf-8")
marker="env={**os.environ,'NTNU_HYDRO_RUN_ID':stamp,'NTNU_HYDRO_VARIANT':variant,'NTNU_HYDRO_ROOT':str(h),'NTNU_HYDRO_MACRO_DIR':str(snapshot.parent)}"
assert text.count(marker)==1
insert=marker+"\nif name=='C0SpeedDownSmoke.java':\n a=json.loads((h.parent/'independent_cfd_diagnostics/C0_speed_down_20261103/USER_AUTHORIZATION.json').read_text(encoding='utf8'))\n assert a.get('approved_by_user') and a.get('experiment_id')=='C0_SPEED_DOWN_20261103' and a.get('previous_case_remains_failed')\n env['NTNU_C0_SPEEDDOWN_ALLOWED']='YES'"
q=text.replace(marker,insert)
backup=D/"night_native_before_env_patch.py"
assert not backup.exists()
shutil.copy2(p,backup)
tmp=p.with_suffix(".py.manual_tmp");tmp.write_text(q,encoding="utf-8");os.replace(tmp,p)
print("ENV_GUARD_PATCHED: only explicitly authorized C0SpeedDownSmoke macro receives marker, never other jobs")
