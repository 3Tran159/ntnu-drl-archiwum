import csv,math,tempfile,unittest,json,datetime
from pathlib import Path
from wave_cycle_repeatability import evaluate
class OriginTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)/'history.csv'
 def tearDown(self):self.tmp.cleanup()
 def data(self,end,origin=3.25,drift=False):
  with self.p.open('w',newline='') as f:
   w=csv.writer(f);w.writerow(['time_s','CD','CL_total'])
   for i in range(round(end*1000)+1):
    t=i/1000
    if t<origin:cd,cl=2+math.sin(17*t),-20+5*t
    else:
     phase=2*math.pi*(t-origin);cd=.01+.002*math.sin(phase);cl=.3+.05*math.sin(phase+.2)+(0.004*(t-origin) if drift else 0)
    w.writerow([t,cd,cl])
 def test_calm_and_ramp_not_counted(self):
  self.data(6.25);r=evaluate(self.p,1,4,20,analysis_origin_s=3.25)
  self.assertFalse(r['stop_for_repeatability']);self.assertEqual(r['complete_cycle_count_on_wave_clock'],3);self.assertEqual(r['earliest_review_time_s'],7.25)
 def test_four_arrived_cycles_can_pass_before_ten(self):
  self.data(7.25);r=evaluate(self.p,1,4,20,analysis_origin_s=3.25)
  self.assertTrue(r['stop_for_repeatability']);self.assertEqual(r['last_four_cycles'][0]['start_s'],3.25);self.assertEqual(r['last_four_cycles'][-1]['end_s'],7.25)
 def test_prearrival_cannot_hit_cap(self):
  self.data(21,origin=30);r=evaluate(self.p,1,4,20,analysis_origin_s=30)
  self.assertFalse(r['stop_recommended']);self.assertEqual(r['elapsed_wave_periods'],0)
 def test_cap_offset(self):
  self.data(23.25,drift=True);r=evaluate(self.p,1,4,20,analysis_origin_s=3.25)
  self.assertTrue(r['cap_reached']);self.assertEqual(r['review_cap_time_s'],23.25);self.assertFalse(r['accuracy_validated'])
 def test_invalid_origin(self):
  for value in [-1,float('nan'),float('inf')]:
   with self.assertRaises(ValueError):evaluate(self.p,1,4,20,analysis_origin_s=value)
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(OriginTests);res=unittest.TextTestRunner(verbosity=2).run(suite)
 Path(__file__).with_name('wave_cycle_origin_test_review.json').write_text(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),tests=res.testsRun,passed=res.wasSuccessful(),errors=len(res.errors),failures=len(res.failures),source='test_wave_cycle_origin.py'),indent=2))
 raise SystemExit(not res.wasSuccessful())
