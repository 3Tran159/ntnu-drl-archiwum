"""Meaningful synthetic checks; temporary histories only, no production data edits."""
import csv,json,math,tempfile,unittest
from pathlib import Path
from wave_cycle_repeatability import evaluate
T=0.8472673206891129
class RepeatabilityTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def write(self,name="history.csv",cycles=10,start=0,gap=None,kind="stable"):
  path=self.root/name
  with path.open("w",newline="") as f:
   w=csv.writer(f);w.writerow(["time_s","CD","CL_total"])
   for i in range(round(cycles*512)+1):
    n=i/512;t=n*T
    if n<start or gap and gap[0]<n<gap[1]:continue
    theta=2*math.pi*n*(1.01 if kind=="phase" else 1)
    cd=.01+.002*math.cos(theta)+.0002*math.sin(2*theta)
    cl=.3+.1*math.sin(theta)-.005*math.cos(3*theta)
    if kind=="drift":cd+=.0002*n;cl+=.005*n
    if kind=="nearzero":cd=1e-10*math.cos(theta);cl=0
    w.writerow([t,cd,cl])
  return path
 def test_stable_sine_with_harmonics(self):
  r=evaluate([self.write()],T)
  self.assertTrue(r["stop_for_repeatability"]);self.assertEqual(r["last_four_cycles"][0]["cycle"],7)
  self.assertFalse(r["accuracy_validated"]);self.assertEqual(len(r["comparisons"]["CD"]["pairs"]),6)
 def test_mean_drift_rejected(self):
  r=evaluate([self.write(kind="drift")],T)
  self.assertFalse(r["stop_for_repeatability"]);self.assertGreater(r["comparisons"]["CD"]["worst_pair_metrics"]["mean_pct"],.5)
 def test_phase_drift_rejected_without_realigning(self):
  r=evaluate([self.write(kind="phase")],T)
  self.assertFalse(r["stop_for_repeatability"]);self.assertGreater(r["comparisons"]["CL_total"]["worst_pair_metrics"]["phase_deg"],2)
 def test_near_zero_finite_and_phase_not_applicable(self):
  r=evaluate([self.write(kind="nearzero")],T)
  self.assertTrue(r["stop_for_repeatability"]);self.assertFalse(r["comparisons"]["CD"]["phase_applicable"])
  self.assertIsNone(r["comparisons"]["CL_total"]["worst_pair_metrics"]["phase_deg"])
  json.dumps(r,allow_nan=False)
 def test_incomplete_first_cycle_excluded(self):
  r=evaluate([self.write(start=.2)],T)
  self.assertNotIn(1,r["valid_complete_cycles"]);self.assertEqual(r["excluded_cycles"][0]["cycle"],1)
  self.assertTrue(r["stop_for_repeatability"])
 def test_missing_interval_in_recent_cycle_rejected(self):
  r=evaluate([self.write(gap=(8.3,8.7))],T)
  self.assertFalse(r["latest_four_complete"]);self.assertFalse(r["stop_for_repeatability"])
 def test_no_early_stop_before_ten_periods(self):
  r=evaluate([self.write(cycles=9.5)],T)
  self.assertFalse(r["minimum_elapsed"]);self.assertFalse(r["stop_recommended"])
 def test_twenty_cycle_cap_is_review_not_failure_proof(self):
  r=evaluate([self.write(cycles=20,kind="drift")],T)
  self.assertTrue(r["cap_reached"]);self.assertTrue(r["stop_recommended"])
  self.assertFalse(r["stop_for_repeatability"]);self.assertEqual(r["status"],"cycle_cap_reached_review_required")
 def test_verified_continuation_overlap(self):
  original=self.write("old.csv",cycles=5.2,start=.2)
  continued=self.write("new.csv",cycles=10,start=5.2)
  r=evaluate([original,continued],T)
  self.assertTrue(r["stop_for_repeatability"]);self.assertEqual(r["duplicate_conflicts"],[])
 def test_conflicting_overlap_blocks_repeatability(self):
  old=self.write("old.csv");new=self.write("new.csv",kind="drift")
  r=evaluate([old,new],T)
  self.assertFalse(r["history_quality_pass"]);self.assertFalse(r["stop_for_repeatability"])
 def test_nonfinite_recent_force_sample_rejected(self):
  path=self.write();text=path.read_text();rows=list(csv.reader(text.splitlines()))
  rows[round(8.4*512)+1][1]="NaN"
  with path.open("w",newline="") as f:csv.writer(f).writerows(rows)
  r=evaluate([path],T);self.assertFalse(r["latest_four_complete"]);self.assertFalse(r["stop_for_repeatability"])
 def test_missing_file_not_treated_as_clean_history(self):
  r=evaluate([self.write(),self.root/"missing.csv"],T)
  self.assertFalse(r["history_quality_pass"]);self.assertFalse(r["stop_for_repeatability"])
if __name__=="__main__":unittest.main(verbosity=2)
