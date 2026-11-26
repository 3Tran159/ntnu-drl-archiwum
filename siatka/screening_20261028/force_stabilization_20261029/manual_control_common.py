"""Validated local run presets and request policy. No solver side effects on import."""
import json,math,os,re,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
W=Path('E:/ntnu/quasi2d_waves_20261029')
PORT=8771
CATALOG=[
 dict(id='W01_M10',label='W01 · H 0.50 m / wavelength 20 m · M10',height=.5,wavelength=20,cells=317277,source='W01_W20L4_M10_FS020_env_setup_r1',review='Exploratory; finer free-surface candidate. Force convergence remains unverified.',enabled=True),
 dict(id='C01_M10',label='C01 · Calm / 80 m domain · M10',height=0,wavelength=20,cells=317277,source='C01_W20L4_M10_FS020_env_setup_r1',review='Matched calm reference for M10 wave runs; new force settling required.',enabled=True),
 dict(id='W01_M09',label='W01 · H 0.50 m / wavelength 20 m · M09',height=.5,wavelength=20,cells=246885,source='W01_W20L4_M09_env_setup_r2',review='Exploratory coarse free-surface comparison; not the short-domain calm mesh.',enabled=True),
 dict(id='C01_M09',label='C01 · Calm / 80 m domain · M09',height=0,wavelength=20,cells=246885,source='C01_W20L4_M09_env_setup_r2',review='Matched calm reference for the M09 long domain.',enabled=True),
 dict(id='W03_M10',label='W03 · H 0.25 m / wavelength 20 m · M10',height=.25,wavelength=20,cells=317277,source='W01_W20L4_M10_FS020_env_setup_r1',review='Additional exploratory case. Lower wave height needs free-surface refinement and a matched H 0.50 m baseline before final comparison.',enabled=True),
 dict(id='W04_M10',label='W04 · H 0.75 m / wavelength 20 m · M10',height=.75,wavelength=20,cells=317277,source='W01_W20L4_M10_FS020_env_setup_r1',review='Additional exploratory case; wave height changes only in a fresh initialized copy.',enabled=True),
 dict(id='W02',label='W02 · H 0.50 m / wavelength 30 m',enabled=False,review='Not ready: needs a matched 120 m domain and calm input.'),
 dict(id='W05',label='W05 · H 0.25 m / wavelength 30 m',enabled=False,review='Not ready: 120 m domain and lower-height resolution check required.'),
 dict(id='W06',label='W06 · H 0.75 m / wavelength 30 m',enabled=False,review='Not ready: 120 m domain and matched calm input required.'),
 dict(id='W07',label='W07 · H 0.50 m / wavelength 10 m',enabled=False,review='Not ready: matched domain and wave-specific resolution check required.'),
 dict(id='W08',label='W08 · H 0.50 m / wavelength 40 m',enabled=False,review='Not ready: matched 160 m domain and calm input required.')]
def read(p,default=None):
 try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return {} if default is None else default
def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
 return h.hexdigest()
WAVE_STARTUP_MESSAGE='Wave startup update in progress; W01a validation pending.'
def wave_startup_policy():
 # Read on every request: import caching must not freeze the launch decision.
 path=R/'wave_startup_policy_current.json';present=path.exists();policy=read(path) if present else {}
 if not isinstance(policy,dict):policy={}
 return dict(present=present,status=policy.get('status','unreadable_or_unknown_policy') if present else 'legacy_policy_absent',legacy_wave_starts_blocked=present,message=WAVE_STARTUP_MESSAGE if present else '')
def is_wave(p):return p.get('height',0)>0 or str(p.get('id','')).startswith('W')
def require_startup_binding(p):
 policy=wave_startup_policy()
 if policy['present'] and is_wave(p):
  # All existing presets dispatch ManualFoilWave.java, which initializes a full-domain wave.
  # A policy status/boolean alone cannot bind a different, audited inlet-launch recipe.
  raise ValueError(WAVE_STARTUP_MESSAGE+' This legacy wave preset has no validated inlet-startup recipe binding.')
def catalog():
 policy=wave_startup_policy();rows=[]
 for base in CATALOG:
  p=dict(base)
  if policy['present'] and is_wave(p):p.update(enabled=False,review=WAVE_STARTUP_MESSAGE,disabled_reason='legacy_wave_recipe_unbound',startup_mode='legacy_full_domain_wave')
  rows.append(p)
 return rows
def preset(key):
 p=next((dict(x) for x in CATALOG if x['id']==key),None)
 if not p:raise ValueError('This case is not prepared for local launch.')
 require_startup_binding(p)
 if not p['enabled']:raise ValueError('This case is not prepared for local launch.')
 return p
def number(v,lo,hi,name):
 if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not lo<=v<=hi:raise ValueError(f'{name} must be between {lo} and {hi}.')
 return float(v)
def validate_request(d):
 if not isinstance(d,dict) or set(d)-{'preset','target_s','wall_minutes'}:raise ValueError('Unexpected request fields.')
 p=preset(d.get('preset'))
 t=number(d.get('target_s'),.05,12,'End time [s]')
 if abs(t*1000-round(t*1000))>1e-7:raise ValueError('End time must use whole milliseconds.')
 wall=number(d.get('wall_minutes'),10,720,'Wall limit [min]')
 return dict(preset=p['id'],target_s=t,wall_minutes=wall)
def validate_source(p):
 require_startup_binding(p)
 source=W/p['source']/'prepared.sim'
 manifest=read(R/'manual_control_source_manifest.json').get(p['source'],{})
 if not source.is_file() or not manifest or digest(source)!=manifest.get('sha256'):raise ValueError('Prepared source identity changed or is unavailable; launch refused.')
 if manifest.get('cells')!=p['cells'] or not manifest.get('audit_pass'):raise ValueError('Prepared source audit not passed.')
 return source,manifest['sha256']
def safe_case(path):
 p=Path(path).resolve()
 if p.parent!=W.resolve() or not p.name.startswith(('W01_W20L4_','W01a_W20L4_','C01_W20L4_M10_calm_settle_r2','LOCAL_','MANUAL_')):raise ValueError('Case is outside the controlled campaign.')
 return p
