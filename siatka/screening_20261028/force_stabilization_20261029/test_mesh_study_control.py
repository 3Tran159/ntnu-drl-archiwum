"""Isolated pause/resume tests: no production marker, process or CFD action."""
import csv,json,tempfile,unittest,types
from pathlib import Path
from unittest.mock import patch,Mock
import mesh_study_control as m
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.o=self.root/'study';self.o.mkdir();self.r=self.root/'root';self.r.mkdir();self.d=self.o/'dashboard_control'
  self.patches=[patch.object(m,'O',self.o),patch.object(m,'D',self.d),patch.object(m,'R',self.r)]
  for p in self.patches:p.start()
  self.addCleanup(lambda:[p.stop() for p in self.patches]);self.addCleanup(self.tmp.cleanup)
  self.base=self.o/'force_stabilization_20261029';self.base.mkdir();self.case=self.base/'mesh_job';self.case.mkdir()
  self.src=self.root/'source.sim';self.src.write_bytes(b'original saved fields')
 def saved(self,status='stopped_by_marker',p=None,start=1.,end=1.2,source=None):
  p=p or self.case;source=source or self.src
  m.write(p/'completed.json',dict(status=status,time_s=end));m.write(p/'exit.json',dict(returncode=0,source_unchanged=True));m.write(p/'EXPORT_OK.json',dict(time_s=end));m.write(p/'source_identity.json',dict(path=str(source),sha256=m.sha(source)))
  m.write(p/'setup.json',dict(start_time_s=start,target_time_s=2.,dt_s=.1,inner_iterations=10,cells=100))
  (p/'final.sim').write_bytes(b'saved state '+str(end).encode())
 def rows(self,p,times):
  with p.open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=['physical_time_s','dt_s','CD','CL_total','pressure_drag_N','viscous_drag_N']);w.writeheader()
   for t in times:w.writerow(dict(physical_time_s=t,dt_s=.1,CD=.01,CL_total=.3,pressure_drag_N=1,viscous_drag_N=2))
 def active(self):
  s=dict(status='GPU_job_running',pid=100,star_pid=101,job='mesh_job',directory=str(self.case))
  m.write(self.o/'gpu_study_state.json',s);m.write(self.o/'gpu_live_study.lock',dict(pid=100));m.write(self.case/'process.json',dict(pid=101));return s
 def paused(self):
  self.saved();q=dict(id='pause-id',state='pause_requested',controller_pid=100,star_pid=101,directory=str(self.case),job='mesh_job')
  m.write(self.d/'pause.json',q);(self.o/'STOP').write_text(q['id']);return q
 def test_pause_requests_only_scoped_markers(self):
  s=self.active()
  with patch.object(m,'alive',return_value=True):
   self.assertTrue(m.snapshot()['can_pause']);m.pause(dict(generation=m.generation(s)))
  self.assertTrue((self.o/'STOP').exists());self.assertTrue((self.case/'STOP').exists());self.assertFalse((self.r/'STOP_ALL').exists())
 def test_stale_pause_does_not_write(self):
  self.active()
  with patch.object(m,'alive',return_value=True),self.assertRaises(ValueError):m.pause(dict(generation='old job'))
  self.assertFalse((self.o/'STOP').exists())
 def test_existing_external_stop_preserved(self):
  s=self.active();(self.o/'STOP').write_text('other reason')
  with patch.object(m,'alive',return_value=True),self.assertRaises(ValueError):m.pause(dict(generation=m.generation(s)))
  self.assertEqual((self.o/'STOP').read_text(),'other reason')
 def test_resume_waits_for_solver_exit(self):
  self.paused()
  with patch.object(m,'alive',side_effect=lambda pid:pid==101):self.assertFalse(m.snapshot()['can_resume'])
 def test_safe_pause_ready_only_after_complete_save(self):
  self.paused()
  with patch.object(m,'alive',return_value=False):self.assertTrue(m.snapshot()['can_resume'])
  (self.case/'EXPORT_OK.json').unlink()
  with patch.object(m,'alive',return_value=False):self.assertFalse(m.snapshot()['can_resume'])
 def test_guards_block_saved_resume(self):
  for status in ['CFL_guard','stability_guard','wall_budget']:
   self.saved(status)
   with self.assertRaises(ValueError):m.safe_saved(self.case)
 def test_source_mutation_blocks(self):
  self.saved();self.src.write_bytes(b'changed')
  with self.assertRaises(ValueError):m.safe_saved(self.case,True)
 def test_stop_identity_cannot_be_cleared_by_resume(self):
  self.paused();(self.o/'STOP').write_text('other')
  with patch.object(m,'alive',return_value=False):self.assertFalse(m.snapshot()['can_resume'])
 def test_duplicate_resume_blocked(self):
  self.paused();m.write(self.d/'launch.json',dict(pid=202))
  with patch.object(m,'alive',side_effect=lambda pid:pid==202),patch.object(m.subprocess,'Popen') as launch:
   with self.assertRaises(ValueError):m.resume(dict(generation='pause-id'))
   launch.assert_not_called()
 def test_resume_routes_to_separate_controller(self):
  self.paused()
  with patch.object(m,'alive',return_value=False),patch.object(m.subprocess,'Popen',return_value=types.SimpleNamespace(pid=202)) as launch:
   m.resume(dict(generation='pause-id'))
   self.assertIn('--resume',launch.call_args.args[0]);self.assertEqual((self.o/'STOP').read_text(),'pause-id')
 def test_busy_root_blocks_resume(self):
  self.paused();(self.r/'queue.lock').write_text('{}')
  with patch.object(m,'alive',return_value=False),patch.object(m.subprocess,'Popen') as launch:
   with self.assertRaises(ValueError):m.resume(dict(generation='pause-id'))
   launch.assert_not_called()
 def test_history_continuity_and_no_raw_mutation(self):
  a=self.root/'a.csv';b=self.root/'b.csv';self.rows(a,[1.1,1.2]);self.rows(b,[1.3,1.4]);before=[m.sha(a),m.sha(b)]
  rows=m.combined_history([a,b],self.root/'merged.csv',.1,1.4)
  self.assertEqual(len(rows),4);self.assertEqual(before,[m.sha(a),m.sha(b)])
 def test_history_gaps_duplicates_and_wrong_end_block(self):
  a=self.root/'a.csv';b=self.root/'b.csv';self.rows(a,[1.1,1.2])
  for times,end in [([1.2,1.3],1.3),([1.4,1.5],1.5),([1.3,1.4],1.5)]:
   self.rows(b,times)
   with self.assertRaises(ValueError):m.combined_history([a,b],self.root/'bad.csv',.1,end)
 def test_completed_stage_replayed_without_launch(self):
  self.saved('stabilized');g=types.SimpleNamespace(BASE=self.base);launch=Mock()
  out=m.replay_job(g,launch,'mesh_job',self.src,dict(NTNU_STAB_START='1',NTNU_STAB_TARGET='2',NTNU_STAB_DT='.1',NTNU_STAB_INNER='10',NTNU_STAB_CELLS='100'))
  self.assertEqual(out,self.case);launch.assert_not_called()
 def test_paused_stage_resumes_unique_attempt_exact_checkpoint(self):
  self.saved();self.rows(self.case/'history.csv',[1.1,1.2]);g=types.SimpleNamespace(BASE=self.base);launch=Mock(return_value='new attempt')
  m.replay_job(g,launch,'mesh_job',self.src,dict(NTNU_STAB_START='1',NTNU_STAB_TARGET='2',NTNU_STAB_DT='.1',NTNU_STAB_INNER='10',NTNU_STAB_CELLS='100'))
  name,src,env=launch.call_args.args
  self.assertTrue(name.startswith('mesh_job_resume_'));self.assertEqual(src,self.case/'final.sim');self.assertEqual(float(env['NTNU_STAB_START']),1.2);self.assertEqual(env['NTNU_STAB_TARGET'],'2')
  self.assertTrue(Path(env['NTNU_STAB_PRIOR_HISTORY']).is_file())
 def test_lineage_expansion_retains_unique_history(self):
  a=self.case/'history.csv';b=self.base/'new'/'history.csv';m.write(self.d/'lineages'/'new.json',dict(histories=[str(a),str(b)]))
  self.assertEqual(m.expand_histories([a,b]),[a,b])
if __name__=='__main__':unittest.main()
