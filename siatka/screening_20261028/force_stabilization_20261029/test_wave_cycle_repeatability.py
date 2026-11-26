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
 def reference(self,offset=.2):
  return dict(available=True,case="synthetic_case",mesh_sha256="a"*64,cl_offset=offset,buoyancy_N=offset*1000,reference_force_N=1000.,provenance_file="synthetic_reference.json",reason="Isolated constant reference")
 def test_historical_basis_is_explicit(self):
  r=evaluate(self.write(),T)
  self.assertEqual(r["coefficient_keys"],["CD","CL_total"]);self.assertEqual(r["CL_definition"],"historical_raw_CL_total")
  self.assertIn("Historical",r["force_basis"]);self.assertIsNone(r["force_reference"])
 def test_constant_offset_changes_mean_not_amplitude_or_phase(self):
  path=self.write();raw=evaluate(path,T);corrected=evaluate(path,T,force_reference=self.reference())
  self.assertEqual(corrected["coefficient_keys"],["CD","CL"]);self.assertNotIn("CL_total",corrected["comparisons"])
  self.assertEqual(corrected["CL_definition"],"buoyancy_subtracted");self.assertTrue(corrected["stop_for_repeatability"])
  for old,new in zip(raw["last_four_cycles"],corrected["last_four_cycles"]):
   a=old["coefficients"]["CL_total"];b=new["coefficients"]["CL"]
   self.assertAlmostEqual(a["mean"]-.2,b["mean"],places=12)
   for key in ("fundamental_amplitude","half_peak_to_peak","fluctuation_rms","fundamental_phase_deg"):self.assertAlmostEqual(a[key],b[key],places=11)
   self.assertEqual(old["coefficients"]["CD"],new["coefficients"]["CD"])
  self.assertNotAlmostEqual(raw["comparisons"]["CL_total"]["normalization"]["mean_scale"],corrected["comparisons"]["CL"]["normalization"]["mean_scale"],places=5)
 def test_offset_changes_mean_normalization_and_drift_percentage(self):
  path=self.write(kind="drift");raw=evaluate(path,T);corrected=evaluate(path,T,force_reference=self.reference(.3))
  a=raw["comparisons"]["CL_total"];b=corrected["comparisons"]["CL"]
  self.assertLess(b["normalization"]["mean_scale"],a["normalization"]["mean_scale"])
  self.assertGreater(b["worst_pair_metrics"]["mean_pct"],a["worst_pair_metrics"]["mean_pct"])
  self.assertAlmostEqual(a["worst_pair_metrics"]["phase_deg"],b["worst_pair_metrics"]["phase_deg"],places=10)
 def test_unavailable_reference_rejected_before_history_read(self):
  for ref in ({},{"available":False},{"available":1},[],{"available":True}):
   with self.subTest(ref=ref):
    with self.assertRaises(ValueError):evaluate(self.root/"missing.csv",T,force_reference=ref)
 def test_nonfinite_reference_rejected(self):
  for key in ("cl_offset","buoyancy_N","reference_force_N"):
   for value in (float("nan"),float("inf"),-float("inf"),None,"not_numeric",True,False):
    ref=self.reference();ref[key]=value
    with self.subTest(key=key,value=value):
     with self.assertRaises(ValueError):evaluate(self.root/"missing.csv",T,force_reference=ref)
 def test_reference_force_must_be_positive_and_offset_consistent(self):
  for updates in ({"reference_force_N":0},{"reference_force_N":-1},{"cl_offset":.12345}):
   with self.subTest(updates=updates):
    with self.assertRaises(ValueError):evaluate(self.root/"missing.csv",T,force_reference={**self.reference(),**updates})
 def test_histories_and_reference_remain_immutable(self):
  import copy,hashlib
  path=self.write();before=hashlib.sha256(path.read_bytes()).hexdigest();ref=self.reference();original=copy.deepcopy(ref)
  evaluate(path,T,force_reference=ref)
  self.assertEqual(before,hashlib.sha256(path.read_bytes()).hexdigest());self.assertEqual(ref,original)
 def test_unavailable_row_correction_never_falls_back_to_raw_lift(self):
  from unittest.mock import patch
  path=self.write()
  with patch("force_reference.correct_row",return_value={"CD":.01,"CL_total":.3,"CL":None,"cl_correction_available":False}):
   r=evaluate(path,T,force_reference=self.reference())
  self.assertFalse(r["stop_for_repeatability"]);self.assertFalse(r["latest_four_complete"]);self.assertTrue(r["invalid_force_rows"]);self.assertEqual(r["comparisons"],{})
 def test_nonfinite_corrected_lift_blocks_cycle(self):
  from unittest.mock import patch
  with patch("force_reference.correct_row",return_value={"CD":.01,"CL":float("inf"),"cl_correction_available":True}):
   r=evaluate(self.write(),T,force_reference=self.reference())
  self.assertFalse(r["stop_for_repeatability"]);self.assertTrue(r["invalid_force_rows"]);json.dumps(r,allow_nan=False)
 def test_corrected_analysis_origin_excludes_prior_calm(self):
  path=self.write(cycles=6)
  rows=list(csv.reader(path.read_text().splitlines()))
  for row in rows[1:]:
   if float(row[0])<2*T-1e-10:row[1]="99999";row[2]="88888"
  with path.open("w",newline="") as stream:csv.writer(stream).writerows(rows)
  r=evaluate(path,T,min_cycles=4,analysis_origin_s=2*T,force_reference=self.reference())
  self.assertTrue(r["stop_for_repeatability"]);self.assertEqual(r["valid_complete_cycles"],[1,2,3,4])
  self.assertAlmostEqual(r["last_four_cycles"][0]["coefficients"]["CL"]["mean"],.1,places=11)
 def test_corrected_near_zero_mean_still_has_finite_metrics(self):
  r=evaluate(self.write(),T,force_reference=self.reference(.3));self.assertTrue(r["stop_for_repeatability"])
  self.assertAlmostEqual(r["last_four_cycles"][-1]["coefficients"]["CL"]["mean"],0,places=12);json.dumps(r,allow_nan=False)
 def test_corrected_conflicting_overlap_blocks_repeatability(self):
  r=evaluate([self.write("old.csv"),self.write("new.csv",kind="drift")],T,force_reference=self.reference())
  self.assertFalse(r["history_quality_pass"]);self.assertFalse(r["stop_for_repeatability"])
  self.assertIn("CL",r["duplicate_conflicts"][0]["new"]);self.assertNotIn("CL_total",r["duplicate_conflicts"][0]["new"])
if __name__=="__main__":
 import datetime,hashlib,io
 root=Path(__file__).resolve().parent
 names=("wave_cycle_repeatability.py","force_reference.py","test_wave_cycle_repeatability.py")
 hashes=lambda:{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}
 before=hashes();stream=io.StringIO()
 result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RepeatabilityTests))
 output=stream.getvalue();print(output,end="")
 report=dict(updated_at=datetime.datetime.now().astimezone().isoformat(),scope="Temporary synthetic force histories and actual correction adapter; no CFD/API launches or production-history edits",tests_run=result.testsRun,failures=[dict(test=str(t),traceback=v) for t,v in result.failures],errors=[dict(test=str(t),traceback=v) for t,v in result.errors],passed=result.wasSuccessful(),source_sha256=before,sources_unchanged=before==hashes(),test_names=unittest.defaultTestLoader.getTestCaseNames(RepeatabilityTests))
 report["passed"]=report["passed"] and report["sources_unchanged"]
 (root/"wave_cycle_repeatability_force_reference_test_review.json").write_text(json.dumps(report,indent=2),encoding="utf8")
 (root/"wave_cycle_repeatability_force_reference_test_output.txt").write_text(output,encoding="utf8")
 raise SystemExit(0 if report["passed"] else 1)
