from pathlib import Path
import ast,datetime,shutil
R=Path(__file__).resolve().parent;p=R/'test_local_control_contracts.py';s=p.read_text()
shutil.copy2(p,R/('test_local_control_contracts_before_lift_'+datetime.datetime.now().strftime('%H%M%S')+'.txt'))
def swap(a,b,count=1):
 global s
 assert s.count(a)==count,(a[:100],s.count(a));s=s.replace(a,b)
swap("import test_local_wave_arrival as arrival_tests","import test_local_wave_arrival as arrival_tests\nimport force_reference as lift")
swap("  self.srcsha=sha(self.src)","  self.srcsha=sha(self.src)\n  self.reference=dict(available=True,cl_offset=.01,buoyancy_N=38.556,reference_force_N=3855.6,lift_basis='vertical_force_minus_buoyancy')\n  self.reference_file=self.ww/'force_reference.json';m.write(self.reference_file,self.reference)\n  self.stack.enter_context(mock.patch.object(lift,'reference_for_source',return_value=self.reference))")
swap("v=dict(file=str(self.src),sha256=self.srcsha","v=dict(force_reference_file=str(self.reference_file),force_reference_sha256=sha(self.reference_file),file=str(self.src),sha256=self.srcsha")
swap("settling={'passed':True}","settling={'passed':True,'lift_basis':'vertical_force_minus_buoyancy'}")
swap("  v.update(change);p=folder/'settled_checkpoint.json';m.write(p,v)","  v.update(change);p=folder/'settled_checkpoint.json';m.write(p,v)")
insert="""
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
"""
swap("\nclass RecordingResult(unittest.TextTestResult):",insert+"\nclass RecordingResult(unittest.TextTestResult):")
ast.parse(s);p.write_text(s)
print('Lift contract tests added; no execution actions.')
