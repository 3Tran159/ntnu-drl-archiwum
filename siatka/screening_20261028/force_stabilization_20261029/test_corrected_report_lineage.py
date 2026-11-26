"""Bounded report/UI numerical contracts. Temp fixtures plus read-only C01 sample audit."""
from pathlib import Path
import contextlib,csv,datetime,hashlib,io,json,math,os,subprocess,tempfile,unittest
from unittest.mock import patch
R=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v),encoding="utf8")
def blocked(*a,**k):raise AssertionError("External process action forbidden")
class ReportTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix="ntnu_report_qa_");self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name);self.root=self.base/"reviews";self.root.mkdir();self.w=self.base/"waves";self.w.mkdir()
  self.parent=self.w/"LOCAL_parent_wave";self.parent.mkdir();self.case=self.w/"LOCAL_resumed_wave";self.case.mkdir()
  self.old=self.parent/"history.csv";self.current=self.case/"history.csv";self.history(self.old,0,2);self.history(self.current,2,4)
  self.identity=dict(source=str(self.parent/"final.sim"),source_sha256="a"*64,input_sha256="a"*64,source_time_s=2.,source_is_guard_failed=False,reinitialized=False,resume_wave=True,continuation_mode="wave",history_files=[str(self.old)],history_sha256={str(self.old):digest(self.old)},activation_time_s=0.,height_m=.5,wavelength_m=20.)
  save(self.case/"source_identity.json",self.identity);save(self.case/"setup.json",dict(dt_s=.001));save(self.case/"request.json",dict(mode="wave",spec=dict(dt_s=.001,height_m=.5,wavelength_m=20.)))
  save(self.case/"wave_activation.json",dict(case=self.case.name,height_m=.5,target_height_m=.5,wavelength_m=20.,activation_time_s=0.,wave_period_s=1.,analysis_origin_s=0.,time_s=4.))
  save(self.case/"controller_result.json",dict(source_unchanged=True))
  self.state=dict(case=self.case.name,directory=str(self.case),status="running",computation_active=True,computation_stage="inlet_wave_full_amplitude",progress=dict(time_s=4.))
  self.ref=dict(available=True,case=str(self.case),mesh_sha256="b"*64,cl_offset=.1,buoyancy_N=100.,reference_force_N=1000.,provenance_file=str(self.root/"reference.json"),reason="Isolated audited reference")
  self.stack=contextlib.ExitStack();self.addCleanup(self.stack.close)
  self.stack.enter_context(patch.object(report,"R",self.root));self.stack.enter_context(patch.object(wave,"ROOT",self.root))
  self.stack.enter_context(patch.object(force,"correction_for_case",lambda folder:dict(self.ref)))
  original=live.history_sources
  self.stack.enter_context(patch.object(live,"history_sources",lambda state,folder,wave_root=None:original(state,folder,wave_root=self.w)))
 def history(self,path,start,end,rawmean=.4):
  with Path(path).open("w",newline="",encoding="utf8") as stream:
   writer=csv.writer(stream);writer.writerow(("time_s","CD","CL_total","Fz_slice_N"))
   for i in range(round(start*1000),round(end*1000)+1):
    t=i/1000;raw=rawmean+.1*math.sin(2*math.pi*t)
    writer.writerow((t,.01+.002*math.cos(2*math.pi*t),raw,raw*1000))
 def data(self):return report.dataset(self.case,state=self.state)
 def test_verified_resumed_report_merges_only_bound_lineage(self):
  data=self.data();self.assertEqual(data["history_rows"],4001);self.assertEqual(data["t_start"],0);self.assertEqual(data["t_last"],4)
  self.assertTrue(data["assessment"]["screen_pass"]);self.assertEqual(set(data["assessment"]["comparisons"]),{"CD","CL"})
  self.assertAlmostEqual(data["series"]["CL"][-1][1],.3,places=12);self.assertAlmostEqual(data["series"]["CL_total"][-1][1],.4,places=12)
 def test_new_wave_never_inherits_calm_baseline(self):
  self.history(self.old,0,2,rawmean=9.)
  self.identity.update(resume_wave=False,continuation_mode=None,source_calm_settled=True,history_sha256={str(self.old):digest(self.old)});save(self.case/"source_identity.json",self.identity)
  data=self.data();self.assertEqual(data["t_start"],2);self.assertEqual(data["history_rows"],2001);self.assertFalse(data["assessment"]["screen_pass"])
  self.assertLess(max(p[1] for p in data["series"]["CL"] if p[1] is not None),1)
 def test_bad_lineage_hash_cannot_claim_repeatability(self):
  self.history(self.current,0,4);self.identity["history_sha256"][str(self.old)]="0"*64;save(self.case/"source_identity.json",self.identity)
  data=self.data();self.assertFalse(data["assessment"]["screen_pass"]);self.assertNotIn("passed",data["cohort"].lower())
 def test_source_input_mismatch_cannot_claim_repeatability(self):
  self.history(self.current,0,4);self.identity["input_sha256"]="f"*64;save(self.case/"source_identity.json",self.identity)
  self.assertFalse(self.data()["assessment"]["screen_pass"])
 def test_unavailable_reference_clears_saved_corrected_success(self):
  self.ref.update(available=False,cl_offset=None,buoyancy_N=None,reference_force_N=None)
  save(self.case/"cycle_assessment.json",dict(case=self.case.name,CL_definition="buoyancy_subtracted",period_s=1.,wave_clock_origin_s=0.,stop_for_repeatability=True,history_sources=[dict(path=str(self.current))],comparisons=dict(CL=dict(**{"pass":True}))))
  data=self.data();self.assertFalse(data["assessment"]["screen_pass"]);self.assertTrue(all(p[1] is None for p in data["series"]["CL"]));self.assertNotIn("passed",data["cohort"].lower())
 def test_nonfinite_reference_cannot_claim_success(self):
  self.ref["cl_offset"]=float("nan")
  # Deliberately forged adapter output; evaluator refuses it before any success result.
  with self.assertRaises(ValueError):self.data()
 def test_report_and_ui_do_not_double_correct(self):
  data=self.data();points,_=wave._case_history(self.state,self.case)
  self.assertAlmostEqual(points[-1][2],.3,places=12);self.assertAlmostEqual(data["series"]["CL"][-1][1],points[-1][2],places=12)
  row=dict(CD=.01,CL_total=.4,Fz_slice_N=400.)
  once=force.correct_row(row,self.ref);twice=force.correct_row(once,self.ref)
  self.assertAlmostEqual(once["CL"],twice["CL"],places=14);self.assertEqual(row,dict(CD=.01,CL_total=.4,Fz_slice_N=400.))
 def test_report_and_ui_leave_both_histories_unchanged(self):
  before=[digest(self.old),digest(self.current)]
  self.data();wave._case_history(self.state,self.case)
  self.assertEqual(before,[digest(self.old),digest(self.current)])
 def test_invalid_source_never_gets_accepted_calm_cohort(self):
  self.state["computation_stage"]="calm_settling";(self.case/"C01_settled.sim").write_bytes(b"unverified fixture")
  save(self.case/"settled_checkpoint.json",dict(status="calm_force_settled",source_unchanged=True,settling=dict(passed=True),file=str(self.case/"C01_settled.sim")))
  self.identity["input_sha256"]="0"*64;save(self.case/"source_identity.json",self.identity)
  self.assertNotEqual(self.data()["cohort"],"Accepted calm reference")
