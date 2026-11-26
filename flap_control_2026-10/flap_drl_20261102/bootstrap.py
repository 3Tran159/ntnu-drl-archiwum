from pathlib import Path
import json, hashlib, shutil, subprocess, datetime, re, html, sqlite3, importlib.util, sys
ROOT=Path(__file__).resolve().parent
INSTALL=Path('E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8')
CAMPAIGN=Path('E:/ntnu_mesh_optimization_20261030')
SOURCE=CAMPAIGN/'clean_c01_campaign_20261101/C01_warm_M13_steady_rho1000_air1p2_20261101/final.sim'
EXPECTED='9af4857b948e0494088b5421f8ede100e66344fc2631cc00030406640d7cc295'
def write(name,obj):
 p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf8')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(4*1024**2),b''):h.update(chunk)
 return h.hexdigest()
for name in ['00_audit','01_reference','02_geometry','03_mesh','04_cases/calm','04_cases/waves','05_macros','06_python','07_runs','08_dataset/raw','08_dataset/processed','08_dataset/splits','09_validation','10_reports']:
 (ROOT/name).mkdir(parents=True,exist_ok=True)
before=SOURCE.stat()
assert before.st_size==506414871
source_hash=sha(SOURCE)
assert source_hash==EXPECTED,'Accepted source hash mismatch'
dest=ROOT/'01_reference/C01_original_copy.sim'
if not dest.exists():shutil.copy2(SOURCE,dest)
assert sha(dest)==EXPECTED
work=ROOT/'04_cases/calm/FLAP_C00_seed.sim'
if not work.exists():shutil.copy2(dest,work)
assert sha(work)==EXPECTED
after=SOURCE.stat()
assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
for name in ['setup.json','completed.json','calm_audit.json','density_configuration_audit.json','baseline_inventory_audit.json']:
 src=SOURCE.parent/name
 if src.exists() and not (ROOT/'01_reference'/name).exists():shutil.copy2(src,ROOT/'01_reference'/name)
manifest=dict(timestamp=datetime.datetime.now().astimezone().isoformat(),device='THINKPAD-LUCJAN',source=str(SOURCE),source_sha256=source_hash,source_size=before.st_size,source_mtime_unchanged=True,reference_copy=str(dest),working_seed=str(work),copies_verified=True,seed_has_flap=False,solver_steps_executed=0,originals_modified=False,active_campaign_modified=False,excluded_case='legacy W07 lambda=92.5 m',expected_C01_time_s=4.699199999999548)
write('00_audit/copy_manifest.json',manifest)
# Read queue using SQLite read-only mode. No application code is imported.
db=CAMPAIGN/'nwar_automation_20261102/queue.sqlite'
queue={'path':str(db)}
if db.exists():
 try:
  con=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True,timeout=2)
  names=[r[0] for r in con.execute("select name from sqlite_master where type='table'")]
  queue['tables']=names; queue['rows']={}
  for name in names:
   if re.fullmatch(r'[A-Za-z0-9_]+',name):
    cur=con.execute('select * from "'+name+'" limit 30')
    cols=[c[0] for c in cur.description]
    queue['rows'][name]=[dict(zip(cols,r)) for r in cur.fetchall()]
  con.close()
 except Exception as e:queue['error']=str(e)
write('00_audit/queue_snapshot.json',queue)
# Record installed HTML release notes, retaining only relevant surrounding paragraphs.
doc=INSTALL/'doc/en/ReleaseNotes_21.02.007_01.html'
s=doc.read_text(encoding='utf8',errors='replace')
s=html.unescape(re.sub('<[^>]+>',' ',s));s=re.sub(r'\s+',' ',s)
hits=[]
for match in re.finditer(r'(?i)GPU|overset|morphing',s):
 a=max(0,match.start()-180);b=min(len(s),match.end()+450)
 hits.append(s[a:b])
(ROOT/'00_audit/release_notes_motion_gpu.txt').write_text('\n\n'.join(hits),encoding='utf8')
write('00_audit/python_inventory.json',{'python':sys.executable,'version':sys.version,'packages':{n:bool(importlib.util.find_spec(n)) for n in ['numpy','pandas','scipy','matplotlib','torch','gymnasium','stable_baselines3']}})
# Inspect the installed Java API without opening or running any simulation.
cp=str(INSTALL/'star/lib/java/platform/modules/ext/*')
javap='C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javap.exe'
classes=['star.common.Simulation','star.common.Boundary','star.common.PhysicsContinuum','star.base.report.ForceReport','star.base.report.MomentReport','star.common.PartManager','star.common.SimulationPartManager','star.common.MeshManager']
for cls in classes:
 p=subprocess.run([javap,'-classpath',cp,cls],capture_output=True,text=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
 (ROOT/'00_audit'/('api_'+cls.rsplit('.',1)[-1]+'.txt')).write_text(p.stdout+p.stderr,encoding='utf8')
print(json.dumps(manifest,indent=2))
print('QUEUE_TABLES',queue.get('tables'))
print('GPU_DOC_EXCERPTS',json.dumps(hits[:12],ensure_ascii=False))
print('PYTHON', (ROOT/'00_audit/python_inventory.json').read_text())
