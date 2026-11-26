from pathlib import Path
import json,hashlib,shutil,datetime,time,os,re
h=Path(__file__).resolve().parents[1];root=h.parent;read=lambda p:json.loads(p.read_text(encoding='utf8'));pause=read(h/'audit/RELOCATION_CURRENT.json');arc=Path(pause['archive']).resolve()
assert arc.is_relative_to((root/'checkpoints').resolve()) and arc.is_dir()
state=read(h/'NIGHT_QUEUE_STATE.json');assert not state.get('active'),'Owned job still active'
assert (root/'PAUSED_FOR_HOME.json').exists() and (root/'STOP_OWNED_CFD.json').exists()
selected=[('C0_OV_HOME_RESUME_20261103_073441.sim',h/'cases/SP_C_split0_overset/c0_top_direction_20261103_050724/checkpoint.sim',.65,11560),
('B0_FIXED_HOME_RESUME_20261103_073441.sim',h/'cases/SP_B_split0_fixed/b0_top_direction_20261103_053542/checkpoint.sim',.5,6250)]
manifest=[];ck=[]
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def preserve(src,dst,redact=False):
 before=src.stat();dst.parent.mkdir(parents=True,exist_ok=True);assert not dst.exists(),str(dst)
 if redact:
  data=src.read_text(encoding='utf8',errors='replace');data=re.sub(r'(?i)(-podkey\s+)\S+',r'\1[REDACTED]',data);dst.write_text(data,encoding='utf8')
 else:shutil.copy2(src,dst)
 after=src.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),('Source changed during archive',str(src))
 a=digest(src);b=digest(dst)
 if not redact:assert a==b,('Copy hash differs',str(src))
 rec=dict(source=str(src),archive=str(dst.relative_to(arc)),bytes=dst.stat().st_size,sha256=b,source_sha256=a,source_mtime_ns=after.st_mtime_ns,redacted_license=redact);manifest.append(rec);return rec
for name,source,t,it in selected:
 cp=state['checkpoint_integrity'][str(source)];assert cp['native_save_complete'] and digest(source)==cp['sha256']
 rec=preserve(source,arc/name);rec.update(physical_time_s=t,native_iteration=it,native_save_complete=True,native_reopen_verified=False,scientific_approved=False);ck.append(rec)
(arc/'CHECKPOINTS.json').write_text(json.dumps(ck,indent=2),encoding='utf8')
files=[p for p in h.rglob('*') if p.is_file() and p.suffix.lower() not in ['.sim','.tmp','.work_tmp','.relocation_tmp'] and not p.is_relative_to(h/'tools/deps') and '__pycache__' not in p.parts and p.name!='night_queue.lock']
required=sum(p.stat().st_size for p in files);assert shutil.disk_usage(arc).free>required+5*1024**3
for n,src in enumerate(files,1):
 rel=src.relative_to(h);preserve(src,arc/'campaign'/rel,src.suffix.lower()=='.log')
 if n%50==0:
  (arc/'ARCHIVE_PROGRESS.json').write_text(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),files_done=n,files_total=len(files),bytes_done=sum(r['bytes'] for r in manifest),status='copying_and_hashing')),encoding='utf8')
for name in ['PAUSED_FOR_HOME.json','STOP_OWNED_CFD.json','HOME_RESUME_INSTRUCTIONS.md']:
 p=root/name
 if p.exists():preserve(p,arc/'root_snapshot'/name)
record=dict(at=datetime.datetime.now().astimezone().isoformat(),status='archive_copy_verified',checkpoint_count=len(ck),files=len(manifest),bytes=sum(r['bytes'] for r in manifest),simh_files=[r['archive'] for r in manifest if r['archive'].lower().endswith('.simh')],excluded='Older .sim checkpoints remain untouched in original campaign. Python package cache tools/deps remains installed; scripts, geometry, all campaign CSVs, logs and reports copied. Solver logs have license key redacted; original approved license source remains in place.',checkpoints=ck,files_manifest=manifest)
(arc/'ARCHIVE_MANIFEST.json').write_text(json.dumps(record,indent=2),encoding='utf8')
(arc/'ARCHIVE_PROGRESS.json').write_text(json.dumps({k:v for k,v in record.items() if k!='files_manifest'},indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in record.items() if k not in ['files_manifest','checkpoints']},indent=2))
