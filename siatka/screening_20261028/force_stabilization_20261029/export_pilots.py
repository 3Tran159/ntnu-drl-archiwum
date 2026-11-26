import sys,os,subprocess,hashlib,json,time
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
sys.path.insert(0,str(R.parent/'night_20261028'))
from night_queue import STAR,saved_options,redact,free_memory
for mesh in ['M03','M02']:
 out=R/(mesh+'_pilot_post');out.mkdir(exist_ok=True)
 if (out/'EXPORT_OK.json').exists():continue
 if (out/'star.log').exists():raise RuntimeError('Previous incomplete export; inspect before retry')
 if free_memory()<16*1024**3:raise RuntimeError('Not enough free RAM')
 source=Q/(mesh+'_GPU')/'F18_dt1000us_long/checkpoint.sim'
 before=hashlib.sha256(source.read_bytes()).hexdigest()
 env=dict(os.environ,NTNU_POST_OUT=str(out))
 with (out/'star.log').open('x',encoding='utf-8') as f:
  p=subprocess.Popen([str(STAR),*saved_options(1),'-batch',str(R/'ExportFlowFields.java'),str(source)],env=env,cwd=str(out),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
  (out/'process.json').write_text(json.dumps({'pid':p.pid,'started_unix':time.time(),'purpose':'read-only field export; no solver steps'}))
  for line in p.stdout:f.write(redact(line));f.flush()
  rc=p.wait()
 (out/'export_result.json').write_text(json.dumps({'returncode':rc,'source_unchanged':hashlib.sha256(source.read_bytes()).hexdigest()==before,'source_sha256':before}))
 if rc!=0 or not (out/'EXPORT_OK.json').exists():raise RuntimeError('Export failed for '+mesh)
print('Pilot field exports completed')
