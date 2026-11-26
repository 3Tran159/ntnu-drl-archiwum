"""Isolated tests. Fake solver evidence only; no STAR or other queues touched."""
from pathlib import Path
import tempfile,json,hashlib,time,os,unittest,sys
import queue_safety as safe,night_queue as q
class SafetyTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='CFD_FAKE_TEST_',dir=Path(__file__).resolve().parents[1]/'audit');self.h=Path(self.tmp.name);(self.h/'cases/fake').mkdir(parents=True);(self.h/'macros').mkdir();(self.h/'audit').mkdir();(self.h/'runs/redacted').mkdir(parents=True)
  self.old=q.H;q.H=self.h
 def tearDown(self):
  assert self.h.resolve().is_relative_to(Path(__file__).resolve().parents[1]/'audit')
  q.H=self.old;self.tmp.cleanup()
 def test_progress_watchdog(self):
  a={};self.assertIsNone(safe.job_watchdog(a,{'iteration':1},{'progress_timeout_s':30},100));self.assertIsNone(safe.job_watchdog(a,{'iteration':2},{'progress_timeout_s':30},129));self.assertEqual(safe.job_watchdog(a,{'iteration':2},{'progress_timeout_s':30},160),'solver_progress_timeout')
 def test_save_protected_and_timeout(self):
  a={};self.assertIsNone(safe.job_watchdog(a,{'saving_or_exporting':True},{'save_timeout_s':60},100));self.assertIsNone(safe.job_watchdog(a,{'saving_or_exporting':True},{'save_timeout_s':60},159));self.assertEqual(safe.job_watchdog(a,{'saving_or_exporting':True},{'save_timeout_s':60},161),'save_timeout_preserve_process')
 def test_integrity_and_cpu_limit(self):
  p=self.h/'cases/fake/a.sim';p.write_bytes(b'FAKE');m=self.h/'macros/Test.java';m.write_bytes(b'FAKE MACRO');j=dict(input=str(p),macro=m.name,approved=True,cpu_processes=16,input_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),macro_sha256=hashlib.sha256(m.read_bytes()).hexdigest());safe.launch_integrity(self.h,j)
  j['cpu_processes']=17
  with self.assertRaises(AssertionError):safe.launch_integrity(self.h,j)
  j['cpu_processes']=8;p.write_bytes(b'CHANGED')
  with self.assertRaises(AssertionError):safe.launch_integrity(self.h,j)
 def test_external_input_rejected(self):
  with self.assertRaises(AssertionError):safe.launch_integrity(self.h,dict(input=str(self.h/'protected_C01.sim'),approved=True))
 def test_adopt_after_receipt_before_state(self):
  j=dict(id='fake',macro='Test.java',input='fake.sim',initial_time_s=.67);st={'launch_intent':dict(id='fake',at='2026-11-03T00:00:00'),'jobs':{}}
  safe.atomic(self.h/'audit/night_launch_latest.json',dict(macro='Test.java',input='fake.sim',at='2026-11-03T00:00:01',pid=123))
  self.assertEqual(safe.recover_launch(self.h,st,{'jobs':[j]},[],lambda x:self.h/'cases/fake'),'adopted_launch_receipt');self.assertEqual(st['active']['pid'],123)
 def test_uncertain_launch_not_repeated(self):
  j=dict(id='fake',macro='Test.java',input='fake.sim');st={'launch_intent':dict(id='fake',at='2026-11-03T00:00:00'),'jobs':{}}
  self.assertEqual(safe.recover_launch(self.h,st,{'jobs':[j]},[],lambda x:self.h/'cases/fake'),'launch_uncertain_hold');self.assertEqual(st['failure_hold'],'fake')
 def fake_finish(self,complete=True):
  out=self.h/'cases/fake';cp=out/'checkpoint.sim';cp.write_bytes(b'FAKE_SIM');os.utime(cp,(time.time()-10,time.time()-10));safe.atomic(out/'status.json',dict(status='benchmark_complete',steps=10,saved_time_s=.69));(out/'history.csv').write_text('step,time_s,CL_hydro\n10,0.69,0.4\n');log=self.h/'runs/fake.log';log.write_text('Saving: '+str(cp)+('... complete (0GB in1s).' if complete else '...')+'\nServer process exited with code : 0\n');st=dict(active=dict(id='fake',macro='BenchmarkStaticPlus2.java',pid=999999,output=str(out),log=str(log),initial_time_s=.67),jobs={});q.scan_current(st,[]);return st
 def test_checkpoint_and_automatic_report(self):
  st=self.fake_finish();self.assertEqual(st['jobs']['fake']['state'],'completed');self.assertIsNone(st['active']);self.assertTrue((self.h/'reports/automatic/fake.json').exists());self.assertEqual(next(iter(st['checkpoint_integrity'].values()))['saved_time_s'],.69)
 def test_incomplete_save_blocks_following_jobs(self):
  st=self.fake_finish(False);self.assertEqual(st['failure_hold'],'fake');self.assertEqual(st['jobs']['fake']['state'],'failed')
if __name__=='__main__':unittest.main(verbosity=2)
