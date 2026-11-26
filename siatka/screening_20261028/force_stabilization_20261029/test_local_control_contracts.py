"""Isolated Python workflow regressions. No real STAR, process control, file opening or production queue writes.
All R/W/D paths are replaced by a temporary tree. Solver results are explicit mocks.
This suite does not validate Java API execution, CFD propagation or force accuracy.
"""
from pathlib import Path
import unittest,unittest.mock as mock,tempfile,json,hashlib,datetime,subprocess,os,sys,io,types,csv,math,contextlib,importlib
ROOT=Path(__file__).resolve().parent
FILES=[]  # Replaced by the model's current TESTED_SOURCES contract after import.
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def forbidden(*a,**k):raise AssertionError('Real external action blocked by isolated test harness')
# Block external effects BEFORE importing workflow modules.
BLOCKS=contextlib.ExitStack()
BLOCKS.enter_context(mock.patch('subprocess.Popen',side_effect=forbidden))
BLOCKS.enter_context(mock.patch('subprocess.run',side_effect=forbidden))
BLOCKS.enter_context(mock.patch('os.startfile',side_effect=forbidden))
import local_control_model as m
FILES=list(m.TESTED_SOURCES)
import local_control_worker as w
import local_domain_preparation as domain
import test_local_wave_arrival as arrival_tests
import force_reference as lift
RAW=dict(name='W01a',height_m=.5,wavelength_m=20,upstream_m=35,downstream_m=43.81,wall_minutes=180,action='run')

