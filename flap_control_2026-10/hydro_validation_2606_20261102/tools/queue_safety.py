"""Safety additions for the existing controller; no process termination."""
from pathlib import Path
import json,time,datetime,hashlib,html
def now():return datetime.datetime.now().astimezone().isoformat()
def atomic(p,data):
 t=p.with_suffix(p.suffix+'.safety.tmp');t.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf8');t.replace(p)
def job_watchdog(active,metrics,job,clock=None):
 stamp=time.time() if clock is None else clock
 signature=[metrics.get('timestep'),metrics.get('iteration'),metrics.get('physical_time_s')]
 watch=active.setdefault('watchdog',dict(started_epoch=stamp,last_progress_epoch=stamp,signature=signature))
 if signature!=watch['signature']:watch.update(signature=signature,last_progress_epoch=stamp)
 if metrics.get('saving_or_exporting'):
  watch.setdefault('saving_started_epoch',stamp)
  return 'save_timeout_preserve_process' if stamp-watch['saving_started_epoch']>job.get('save_timeout_s',1800) else None
 watch.pop('saving_started_epoch',None)
 if stamp-watch['last_progress_epoch']>job.get('progress_timeout_s',900):return 'solver_progress_timeout'
 if stamp-watch['started_epoch']>job.get('maximum_runtime_s',28800):return 'approved_runtime_exceeded'
 return None
def launch_integrity(h,job):
 p=Path(job['input']).resolve();assert p.is_relative_to(h/'cases') and p.is_file()
 assert job.get('approved') is True and not job.get('disabled')
 cpu=job.get('cpu_processes',8);cap=20 if job.get('experiment_id')=='RECOVERED_PERF_20261103' and job.get('kind') in ['recovered_perf','perf_production'] else 16;assert 1<=cpu<=cap
 expected=job.get('input_sha256');assert expected,'Missing approved input checksum'
 with p.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==expected,'Input checkpoint changed'
 macro=h/'macros'/job['macro'];assert hashlib.sha256(macro.read_bytes()).hexdigest()==job.get('macro_sha256'),'Macro changed since approval'
def recover_launch(h,st,cfg,plist,output_path):
 intent=st.get('launch_intent')
 if not intent or st.get('active'):return
 receipt_path=h/'audit/night_launch_latest.json'
 receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
 candidates=[j for j in cfg['jobs'] if j['id']==intent['id']]
 if not candidates:return
 job=candidates[0]
 if receipt.get('macro')==job['macro'] and receipt.get('input')==job['input'] and receipt.get('at','')>=intent['at']:
  receipt.update(id=job['id'],output=str(output_path(receipt)),initial_time_s=job.get('initial_time_s',0),state='active')
  st['active']=receipt;st.pop('launch_intent',None)
  return 'adopted_launch_receipt'
 # Never repeat an uncertain launch after a controller crash.
 st['failure_hold']=job['id'];st['jobs'].setdefault(job['id'],dict(state='launch_uncertain_requires_review',id=job['id']))
 st['uncertain_launch']=st.pop('launch_intent')
 return 'launch_uncertain_hold'
def automatic_job_report(h,rec):
 output=Path(rec['output']);status=rec.get('macro_status') or {}
 report=dict(at=now(),job=rec['id'],state=rec['state'],macro_status=status,checkpoints=rec.get('checkpoints',[]),log=rec.get('redacted_log'),scientific_approval=False,note='Execution completion does not approve scientific results.')
 dest=h/'reports/automatic';dest.mkdir(parents=True,exist_ok=True)
 atomic(dest/(rec['id']+'.json'),report)
 text='<html><meta charset="utf-8"><style>body{font:17px system-ui;max-width:1000px;margin:30px auto}pre{white-space:pre-wrap}</style><h1>'+html.escape(rec['id'])+'</h1><p>'+html.escape(rec['state'])+' — scientific acceptance requires the declared review gate.</p><pre>'+html.escape(json.dumps(report,indent=2))+'</pre></html>'
 (dest/(rec['id']+'.html')).write_text(text,encoding='utf8')
