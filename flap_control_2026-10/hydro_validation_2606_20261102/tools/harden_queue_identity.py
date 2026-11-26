from pathlib import Path
import json,os,py_compile,shutil,datetime
h=Path(__file__).resolve().parents[1];p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8')
shutil.copy2(p,h/'audit'/('queue_before_identity_hardening_'+datetime.datetime.now().strftime('%H%M%S')+'.py'))
s=s.replace('born=[string]$_.CreationDate;', 'born=[string]$_.CreationDate.Ticks;')
s=s.replace("if p['ppid'] in roots and p['pid'] not in roots:roots.add(p['pid']);changed=True", "if p['ppid'] in roots and p['ppid'] in alive and p['pid'] not in roots and int(p['born'] or 0)>=int(alive[p['ppid']]['born'] or 0)>0:roots.add(p['pid']);changed=True")
s=s.replace("hp=out/'history.csv'","rows=[];hp=out/'history.csv'")
s=s.replace("if ckpts:metrics['last_output_sim']=str(ckpts[-1])","""complete_ckpts=[cp for cp in ckpts if time.time()-cp.stat().st_mtime>2]
 if complete_ckpts and log.exists():
  candidate=complete_ckpts[-1];cache=st.setdefault('checkpoint_integrity',{})
  if str(candidate) not in cache:
   native_log=log.read_text(encoding='utf8',errors='replace')
   save_done=any('Saving:' in line and str(candidate) in line and 'complete (' in line for line in native_log.splitlines())
   if save_done:
    before=candidate.stat()
    with candidate.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    after=candidate.stat()
    if before.st_size==after.st_size and before.st_mtime_ns==after.st_mtime_ns:
     saved_time=rec.get('initial_time_s')
     match=re.match(r'checkpoint_step_(\\d+)\\.sim',candidate.name)
     if match:
      selected=[r for r in rows if int(r['step'])==int(match.group(1))]
      if selected:saved_time=float(selected[-1]['time_s'])
     elif candidate.name in ['checkpoint.sim','error_checkpoint.sim'] and rows:saved_time=float(rows[-1]['time_s'])
     cache[str(candidate)]=dict(path=str(candidate),bytes=after.st_size,sha256=digest,saved_time_s=saved_time,native_save_complete=True,hash_at=now(),native_reopen_verified=False)
  if str(candidate) in cache:
   metrics['last_output_sim']=str(candidate);metrics['checkpoint_integrity']=cache[str(candidate)]""")
s=s.replace("base=read(H/'validation/C0_actual_resume_20261102_221053.json',{})","""base=read(H/'validation/C0_actual_resume_20261102_221053.json',{})
 base['historical_resume_checkpoint']={k:base.pop(k,None) for k in ['bytes','sha256','timestep','iteration','start_time_s']}""")
s=s.replace("base['current_obstacle']='C0 force bias", """for key in ['timestep','iteration']:
  if key in view['metrics']:base[key]=view['metrics'][key]
 if active:base['start_time_s']=active.get('initial_time_s')
 if view['metrics'].get('checkpoint_integrity'):base['last_checkpoint_integrity']=view['metrics']['checkpoint_integrity']
 base['current_obstacle']='C0 force bias""")
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
cfg=json.loads((h/'NIGHT_QUEUE.json').read_text(encoding='utf8'));cfg['controller_exit_requested']=True
tmp=h/'NIGHT_QUEUE.json.tmp';tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');os.replace(tmp,h/'NIGHT_QUEUE.json')
print('Ready: parent/child birth-time checks prevent PID-reuse misclassification; checkpoint path/size/hash/time are kept together.')