class Contracts(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='ntnu_local_contract_');self.root=Path(self.tmp.name).resolve()
  self.r=self.root/'R';self.ww=self.root/'W';self.dd=self.r/'local_control'
  for p in (self.r,self.ww,self.dd):p.mkdir(parents=True,exist_ok=True)
  self.stack=contextlib.ExitStack();self.addCleanup(self.stack.close);self.addCleanup(self.tmp.cleanup)
  for mod in (m,w,domain):
   for key,value in (('R',self.r),('W',self.ww)):
    self.stack.enter_context(mock.patch.object(mod,key,value))
  self.stack.enter_context(mock.patch.object(m,'D',self.dd));self.stack.enter_context(mock.patch.object(w,'D',self.dd))
  self.stack.enter_context(mock.patch.object(w.e,'saved_options',return_value=[]))
  self.stack.enter_context(mock.patch.object(w.e,'STAR',self.r/'MOCK_STAR_NEVER_EXECUTED.exe'))
  for name in FILES:(self.r/name).write_bytes((ROOT/name).read_bytes())
  m.write(self.r/'local_control_macro_receipt.json',dict(status='javac_passed',macro_sha256=sha(self.r/'LocalCalmWave.java')))
  self.src=self.ww/'preserved_source.sim';self.src.write_bytes(b'IMMUTABLE-SYNTHETIC-SOURCE')
  self.srcsha=sha(self.src)
  self.reference=dict(available=True,cl_offset=.01,buoyancy_N=38.556,reference_force_N=3855.6,lift_basis='vertical_force_minus_buoyancy')
  self.reference_file=self.ww/'force_reference.json';m.write(self.reference_file,self.reference)
  self.stack.enter_context(mock.patch.object(lift,'reference_for_source',return_value=self.reference))
  mesh=self.ww/'mesh.CGNS';mesh.write_bytes(b'IMMUTABLE-MESH')
  self.profile=dict(id='fixture_mesh_A',label='Fixture inspected mesh',status='mechanically_compatible',file_sha256=self.srcsha,mesh_sim=str(self.src),mesh_sim_sha256=self.srcsha,mesh_cgns=str(mesh),mesh_cgns_sha256=sha(mesh),cells=317277,domain_x_m=[-35.,45.],dt_s=.001,inner=10)
  self.stack.enter_context(mock.patch.object(m,'mesh_profile',side_effect=lambda mesh_id=None:dict(self.profile)))
  self.spec=m.validate(dict(RAW))
 def job(self):return m.enqueue(dict(RAW))
 def source(self,**change):
  v=dict(force_reference_file=str(self.reference_file),force_reference_sha256=sha(self.reference_file),file=str(self.src),sha256=self.srcsha,physical_time_s=1.5,status='calm_force_settled',source_unchanged=True,cells=317277,mesh=str(self.ww/'mesh.CGNS'),mesh_id=self.spec['mesh_id'],mesh_sha256=self.spec['mesh_sha256'],domain_key=m.domain_key(self.spec),dt_s=self.spec['dt_s'],inner=10,order='SECOND_ORDER',pressure_AMG_tolerance=.01)
  v.update(change);return v
 def manifest(self,**change):
  folder=self.ww/'C01_W20L4_M10_calm_settle_r2';folder.mkdir(exist_ok=True)
  v=dict(self.source(),domain_x_m=[-35.,45.],domain_z_m=[-22,8],depth_m=24,span_m=.02,dt_s=.001,inner=10,order='SECOND_ORDER',pressure_AMG_tolerance=.01,wave_active=False,settling={'passed':True,'lift_basis':'vertical_force_minus_buoyancy'})
  v.update(change);p=folder/'settled_checkpoint.json';m.write(p,v)
  (self.dd/'calm').mkdir(exist_ok=True);m.write(self.dd/'calm'/f'{m.domain_key(self.spec)}.json',{'manifest':str(p)})
  return p
 def preflight(self):
  s=contextlib.ExitStack();s.enter_context(mock.patch.object(w,'safe_ready',return_value=True));s.enter_context(mock.patch.object(w,'resources',return_value=(64*1024**3,100*1024**3)));return s
 def history(self,old=1.,new=1.,last=400,drop=(),zero=False,reverse=False,dt=.001):
  p=self.r/'history.csv';rows=[]
  for i in range(last+1):
   if i in drop:continue
   value=(old if i*dt<=.2+1e-12 else new);rows.append([i*dt,value,value*2])
  if reverse:rows[100],rows[101]=rows[101],rows[100]
  with p.open('w',newline='',encoding='utf8') as f:
   wr=csv.writer(f);wr.writerow(['time_s','CD','CL_total']);wr.writerows(rows)
  return p
 def test_validation_all_presets_and_actions(self):
  for name,h,lam in m.PRESETS:
   for action in ('prepare','run'):
    v=m.validate(dict(name=name,height_m=h,wavelength_m=lam,upstream_m=1.75*lam,downstream_m=2.25*lam-1.19,wall_minutes=180,action=action))
    self.assertEqual(v['depth_m'],24);self.assertEqual(v['z_m'],[-22,8]);self.assertAlmostEqual(v['length_m'],4*lam)
 def test_validation_rejects_nonfinite_boolean_and_unsupported(self):
  changes=[{'height_m':float('nan')},{'wavelength_m':float('inf')},{'height_m':True},{'height_m':.4},{'wavelength_m':15},{'upstream_m':1000},{'action':'shell'},{'depth_m':16},{'name':'bad\nname'},{'upstream_m':20,'downstream_m':38.81}]
  for change in changes:
   with self.subTest(change=change),self.assertRaises(ValueError):m.validate(dict(RAW,**change))
 def test_calm_key_is_height_independent_but_domain_specific(self):
  a=m.domain_key(self.spec);self.assertEqual(a,m.domain_key(m.validate(dict(RAW,height_m=.25))))
  self.assertNotEqual(a,m.domain_key(m.validate(dict(RAW,upstream_m=25,downstream_m=33.81))))
 def test_enqueue_creates_distinct_preserved_jobs(self):
  a=self.job();b=self.job();self.assertNotEqual(a['id'],b['id']);self.assertEqual(len(m.jobs()),2)
  self.assertEqual(m.read(self.dd/'jobs'/a['id']/'job.json')['status'],'queued')
 def test_registered_calm_requires_matching_pass_and_source(self):
  self.manifest();self.assertEqual(m.registered_calm(self.spec,True)['sha256'],self.srcsha)
  for change in ({'domain_x_m':[-25,35]},{'domain_z_m':[-14,8]},{'dt_s':.002},{'inner':20},{'status':'failed'},{'source_unchanged':False},{'settling':{'passed':False}}):
   self.manifest(**change);self.assertIsNone(m.registered_calm(self.spec,True),change)
  for change in ({'mesh_id':'other_mesh'},{'mesh_sha256':'different'},{'domain_key':'wrong'},{'order':'FIRST_ORDER'},{'pressure_AMG_tolerance':.1},{'wave_active':True}):
   self.manifest(**change);self.assertIsNone(m.registered_calm(self.spec,True),change)
 def test_registered_calm_rejects_invalid_source_time(self):
  for t in (None,True,-1,0,float('nan'),float('inf')):
   self.manifest(physical_time_s=t);self.assertIsNone(m.registered_calm(self.spec,True),repr(t))
 def test_changed_calm_source_is_rejected(self):
  self.manifest();self.src.write_bytes(b'altered-fixture')
  with self.assertRaises(ValueError):m.registered_calm(self.spec,True)
 def test_cancelled_job_cannot_be_revived_or_launched(self):
  j=self.job();m.cancel(j['id'])
  with mock.patch.object(w,'safe_ready',return_value=True),mock.patch.object(w,'execute_solver') as solver:
   with self.assertRaises(w.Cancelled):w.process_job(j)
   solver.assert_not_called()
  with self.assertRaises(w.Cancelled):w.status(j,'stale writer',status='waiting')
  self.assertEqual(m.read(self.dd/'jobs'/j['id']/'job.json')['status'],'cancelled')
 def test_cancellation_while_waiting_stops_before_next_phase(self):
  j=self.job()
  with mock.patch.object(w,'safe_ready',side_effect=[False,True]),mock.patch.object(w.time,'sleep',side_effect=lambda _:m.cancel(j['id'])),mock.patch.object(w,'execute_solver') as solver:
   with self.assertRaises(w.Cancelled):w.process_job(j)
   solver.assert_not_called()
 def test_cancel_marker_survives_stale_status(self):
  j=self.job();m.cancel(j['id']);m.write(self.dd/'jobs'/j['id']/'job.json',j)
  with self.assertRaises(w.Cancelled):w.ensure_not_cancelled(j)
 def test_cancel_transition_and_active_job_are_rejected(self):
  j=self.job()
  with m.job_transition(j['id']):
   with self.assertRaises(ValueError):m.cancel(j['id'])
  j['status']='running';m.write(self.dd/'jobs'/j['id']/'job.json',j)
  with self.assertRaises(ValueError):m.cancel(j['id'])
 def test_pause_rejects_solver_before_claim(self):
  j=self.job();(self.dd/'PAUSE').touch()
  with self.assertRaises(w.Halt):w.execute_solver(j,'wave',self.source())
  self.assertFalse((self.r/'queue.lock').exists());self.assertEqual(sha(self.src),self.srcsha)
 def test_pause_after_domain_preparation_prevents_calm_launch(self):
  j=self.job()
  def prep(*a,**k):(self.dd/'PAUSE').touch();return {'path':str(self.src)}
  with mock.patch.object(w,'safe_ready',return_value=True),mock.patch.object(m,'registered_calm',return_value=None),mock.patch.object(domain,'existing',return_value=None),mock.patch.object(domain,'prepare',side_effect=prep),mock.patch.object(w,'execute_solver') as solver:
   with self.assertRaises(w.Halt):w.process_job(j)
   solver.assert_not_called()
 def test_domain_pause_before_and_after_atomic_cpu_phase(self):
  (self.dd/'PAUSE').touch()
  with mock.patch.object(domain,'_cpu') as cpu:
   with self.assertRaises(RuntimeError):domain.cpu([])
   cpu.assert_not_called()
  (self.dd/'PAUSE').unlink()
  with mock.patch.object(domain,'_cpu',side_effect=lambda *a,**k:(self.dd/'PAUSE').touch()) as cpu:
   with self.assertRaises(RuntimeError):domain.cpu([])
   self.assertEqual(cpu.call_count,1)
   with self.assertRaises(RuntimeError):domain.cpu([])
   self.assertEqual(cpu.call_count,1)
 def test_lock_release_respects_pid_and_token(self):
  p=self.r/'queue.lock';m.write(p,dict(pid=os.getpid(),token='other'));w.release(p,'mine');self.assertTrue(p.exists())
  m.write(p,dict(pid=os.getpid()+1,token='mine'));w.release(p,'mine');self.assertTrue(p.exists())
  m.write(p,dict(pid=os.getpid(),token='mine'));w.release(p,'mine');self.assertFalse(p.exists())
 def test_solver_inventory_fails_closed(self):
  (self.r/'queue.lock').touch();self.assertFalse(w.safe_ready());(self.r/'queue.lock').unlink()
  (self.ww/'preparation.lock').touch();self.assertFalse(w.safe_ready());(self.ww/'preparation.lock').unlink()
  with mock.patch.object(w.subprocess,'run',return_value=types.SimpleNamespace(returncode=0,stdout='33892\n')):self.assertFalse(w.safe_ready())
  with mock.patch.object(w.subprocess,'run',return_value=types.SimpleNamespace(returncode=1,stdout='')):
   with self.assertRaises(w.Halt):w.safe_ready()
 def test_process_inventory_is_scoped_to_owned_absolute_paths(self):
  import re
  with mock.patch.object(w.subprocess,'run',return_value=types.SimpleNamespace(returncode=0,stdout='')) as query:
   self.assertTrue(w.safe_ready());command=query.call_args.args[0][-1]
  self.assertIn('Replace([char]92,[char]47)',command)
  patterns=re.findall(r"-match '([^']+)'",command);path_pattern=patterns[-1]
  owned=['E:/ntnu/quasi2d_waves_20261029/case/input.sim','F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/Run.java']
  independent='C:/Users/ThinkPad/Documents/ChatGPT/ntnu science/mesh_study_20261030/gci_w01a_20261030/force_stabilization_20261029/ContinueCalmGCI.java'
  for p in owned:self.assertRegex(p,path_pattern)
  self.assertIsNone(re.search(path_pattern,independent,re.I));self.assertIsNone(re.search(path_pattern,'E:/ntnu/quasi2d_waves_20261029_other/input.sim',re.I))
 def test_source_time_rejected_before_any_solver(self):
  for t in (None,True,-1,0,float('nan'),float('inf')):
   j=self.job()
   with self.preflight(),self.assertRaisesRegex(w.Halt,'source physical time'):w.execute_solver(j,'wave',self.source(physical_time_s=t))
  self.assertEqual(sha(self.src),self.srcsha)
 def test_source_path_hash_and_settled_status_fail_closed(self):
  outside=self.root/'outside.sim';outside.write_bytes(b'outside')
  for src in (self.source(file=str(outside),sha256=sha(outside)),self.source(sha256='bad'),self.source(status='stability_guard'),self.source(source_unchanged=False)):
   with self.preflight(),self.assertRaises(w.Halt):w.execute_solver(self.job(),'wave',src)
  self.assertEqual(sha(self.src),self.srcsha)
 def fake_solver(self,status='stability_guard',prepared=False):
  def launch(*a,**kw):
   folder=Path(kw['cwd'])
   if prepared:
    (folder/'prepared_wave.sim').write_bytes(b'MOCK_PREPARED_DEFINITION')
    m.write(folder/'prepared_wave_audit.json',dict(flow_steps=0,time_s=1.5,global_reinitialization=False))
   else:
    (folder/'final.sim').write_bytes(b'MOCK_DIAGNOSTIC_OUTPUT');m.write(folder/'completed.json',dict(status=status,steps=10,time_s=1.51))
   return types.SimpleNamespace(pid=987654321,stdout=io.StringIO('mock solver output\n'),poll=lambda:0,wait=lambda timeout=None:0)
  return launch
 def test_physical_guard_never_becomes_success_or_settled(self):
  j=self.job()
  with self.preflight(),mock.patch.object(w.subprocess,'Popen',side_effect=self.fake_solver()):
   with self.assertRaises(w.Halt):w.execute_solver(j,'wave',self.source())
  self.assertEqual(sha(self.src),self.srcsha);self.assertFalse((self.r/'queue.lock').exists())
  folder=Path(j['attempts'][0]['directory']);self.assertTrue((folder/'final.sim').exists());self.assertFalse((folder/'settled_checkpoint.json').exists())
 def test_preparation_uses_unique_copies_and_does_not_mutate_source(self):
  result=[]
  with self.preflight(),mock.patch.object(w.subprocess,'Popen',side_effect=self.fake_solver(prepared=True)):
   for _ in range(2):result.append(w.execute_solver(self.job(),'wave_setup',self.source()))
  self.assertNotEqual(result[0]['directory'],result[1]['directory'])
  for r in result:
   self.assertEqual(r['status'],'prepared_wave_definition');self.assertEqual(r['flow_steps'],0)
   self.assertEqual(sha(Path(r['directory'])/'input.sim'),self.srcsha)
  self.assertEqual(sha(self.src),self.srcsha)
 def test_failed_job_halts_queue_before_second_job(self):
  a=self.job();b=self.job();kernel=mock.MagicMock();kernel.GetCurrentProcess.return_value=1;kernel.SetProcessAffinityMask.return_value=1
  with mock.patch.object(w.ctypes,'windll',types.SimpleNamespace(kernel32=kernel)),mock.patch.object(w.sys,'argv',['worker','--run']),mock.patch.object(m,'readiness',return_value={'ready':True}),mock.patch.object(w,'process_job',side_effect=w.Halt('Mock physical failure')) as proc,mock.patch.object(w.subprocess,'run',return_value=types.SimpleNamespace(returncode=0)):
   w.main()
  self.assertEqual(proc.call_count,1);self.assertEqual(m.read(self.dd/'jobs'/a['id']/'job.json')['status'],'needs_review')
  self.assertEqual(m.read(self.dd/'jobs'/b['id']/'job.json')['status'],'queued');self.assertTrue((self.dd/'PAUSE').exists())
 def test_automated_start_refuses_existing_pause_without_clearing(self):
  (self.dd/'PAUSE').touch()
  with mock.patch.object(m,'readiness',return_value={'ready':True}),mock.patch.object(m.subprocess,'Popen') as launch:
   with self.assertRaisesRegex(ValueError,'automated start refused'):m.start_worker(resume=False)
   launch.assert_not_called()
  self.assertTrue((self.dd/'PAUSE').exists())
 def test_automated_start_preserves_pause_arriving_during_preflight(self):
  self.job()
  def ready():(self.dd/'PAUSE').touch();return {'ready':True}
  with mock.patch.object(m,'readiness',side_effect=ready),mock.patch.object(m.subprocess,'Popen',return_value=types.SimpleNamespace(pid=987654321)):
   m.start_worker(resume=False)
  self.assertTrue((self.dd/'PAUSE').exists(),'A racing Pause must remain for the worker entry guard')
  with mock.patch.object(w,'safe_ready',return_value=True),mock.patch.object(w,'execute_solver') as solver:
   with self.assertRaises(w.Halt):w.process_job(self.job())
   solver.assert_not_called()
 def test_acknowledge_preserves_attempt_and_blocks_unreviewed_restart(self):
  j=self.job();w.stop_report(j,'mock halt')
  with mock.patch.object(m,'readiness',return_value={'ready':True}),self.assertRaises(ValueError):m.start_worker()
  m.acknowledge(j['id']);self.assertEqual(m.read(self.dd/'jobs'/j['id']/'job.json')['status'],'reviewed_archived')
  self.assertTrue((self.dd/'PAUSE').exists())
 def test_latest_mean_denominator_and_signed_change(self):
  self.assertTrue(hasattr(w,'calm_screen'),'New worker calm_screen missing')
  r=w.calm_screen(self.history(new=.99502));self.assertFalse(r['pass'])
  self.assertAlmostEqual(r['coefficients']['CD']['change_pct'],100*(.99502-1)/.99502,places=10)
  r=w.calm_screen(self.history(new=1.00501));self.assertTrue(r['pass'])
  self.assertAlmostEqual(r['coefficients']['CD']['change_pct'],100*(1.00501-1)/1.00501,places=10)
 def test_calm_coverage_sample_floor_gap_and_zero_mean(self):
  for kw in ({'last':399},{'drop':(50,51)},{'drop':(100,101,102,103)},{'old':0,'new':0},{'reverse':True}):
   with self.subTest(kw=kw):self.assertFalse(w.calm_screen(self.history(**kw))['pass'])
  self.assertFalse(w.calm_screen(self.history(drop=(50,)))['pass'],'An isolated missing step remains a prohibited gap')
  boundary=w.calm_screen(self.history(dt=.001005));self.assertTrue(boundary['pass']);self.assertEqual(boundary['samples'],[199,200])
 def test_unsafe_file_open_is_rejected_and_valid_open_is_mocked(self):
  allowed=self.ww/'result.sim';allowed.write_bytes(b'saved');outside=self.root/'outside.sim';outside.write_bytes(b'outside')
  with mock.patch.object(m,'file_choices',return_value=[{'path':str(allowed)},{'path':str(outside)}]),mock.patch.object(m.os,'startfile') as opening:
   for bad in (outside,self.ww/'unlisted.sim',self.ww/'missing.sim'):
    with self.assertRaises(ValueError):m.open_file(str(bad))
   opening.assert_not_called();m.open_file(str(allowed));opening.assert_called_once_with(str(allowed.resolve()))
 def readiness_fixture(self):
  hashes={n:sha(self.r/n) for n in FILES};macro=hashes['LocalCalmWave.java']
  m.write(self.r/'local_control_macro_receipt.json',dict(status='javac_passed',macro_sha256=macro))
  m.write(self.r/'local_control_zero_step_review.json',dict(status='zero_step_API_audit_passed',macro_sha256=macro))
  m.write(self.r/'local_control_test_review.json',dict(status='passed',source_sha256=hashes))
 def paused_job(self,**change):
  j=self.job();manifest=self.source(status='safe_saved_continuation',mode='wave',physical_guard_failed=False,activation_time_s=.587,period_s=.847,arrival_assessment=None,history_files=[],guard_checked=True,kind='final',startup_complete=True)
  manifest.update(change);p=self.ww/'resume_manifest.json';m.write(p,manifest)
  j.update(status='paused',resume_manifest=str(p));m.write(self.dd/'jobs'/j['id']/'job.json',j);return j,manifest
 def test_hold_keeps_enqueue_only_and_blocks_all_solver_start_paths(self):
  m.write(self.r/'campaign_hold.json',dict(active=True,reason='Other mesh study'))
  with mock.patch.object(m.subprocess,'Popen') as launch:
   j=self.job();self.assertEqual(j['status'],'queued')
   with self.assertRaisesRegex(ValueError,'hold'):m.start_worker()
   with self.assertRaises(w.Halt):w.execute_solver(j,'wave',self.source())
   with mock.patch.object(w,'safe_ready',return_value=True),self.assertRaises(w.Halt):w.process_job(j)
   launch.assert_not_called()
  self.assertFalse((self.r/'queue.lock').exists())
 def test_release_hold_is_explicit_and_keeps_queue_paused(self):
  m.write(self.r/'campaign_hold.json',dict(active=True))
  with mock.patch.object(m.subprocess,'Popen') as launch:
   m.release_hold();launch.assert_not_called()
  self.assertFalse(m.hold()['active']);self.assertTrue((self.dd/'PAUSE').exists())
 def test_hold_does_not_masquerade_as_recipe_failure(self):
  self.readiness_fixture();m.write(self.r/'campaign_hold.json',dict(active=True))
  r=m.readiness();self.assertTrue(r['recipe_ready']);self.assertTrue(r['can_validate_recipe']);self.assertFalse(r['ready'])
 def test_preparation_pause_wrapper_honours_campaign_hold(self):
  m.write(self.r/'campaign_hold.json',dict(active=True))
  with mock.patch.object(domain,'_cpu') as cpu:
   with self.assertRaises(RuntimeError):domain.cpu([])
   cpu.assert_not_called()
 def test_selected_mesh_identity_and_dt_change_calm_key(self):
  first=m.domain_key(self.spec)
  self.profile['id']='fixture_mesh_B';self.assertNotEqual(first,m.domain_key(m.validate(dict(RAW))))
  self.profile['id']=self.spec['mesh_id'];self.profile['dt_s']=.0001;self.assertNotEqual(first,m.domain_key(m.validate(dict(RAW))))
  self.profile['dt_s']=.001;self.profile['file_sha256']='different';self.assertNotEqual(first,m.domain_key(m.validate(dict(RAW))))
 def test_invalid_selected_dt_and_checkpoint_cadence_are_rejected(self):
  for dt in (float('nan'),.00001,.002):
   self.profile['dt_s']=dt
   with self.assertRaises(ValueError):m.validate(dict(RAW))
  self.profile['dt_s']=.0003
  with self.assertRaises(ValueError):m.validate(dict(RAW,checkpoint_interval_s=.05))
  self.assertEqual(m.validate(dict(RAW,checkpoint_interval_s=.06))['dt_s'],.0003)
  self.profile['inner']=50
  with self.assertRaises(ValueError):m.validate(dict(RAW,checkpoint_interval_s=.06))
 def test_queue_rejects_changed_selected_mesh_before_launch(self):
  j=self.job();self.profile['file_sha256']='changed'
  with self.preflight(),self.assertRaisesRegex(w.Halt,'mesh identity'):w.execute_solver(j,'wave',self.source())
  self.assertFalse(j['attempts']);self.assertFalse((self.r/'queue.lock').exists())
 def test_profile_dt_cells_and_checkpoint_interval_reach_mock_setup(self):
  self.profile.update(dt_s=.0001,cells=595285);self.spec=m.validate(dict(RAW))
  with self.preflight(),mock.patch.object(w.subprocess,'Popen',side_effect=self.fake_solver(prepared=True)) as launch:
   w.execute_solver(self.job(),'wave_setup',self.source(cells=595285))
  env=launch.call_args.kwargs['env']
  self.assertEqual(float(env['NTNU_WAVE_DT']),.0001);self.assertEqual(int(env['NTNU_WAVE_CELLS']),595285);self.assertEqual(int(env['NTNU_WAVE_STEPS']),400000)
  self.assertEqual(float(env['NTNU_CHECKPOINT_INTERVAL_S']),.05);self.assertEqual(env['NTNU_RESUME_WAVE'],'false')
  self.assertNotIn('-gpgpu',launch.call_args.args[0]);self.assertEqual(sha(self.src),self.srcsha)
 def test_calm_screen_matches_profile_dt_and_latest_mean(self):
  r=w.calm_screen(self.history(new=1.00501,last=4000,dt=.0001),.0001)
  self.assertTrue(r['pass']);self.assertEqual(r['samples'],[2000,2000])
  self.assertAlmostEqual(r['coefficients']['CD']['change_pct'],100*(1.00501-1)/1.00501,places=10)
  self.assertFalse(w.calm_screen(self.history(last=4000,dt=.0001,drop=(500,)),.0001)['pass'])
 def test_continue_is_queue_only_and_retains_original_clock(self):
  j,manifest=self.paused_job();(self.dd/'PAUSE').touch();original_attempts=list(j['attempts'])
  with mock.patch.object(m.subprocess,'Popen') as launch:
   m.continue_job(j['id']);launch.assert_not_called()
  queued=m.read(self.dd/'jobs'/j['id']/'job.json')
  self.assertEqual(queued['status'],'queued');self.assertEqual(queued['attempts'],original_attempts);self.assertEqual(queued['resume_source']['activation_time_s'],.587);self.assertTrue((self.dd/'PAUSE').exists())
 def test_continue_rejects_failure_changed_file_and_changed_domain(self):
  for change in ({'physical_guard_failed':True},{'sha256':'changed'},{'mesh_id':'other'},{'domain_key':'other'}):
   j,_=self.paused_job(**change)
   with self.assertRaises(ValueError):m.continue_job(j['id'])
  j,_=self.paused_job();j['status']='needs_review';m.write(self.dd/'jobs'/j['id']/'job.json',j)
  with self.assertRaises(ValueError):m.continue_job(j['id'])
  m.write(self.r/'campaign_hold.json',{'active':True});j,_=self.paused_job()
  with self.assertRaises(ValueError):m.continue_job(j['id'])
 def test_resuming_wave_keeps_activation_and_avoids_new_calm_phase(self):
  j,source=self.paused_job();source.update(mode='wave')
  with self.preflight(),mock.patch.object(w.subprocess,'Popen',side_effect=self.fake_solver()) as launch:
   with self.assertRaises(w.Halt):w.execute_solver(j,'wave',source)
  env=launch.call_args.kwargs['env'];self.assertEqual(env['NTNU_RESUME_WAVE'],'true');self.assertEqual(float(env['NTNU_WAVE_ACTIVATION_TIME']),.587);self.assertEqual(float(env['NTNU_SOURCE_TIME']),1.5)
  self.assertEqual(sha(self.src),self.srcsha)
 def test_resume_rejects_invalid_profile_and_guard_before_launch(self):
  for change in ({'dt_s':.002},{'physical_guard_failed':True},{'domain_key':'other'},{'mode':'calm'}):
   j,source=self.paused_job(**change)
   with self.preflight(),self.assertRaises(w.Halt):w.execute_solver(j,'wave',source)
   self.assertFalse(j['attempts'])
 def test_resume_calm_pause_does_not_advance_to_wave(self):
  j,source=self.paused_job(mode='calm');j['resume_source']=source
  with mock.patch.object(w,'safe_ready',return_value=True),mock.patch.object(w,'execute_solver',return_value={'status':'paused','resume_manifest':'fixture'}) as solver:
   result=w.process_job(j)
  self.assertEqual(result['status'],'paused');self.assertEqual(solver.call_count,1);self.assertEqual(solver.call_args.args[1],'calm')
 def stopped_solver(self,history_time=1.51,guard_kind='final',guard_checked=True):
  def launch(*a,**kw):
   folder=Path(kw['cwd']);f=folder/'final.sim';f.write_bytes(b'MOCK_STOPPED_SAVED_FIELD');(folder/'STOP').touch()
   m.write(folder/'completed.json',dict(status='stopped_by_marker',steps=10,time_s=1.51))
   m.write(folder/'latest_checkpoint.json',dict(file=str(f),time_s=history_time,saved_time_s=history_time,completed_save=True,guard_checked=guard_checked,kind=guard_kind,max_speed_m_s=24,alpha_min=0,alpha_max=1,dt_s=.001))
   (folder/'history.csv').write_text('time_s,max_speed_m_s,alpha_min,alpha_max,CD,CL_total\n'+str(history_time)+',24,0,1,.01,.2\n')
   return types.SimpleNamespace(pid=987654321,stdout=io.StringIO('mock stopped\n'),poll=lambda:0,wait=lambda timeout=None:0)
  return launch
 def test_normal_guarded_stop_creates_safe_paused_manifest(self):
  with self.preflight(),mock.patch.object(w.subprocess,'Popen',side_effect=self.stopped_solver()),mock.patch.object(w.audit,'native_audit',return_value={'pass':True}):
   result=w.execute_solver(self.job(),'wave',self.source())
  self.assertEqual(result['status'],'paused');saved=m.read(Path(result['resume_manifest']))
  self.assertEqual(saved['physical_time_s'],1.51);self.assertFalse(saved['physical_guard_failed']);self.assertEqual(sha(self.src),self.srcsha)
 def test_mismatched_saved_time_or_incomplete_guard_cannot_continue(self):
  for kwargs in ({'history_time':1.509},{'guard_kind':'startup_user_stop'},{'guard_checked':False}):
   with self.subTest(kwargs=kwargs),self.preflight(),mock.patch.object(w.subprocess,'Popen',side_effect=self.stopped_solver(**kwargs)),mock.patch.object(w.audit,'native_audit',return_value={'pass':True}),self.assertRaises(w.Halt):
    w.execute_solver(self.job(),'wave',self.source())
 def test_invalid_wave_clock_and_history_lineage_refused_before_launch(self):
  changes=[{'activation_time_s':float('nan')},{'activation_time_s':2},{'activation_time_s':True},{'period_s':float('inf')},{'period_s':0},{'arrival_assessment':{'established':True,'analysis_origin_s':2}}]
  history=self.ww/'old_history.csv';history.write_text('preserved evidence')
  changes.append({'history_files':[str(history)],'history_sha256':{str(history):'changed'}})
  outside=self.root/'outside_history.csv';outside.write_text('unrelated history');traversal=self.ww/'..'/'outside_history.csv'
  changes.append({'history_files':[str(traversal)],'history_sha256':{str(traversal):sha(outside)}})
  for change in changes:
   j,source=self.paused_job(**change)
   with self.preflight(),self.assertRaises(w.Halt):w.execute_solver(j,'wave',source)
   self.assertFalse(j['attempts'])
 def test_calm_acceptance_requires_guarded_final_and_preserves_metadata(self):
  def fake_calming(guard):
   def launch(*a,**kw):
    proc=self.stopped_solver(guard_checked=guard)(*a,**kw);folder=Path(kw['cwd']);(folder/'STOP').unlink()
    count=iter([None,0]);proc.poll=lambda:next(count,0);return proc
   return launch
  for guard in (False,True):
   j=self.job()
   with self.preflight(),mock.patch.object(w.subprocess,'Popen',side_effect=fake_calming(guard)),mock.patch.object(w.audit,'native_audit',return_value={'pass':True}),mock.patch.object(w.audit,'history_guard',return_value=None),mock.patch.object(w,'calm_screen',return_value={'pass':True,'coefficients':{'CD':{'change_pct':.1},'CL_total':{'change_pct':.1}}}),mock.patch.object(w.time,'sleep'):
    if not guard:
     with self.assertRaises(w.Halt):w.execute_solver(j,'calm',self.source())
    else:
     result=w.execute_solver(j,'calm',self.source());self.assertEqual(result['status'],'calm_force_settled')
     cp=m.read(Path(result['file']).parent/'latest_checkpoint.json');self.assertTrue(cp['guard_checked']);self.assertEqual(cp['kind'],'settled_calm')
   if not guard:self.assertFalse((Path(j['attempts'][0]['directory'])/'C01_settled.sim').exists())
 def test_paused_result_halts_queue_normally_before_next_job(self):
  a=self.job();b=self.job();kernel=mock.MagicMock();kernel.GetCurrentProcess.return_value=1;kernel.SetProcessAffinityMask.return_value=1
  with mock.patch.object(w.ctypes,'windll',types.SimpleNamespace(kernel32=kernel)),mock.patch.object(w.sys,'argv',['worker','--run']),mock.patch.object(m,'readiness',return_value={'ready':True}),mock.patch.object(w,'process_job',return_value={'status':'paused','resume_manifest':'fixture'}) as proc,mock.patch.object(w.subprocess,'run',return_value=types.SimpleNamespace(returncode=0)):
   w.main()
  self.assertEqual(proc.call_count,1);self.assertEqual(m.read(self.dd/'jobs'/a['id']/'job.json')['status'],'paused');self.assertEqual(m.read(self.dd/'jobs'/b['id']/'job.json')['status'],'queued')
  self.assertTrue((self.dd/'PAUSE').exists())
 def test_readiness_requires_matching_tested_source_hashes(self):
  hashes={n:sha(self.r/n) for n in FILES};macro=hashes['LocalCalmWave.java']
  m.write(self.r/'local_control_macro_receipt.json',dict(status='javac_passed',macro_sha256=macro))
  m.write(self.r/'local_control_zero_step_review.json',dict(status='zero_step_API_audit_passed',macro_sha256=macro))
  m.write(self.r/'local_control_test_review.json',dict(status='passed',source_sha256=hashes))
  self.assertTrue(m.readiness()['ready'])
  (self.r/'local_control_worker.py').write_text('changed AFTER tests')
  self.assertFalse(m.readiness()['ready'],'Stale passed review must not authorize changed code')

 def test_corrected_calm_uses_buoyancy_removed_mean_and_preserves_history(self):
  p=self.history(new=1.00501);before=sha(p)
  r=w.calm_screen(p,force_reference=self.reference)
  self.assertEqual(r['lift_basis'],'vertical_force_minus_buoyancy')
  self.assertIn('CL',r['coefficients']);self.assertNotIn('CL_total',r['coefficients'])
  self.assertAlmostEqual(r['coefficients']['CL']['mean'],2*1.00501-.01,places=9)
  self.assertAlmostEqual(r['coefficients']['CL']['change_pct'],100*(2*1.00501-2)/(2*1.00501-.01),places=9)
  self.assertEqual(sha(p),before)
 def test_missing_corrected_reference_cannot_start_solver(self):
  with self.preflight(),mock.patch.object(lift,'reference_for_source',return_value={'available':False,'reason':'missing native evidence'}),mock.patch.object(w.subprocess,'Popen') as start:
   with self.assertRaisesRegex(w.Halt,'buoyancy reference'):w.execute_solver(self.job(),'wave',self.source())
   start.assert_not_called()
  self.assertFalse((self.r/'queue.lock').exists())
 def test_legacy_raw_calm_acceptance_is_not_reused_for_corrected_lift(self):
  self.manifest(settling={'passed':True,'lift_basis':'raw_total_vertical_force'})
  self.assertIsNone(m.registered_calm(self.spec,True))
  self.manifest(force_reference_sha256=None)
  self.assertIsNone(m.registered_calm(self.spec,True))

