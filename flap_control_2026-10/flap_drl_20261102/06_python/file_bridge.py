"""Atomic, numbered file protocol. No solver launch, no network service."""
from pathlib import Path
import os,json,math
def atomic_json(path,obj):
 path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp')
 with tmp.open('w',encoding='utf8') as f:
  json.dump(obj,f,allow_nan=False);f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
def command(folder,run_id,seq,time_s,target_rad):
 if seq<0 or not all(map(math.isfinite,[time_s,target_rad])):raise ValueError('Invalid command')
 if abs(target_rad)>math.radians(5):raise ValueError('Beyond provisional angle envelope')
 p=Path(folder)/f'command_{seq:08d}.json'
 if p.exists():raise FileExistsError(p)
 atomic_json(p,dict(schema_version='1.0',run_id=run_id,seq=seq,time_s=time_s,target_rad=target_rad))
 return p
def observation(path,run_id,seq):
 d=json.loads(Path(path).read_text())
 if d['run_id']!=run_id or d['seq']!=seq:raise ValueError('Stale or foreign observation')
 for name in ['time_s','delta_actual_rad','omega_actual_rad_s','Fx_total_N','Fz_total_N','Mh_flap_Nm']:
  if not math.isfinite(d[name]):raise ValueError('Non-finite observation: '+name)
 return d
