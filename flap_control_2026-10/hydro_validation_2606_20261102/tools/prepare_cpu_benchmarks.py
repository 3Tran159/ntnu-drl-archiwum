from pathlib import Path
import json,shutil,datetime,ast,hashlib
H=Path(__file__).resolve().parents[1];cfg=json.loads((H/'NIGHT_QUEUE.json').read_text());st=json.loads((H/'NIGHT_QUEUE_STATE.json').read_text())
assert st.get('active') is None and not (H/'audit/night_queue.lock').exists()
b=H/'audit'/('before_cpu_benchmark_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));b.mkdir()
def edit(n,fn):
 p=H/'tools'/n;shutil.copy2(p,b/n);s=fn(p.read_text());ast.parse(s);p.write_text(s,encoding='utf8')
def rep(s,a,z):assert s.count(a)==1,(a,s.count(a));return s.replace(a,z)
def queue(s):
 s=rep(s,"ALLOWED.update(['KinematicPoc333939.java','PrepareStaticPlus2.java'])","ALLOWED.update(['KinematicPoc333939.java','PrepareStaticPlus2.java','BenchmarkStaticPlus2.java'])")
 s=s.replace("cfg['max_cpu_processes']==8","cfg['max_cpu_processes']==16").replace('max_cpu_processes=8','max_cpu_processes=16')
 s=rep(s,"  elif j.get('kind')=='static_preparation':","  elif j.get('kind')=='benchmark':\n   assert j['macro']=='BenchmarkStaticPlus2.java' and j.get('angle_deg')==2 and j.get('cpu_processes') in [8,12,16]\n   assert cfg['scientific_gates'].get('kinematic_sweep_accepted') is True\n  elif j.get('kind')=='static_preparation':")
 s=rep(s,'def output_path(receipt):',"def output_path(receipt):\n if receipt['macro']=='BenchmarkStaticPlus2.java':return H/'cases/SP_C_split0_overset'/('plus2_benchmark_'+receipt['run_id'])")
 s=rep(s,"['static_pose_prepared','kinematic_poc_passed'","['benchmark_complete','static_pose_prepared','kinematic_poc_passed'")
 s=rep(s,"j['macro'],j['input']],capture_output=True", "j['macro'],j['input'],str(j.get('cpu_processes',8))],capture_output=True")
 s=rep(s,"   publish(st,cfg,metrics,rs)","   publish(st,cfg,metrics,rs)")
 s=rep(s," st=read(STATE,dict(jobs={},active=None));", " from benchmark_telemetry import start_telemetry\n start_telemetry(H)\n st=read(STATE,dict(jobs={},active=None));")
 s=rep(s," atomic(H/'NIGHT_STATUS.json',base)"," if review.get('current_job_kind')=='benchmark':\n  from benchmark_telemetry import publish_benchmark\n  publish_benchmark(H,view,base,st,review)\n  atomic(H/'NIGHT_DASHBOARD.json',view)\n atomic(H/'NIGHT_STATUS.json',base)")
 return s
edit('night_queue.py',queue)
def native(s):
 s=rep(s,"allowed['PrepareStaticPlus2.java']=8","allowed['PrepareStaticPlus2.java']=8\nallowed['BenchmarkStaticPlus2.java']=16")
 s=rep(s,"name=sys.argv[1];assert name in allowed", "name=sys.argv[1];assert name in allowed\ncpu=int(sys.argv[3]) if len(sys.argv)>3 else allowed[name]\nassert cpu in [8,12,16] if name=='BenchmarkStaticPlus2.java' else cpu<=allowed[name]\nassert 1<=cpu<=16")
 return s.replace('str(allowed[name])','str(cpu)').replace('cpu_processes=allowed[name]','cpu_processes=cpu')
edit('night_native.py',native)
src=H/'cases/SP_C_split0_overset/static_plus2_prepared_20261103_085250/SP_C_plus2_prepared_NOT_SOLVED_2606.sim'
with src.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()=='4f5fd71acc76a75f21fbacdaa8d6e2e0c3b4145d34fd3480b0a19429fbeba22a'
for np in [8,12,16]:cfg['jobs'].append(dict(id='plus2_benchmark_'+str(np)+'cpu_20261103',macro='BenchmarkStaticPlus2.java',input=str(src),approved=True,kind='benchmark',angle_deg=2,cpu_processes=np,initial_time_s=.67,gate='kinematic_sweep_accepted'))
cfg.update(max_cpu_processes=16,controller_exit_requested=False,accept_new_jobs=True)
(H/'NIGHT_QUEUE.json').write_text(json.dumps(cfg,indent=2),encoding='utf8')
r=json.loads((H/'WORK_CURRENT_REVIEW.json').read_text());r.update(current_job_kind='benchmark',status='BENCHMARK_AUTHORIZED',last_decision='Sequential8/12/16MPI benchmark from identical +2t0.670 checkpoint.3warmup+7timed steps. Strict scientific guards unchanged. Stop later variants after +2experiment.',next='Compare timings,communication,hardware telemetry and numerical agreement; select fastest stable configuration before continuation.',obstacle='Thermal sensors access denied; thermal/power cause cannot be certified from Windows counters alone.');r['parameters']['CPU_max']=16
(H/'WORK_CURRENT_REVIEW.json').write_text(json.dumps(r,indent=2),encoding='utf8')
with (H/'NIGHT_DECISIONS.jsonl').open('a') as f:f.write(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),kind='cpu_limit_update_and_benchmark',maximum=16,ranks=[8,12,16],input_sha256='4f5fd71acc76a75f21fbacdaa8d6e2e0c3b4145d34fd3480b0a19429fbeba22a',backup=str(b)))+'\n')
print('Three sequential guarded benchmarks prepared; existing queue only.')