class RecordingResult(unittest.TextTestResult):
 def __init__(self,*a,**k):super().__init__(*a,**k);self.details=[]
 def addSuccess(self,t):super().addSuccess(t);self.details.append(dict(test=t.id(),status='passed'))
 def addFailure(self,t,e):super().addFailure(t,e);self.details.append(dict(test=t.id(),status='failed',detail=self._exc_info_to_string(e,t)))
 def addError(self,t,e):super().addError(t,e);self.details.append(dict(test=t.id(),status='error',detail=self._exc_info_to_string(e,t)))
 def addSubTest(self,test,subtest,err):
  super().addSubTest(test,subtest,err)
  if err:self.details.append(dict(test=subtest.id(),status='failed',detail=self._exc_info_to_string(err,subtest)))
def main():
 before={name:sha(ROOT/name) for name in FILES}
 suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(Contracts),unittest.defaultTestLoader.loadTestsFromModule(arrival_tests)])
 buf=io.StringIO();result=unittest.TextTestRunner(stream=buf,verbosity=2,resultclass=RecordingResult).run(suite)
 after={name:sha(ROOT/name) for name in FILES};stable=before==after
 review=dict(status='passed' if result.wasSuccessful() and stable else 'failed',created_at=datetime.datetime.now().astimezone().isoformat(),source_sha256=before,sources_unchanged_during_test=stable,source_sha256_after=after,test_count=result.testsRun,failures=len(result.failures),errors=len(result.errors),tests=result.details,
 scope='Mocked Python model/worker and existing synthetic arrival suite only. Temporary R/W/D tree; all process launch/control and file-opening APIs blocked globally or replaced by explicit mocks. No production queue, source .sim, solver, GPU, or service actions. Does not validate STAR API execution, CFD propagation, mesh/time accuracy, or wave forces.')
 tag='local_control_test_preview' if '--preview' in sys.argv else 'local_control_test'
 (ROOT/(tag+'_review.json')).write_text(json.dumps(review,indent=2),encoding='utf8')
 (ROOT/(tag+'_output.txt')).write_text(buf.getvalue(),encoding='utf8')
 print(json.dumps({k:review[k] for k in ('status','test_count','failures','errors','sources_unchanged_during_test')}))
 for x in result.details:
  if x['status']!='passed':print(x['test']+': '+x['detail'][-2200:])
 if not result.wasSuccessful() or not stable:raise SystemExit(1)
if __name__=='__main__':
 try:main()
 finally:BLOCKS.close()