def real_sample():
 folder=Path("E:/ntnu/quasi2d_waves_20261029/C01_W20L4_M10_calm_settle_r2");path=folder/"history.csv";before=digest(path)
 with path.open(encoding="utf-8-sig",newline="") as f:raw=list(csv.DictReader(f))[-1]
 ref=force.correction_for_case(folder);corrected=force.correct_row(raw,ref);again=force.correct_row(corrected,ref)
 state=dict(case=folder.name,directory=str(folder),computation_stage="calm_settling",computation_active=False,status="needs_review")
 data=report.dataset(folder,state=state);points,_=wave._case_history(state,folder)
 expected=.31158453154447896
 assert ref["available"] is True
 assert abs(float(raw["CL_total"])-.3174766587847341)<1e-13
 assert abs(ref["cl_offset"]-.005892127240255106)<1e-15
 assert abs(corrected["CL"]-expected)<1e-13 and abs(again["CL"]-expected)<1e-13
 assert abs(points[-1][2]-expected)<1e-13 and abs(data["series"]["CL"][-1][1]-expected)<1e-13
 assert digest(path)==before
 assert data["assessment"]["screen_pass"] is False and data["cohort"]=="Failed / diagnostic"
 return dict(case=folder.name,time_s=float(raw["time_s"]),rawCL_total=float(raw["CL_total"]),offset=ref["cl_offset"],CL=corrected["CL"],ui_CL=points[-1][2],report_CL=data["series"]["CL"][-1][1],raw_csv_sha256=before,raw_csv_unchanged=True,cohort=data["cohort"],source="Read-only actual terminal C01 sample")
def main():
 global report,wave,force,live
 names=["build_local_control_report.py","wave_cycle_dashboard_panel.py","live_analysis_panel.py","force_reference.py","wave_cycle_repeatability.py"]
 before={name:digest(R/name) for name in names}
 with contextlib.ExitStack() as stack:
  for name in ("Popen","run","call","check_call","check_output"):stack.enter_context(patch.object(subprocess,name,blocked))
  if hasattr(os,"startfile"):stack.enter_context(patch.object(os,"startfile",blocked))
  import build_local_control_report as report,wave_cycle_dashboard_panel as wave,force_reference as force,live_analysis_panel as live
  stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReportTests))
  actual=None;actual_error=None
  try:actual=real_sample()
  except Exception as ex:actual_error=type(ex).__name__+": "+str(ex)
 output=stream.getvalue();print(output,end="")
 after={name:digest(R/name) for name in names}
 receipt=dict(updated_at=datetime.datetime.now().astimezone().isoformat(),scope="Temp report/UI lineage fixtures plus read-only real C01 history; no CFD/API/process actions",tests_run=result.testsRun,failures=[dict(test=str(t),traceback=v) for t,v in result.failures],errors=[dict(test=str(t),traceback=v) for t,v in result.errors],real_sample=actual,real_sample_error=actual_error,source_sha256=before,sources_unchanged=before==after,passed=result.wasSuccessful() and not actual_error and before==after)
 save(R/"corrected_report_lineage_test_review.json",receipt);(R/"corrected_report_lineage_test_output.txt").write_text(output,encoding="utf8")
 print(json.dumps(dict(passed=receipt["passed"],real_sample=actual,real_sample_error=actual_error)));raise SystemExit(0 if receipt["passed"] else 1)
if __name__=="__main__":main()
