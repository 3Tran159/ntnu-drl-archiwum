"""Synthetic policy tests only. No STAR, GPU, queue, source-case or production JSON changes."""
import csv,math,tempfile,unittest
from pathlib import Path
from local_wave_arrival import assess
T=.8472673206891129
H=.5
ACT=123.456
class ArrivalTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix="ntnu_arrival_test_");self.folder=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def write(self,end=7.02,start=0,offset=0,amp=.25,mean_drift=0,amp_growth=0,phase_growth=0,
           frequency=1,gap=None,nan_at=None,stations=(-1.,2.5),dt=None):
  dt=T/100 if dt is None else dt
  with (self.folder/"gauges.csv").open("w",newline="") as f:
   writer=csv.writer(f);writer.writerow(["time_s","x_m","eta_actual_m","eta_analytic_m"])
   j=0
   while (rel:=start*T+offset+j*dt)<=end*T+1e-10:
    k=math.floor(rel/T+1e-9);phase=2*math.pi*rel/T
    if gap is not None and gap[0]*T<rel<gap[1]*T:
     j+=1;continue
    for x in stations:
     spatial=.12*x;reference=.25*math.sin(phase+spatial)
     actual=amp*(1+amp_growth*k)*math.sin(phase*frequency+spatial+math.radians(phase_growth*k))+mean_drift*k+.013
     if nan_at is not None and abs(rel-nan_at*T)<dt/2:actual=float("nan")
     writer.writerow([ACT+rel,x,actual,reference])
    j+=1
 def check(self):return assess(self.folder,ACT,T,H,20,-35)
 def test_stable_sine_establishes_at_end_earliest_three(self):
  self.write();r=self.check();self.assertTrue(r["established"],r)
  self.assertEqual(r["evidence"]["qualifying_cycle_indices"],[4,5,6])
  self.assertAlmostEqual(r["analysis_origin_s"],ACT+7*T)
  self.assertFalse(r["accuracy_admitted"])
 def test_flat_calm_cannot_pass(self):
  self.write(amp=0);self.assertFalse(self.check()["established"])
 def test_weak_signal_cannot_pass(self):
  self.write(amp=.04);self.assertFalse(self.check()["established"])
 def test_mean_drift_fails(self):
  self.write(mean_drift=.012);self.assertFalse(self.check()["established"])
 def test_allpairs_amplitude_catches_small_accumulating_drift(self):
  self.write(amp_growth=.04);r=self.check();self.assertFalse(r["established"])
  metrics=r["evidence"]["latest_failure"]["stations"]["-1.0"]["pair_metrics"]
  self.assertTrue(metrics[0]["passed"]);self.assertFalse(metrics[1]["passed"])
 def test_allpairs_phase_catches_three_degree_per_cycle(self):
  self.write(phase_growth=3);self.assertFalse(self.check()["established"])
 def test_wrong_period_fails(self):
  self.write(frequency=1.07);self.assertFalse(self.check()["established"])
 def test_internal_gap_fails(self):
  self.write(gap=(4.7,4.8));self.assertFalse(self.check()["established"])
 def test_nonfinite_sample_fails(self):
  self.write(nan_at=5.1);self.assertFalse(self.check()["established"])
 def test_missing_station_fails(self):
  self.write(stations=(-1.,));r=self.check();self.assertFalse(r["established"])
  self.assertIn("missing",r["reason"])
 def test_noninteger_endpoints_use_bracketing_interpolation(self):
  self.write(offset=.003*T);r=self.check();self.assertTrue(r["established"],r)
  self.assertAlmostEqual(r["analysis_origin_s"],ACT+7*T)
 def test_incomplete_third_cycle_waits(self):
  self.write(end=6.99);r=self.check();self.assertFalse(r["established"])
  self.assertIn("Awaiting",r["reason"])
 def test_late_start_skips_uncovered_first_cycle(self):
  self.write(start=4.1,end=8.02);r=self.check();self.assertTrue(r["established"],r)
  self.assertEqual(r["evidence"]["qualifying_cycle_indices"],[5,6,7])
  self.assertAlmostEqual(r["analysis_origin_s"],ACT+8*T)
 def test_origin_does_not_slide_when_more_data_arrive(self):
  self.write(end=7.02);a=self.check();self.write(end=10.02);b=self.check()
  self.assertTrue(a["established"] and b["established"])
  self.assertEqual(a["analysis_origin_s"],b["analysis_origin_s"])
 def test_coarse_gauges_fail(self):
  self.write(dt=T/32);r=self.check();self.assertFalse(r["established"])
  self.assertIn("coarse",r["reason"])
 def test_bad_period_fails(self):
  self.write();self.assertFalse(assess(self.folder,ACT,float("nan"),H,20,-35)["established"])
 def test_missing_csv_fails_closed(self):
  self.assertFalse(self.check()["established"])
if __name__=="__main__":unittest.main(verbosity=2)
