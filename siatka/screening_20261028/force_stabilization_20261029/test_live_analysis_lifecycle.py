"""Isolated live/archive lifecycle regression tests. No CFD, HTTP or process actions."""
from pathlib import Path
import contextlib,datetime,hashlib,importlib,json,os,subprocess,sys,tempfile,unittest
from unittest.mock import patch
R=Path(__file__).resolve().parent
OUT=R/"live_analysis_lifecycle_qa"
def blocked(*a,**k):raise AssertionError("External action forbidden in isolated UI test")
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v),encoding="utf8")
class LifecycleTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix="ntnu_live_qa_");self.addCleanup(self.tmp.cleanup)
  self.base=Path(self.tmp.name);self.root=self.base/"review";self.root.mkdir();self.w=self.base/"waves";self.w.mkdir()
  self.case=self.w/"LOCAL_mock_wave";self.case.mkdir()
  self.state=dict(case=self.case.name,directory=str(self.case),status="running",computation_active=True,computation_stage="inlet_wave_full_amplitude",controller_pid=123456,updated_at=datetime.datetime.now().astimezone().isoformat(),progress=dict(time_s=4.2))
  self.old=self.w/"LOCAL_parent_wave";self.old.mkdir();self.history=self.old/"history.csv"
  self.history.write_text("time_s,CD,CL_total\n2.0,0.1,0.2\n",encoding="utf8")
  (self.case/"history.csv").write_text("time_s,CD,CL_total\n4.2,0.3,0.4\n",encoding="utf8")
  self.identity=dict(source=str(self.old/"final.sim"),source_sha256="a"*64,input_sha256="a"*64,source_time_s=4.0,source_is_guard_failed=False,reinitialized=False,resume_wave=True,continuation_mode="wave",history_files=[str(self.history)],history_sha256={str(self.history):digest(self.history)},activation_time_s=1.0)
  save(self.case/"source_identity.json",self.identity)
 def paths(self):
  sources,warnings=module.history_sources(self.state,self.case,wave_root=self.w)
  return [str(Path(x["path"]).resolve()) for x in sources],warnings
 def assert_old_rejected(self):
  paths,warnings=self.paths();self.assertNotIn(str(self.history.resolve()),paths);self.assertTrue(warnings)
 def test_active_running(self):self.assertTrue(module.is_active(self.state,root=self.root))
 def test_explicit_inactive(self):
  self.state["computation_active"]=False;self.assertFalse(module.is_active(self.state,root=self.root))
 def test_disk_completed_overrides_stale_running(self):
  for status in ("stability_guard","target_reached","user_stop","calm_settled","repeatability_passed"):
   with self.subTest(status=status):
    save(self.case/"completed.json",dict(status=status,time_s=4.2));self.assertFalse(module.is_active(self.state,root=self.root))
 def test_nested_completed_overrides_stale_running(self):
  self.state["result"]=dict(completed=dict(status="stability_guard",time_s=4.2));self.assertFalse(module.is_active(self.state,root=self.root))
 def test_terminal_state_overrides_active_flag(self):
  for status in ("needs_review","physical_guard_failed_saved","paused","completed","cancelled","saved_server_open"):
   with self.subTest(status=status):
    self.state["status"]=status;self.assertFalse(module.is_active(self.state,root=self.root))
 def test_guard_progress_overrides_stale_running(self):
  self.state["progress"]=dict(status="stability_guard",time_s=4.2);self.assertFalse(module.is_active(self.state,root=self.root))
 def test_failed_source_lineage_rejected(self):
  self.identity["source_is_guard_failed"]=True;save(self.case/"source_identity.json",self.identity);self.assert_old_rejected()
 def test_wrong_case_side_image_rejected(self):
  import wave_cycle_dashboard_panel as wave
  image=self.root/"old.svg";image.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>',encoding="utf8")
  save(self.root/"wave_side_view_current.json",dict(case="OLD_OTHER_CASE",field_time_s=4.2,image_path=str(image),provenance="Actual historical field"))
  with patch.object(wave,"ROOT",self.root):self.assertEqual(wave._side_view(self.state),"")
 def test_wrong_case_vorticity_rejected(self):
  import wave_cycle_dashboard_panel as wave
  image=self.root/"old.png";image.write_bytes(b"historical native field")
  save(self.root/"wave_vorticity_current.json",dict(case="OLD_OTHER_CASE",field_time_s=4.2,image_path=str(image),provenance_path=str(self.root/"old_provenance.json")))
  with patch.object(wave,"ROOT",self.root):self.assertEqual(wave._vorticity_view(self.state),"")
 def test_stale_computer_activity_does_not_activate(self):
  self.state["computation_active"]=False
  save(self.root/"computer_status.json",dict(activity=dict(state="running",case="OLD_W01",metrics=dict(CL_total=99999.1234))))
  self.assertFalse(module.is_active(self.state,root=self.root))
 def test_verified_wave_history_kept(self):
  paths,warnings=self.paths();self.assertIn(str(self.history.resolve()),paths);self.assertIn(str((self.case/"history.csv").resolve()),paths);self.assertFalse(warnings)
 def test_new_wave_does_not_inherit_calm_history(self):
  self.identity.update(resume_wave=False,continuation_mode=None,source_calm_settled=True);save(self.case/"source_identity.json",self.identity);self.assert_old_rejected()
 def test_resume_mode_mismatch_rejected(self):
  self.identity["continuation_mode"]="calm";save(self.case/"source_identity.json",self.identity);self.assert_old_rejected()
 def test_wrong_history_sha_rejected(self):
  self.identity["history_sha256"][str(self.history)]="0"*64;save(self.case/"source_identity.json",self.identity);self.assert_old_rejected()
 def test_missing_history_sha_rejected(self):
  self.identity["history_sha256"]={};save(self.case/"source_identity.json",self.identity);self.assert_old_rejected()
 def test_source_input_identity_mismatch_rejected(self):
  self.identity["input_sha256"]="b"*64;save(self.case/"source_identity.json",self.identity);self.assert_old_rejected()
 def test_missing_source_identity_rejected(self):
  self.identity.pop("source_sha256");save(self.case/"source_identity.json",self.identity);self.assert_old_rejected()
 def test_modified_history_rejected(self):
  self.history.write_text("time_s,CD,CL_total\n2.0,999,999\n",encoding="utf8");self.assert_old_rejected()
 def test_missing_history_rejected(self):
  self.history.unlink();self.assert_old_rejected()
 def test_outside_root_history_rejected(self):
  outside=self.base/"outside.csv";outside.write_text("time_s,CD,CL_total\n2,3,4\n",encoding="utf8")
  self.identity.update(history_files=[str(outside)],history_sha256={str(outside):digest(outside)})
  save(self.case/"source_identity.json",self.identity);paths,warnings=self.paths();self.assertNotIn(str(outside.resolve()),paths);self.assertTrue(warnings)
 def test_resolved_traversal_history_rejected(self):
  outside=self.base/"outside.csv";outside.write_text("time_s,CD,CL_total\n2,3,4\n",encoding="utf8")
  raw=str(self.w/".."/"outside.csv");self.identity.update(history_files=[raw],history_sha256={raw:digest(outside)})
  save(self.case/"source_identity.json",self.identity);paths,warnings=self.paths();self.assertNotIn(str(outside.resolve()),paths);self.assertTrue(warnings)
 def test_idle_live_has_no_archived_values(self):
  self.state.update(status="needs_review",computation_active=False,result=dict(completed=dict(status="stability_guard",time_s=4.2)))
  live,archive=module.panels(self.state,'<div>UNIQUE_ARCHIVED_CD_9876.543<img src="old-case.png"><script class="wcp-history-data">old</script></div>',"<div>UNIQUE_FAILURE_DIAGNOSTIC</div>","<div>UNIQUE_ARCHIVED_FILE</div>",root=self.root,destinations=[self.base/"published"])
  for sentinel in ("9876.543","old-case.png","wcp-history-data","UNIQUE_FAILURE_DIAGNOSTIC","UNIQUE_ARCHIVED_FILE"):
   self.assertNotIn(sentinel,live)
  self.assertIn("Live analysis",live)
 def make_window_history(self,dt,alter=None,value=None):
  import csv
  save(self.case/"setup.json",dict(dt_s=dt))
  with (self.case/"history.csv").open("w",newline="",encoding="utf8") as stream:
   writer=csv.writer(stream);writer.writerow(("time_s","CD","CL_total"))
   for i in range(round(.4/dt)+1):
    t=round(i*dt,9)
    if alter:
     t=alter(i,t)
     if t is None:continue
    cd=(1.0 if t<=.2 else 1.004) if value is None else value
    writer.writerow((t,cd,.2))
 def test_window_point1ms_count_and_latest_denominator(self):
  import wave_cycle_dashboard_panel as wave
  self.make_window_history(.0001)
  data=wave._window_delta_data(self.case);last=data["latest"]["CD_window_pct"]
  self.assertEqual(data["minimum_samples"],1999);self.assertIsNotNone(last)
  self.assertAlmostEqual(last["value_pct"],100*(1.004-1)/1.004,places=7)
 def test_window_1ms_count_and_latest_denominator(self):
  import wave_cycle_dashboard_panel as wave
  self.make_window_history(.001)
  data=wave._window_delta_data(self.case);self.assertEqual(data["minimum_samples"],199);self.assertAlmostEqual(data["latest"]["CD_window_pct"]["value_pct"],100*(1.004-1)/1.004,places=7)
 def test_window_missing_step_is_unavailable(self):
  import wave_cycle_dashboard_panel as wave
  self.make_window_history(.0001,alter=lambda i,t:None if i==3000 else t)
  self.assertIsNone(wave._window_delta_data(self.case)["latest"]["CD_window_pct"])
 def test_window_fractional_gap_matches_controller(self):
  import wave_cycle_dashboard_panel as wave
  self.make_window_history(.001,alter=lambda i,t:t+.0002 if i==300 else t)
  self.assertIsNone(wave._window_delta_data(self.case)["latest"]["CD_window_pct"])
 def test_window_missing_dt_is_unavailable(self):
  import wave_cycle_dashboard_panel as wave
  self.make_window_history(.001);(self.case/"setup.json").unlink()
  data=wave._window_delta_data(self.case);self.assertIsNone(data["dt_s"]);self.assertIsNone(data["latest"]["CD_window_pct"])
 def test_window_near_zero_denominator_unavailable(self):
  import wave_cycle_dashboard_panel as wave
  self.make_window_history(.001,value=1e-14);self.assertIsNone(wave._window_delta_data(self.case)["latest"]["CD_window_pct"])
 def test_active_live_case_present(self):
  live,archive=module.panels(self.state,"<div>CURRENT_MATCHED_CURVES</div>","","",root=self.root,destinations=[self.base/"published"])
  self.assertIn("CURRENT_MATCHED_CURVES",live)
 def test_completion_archives_and_clears_live(self):
  destinations=[self.base/"published"]
  live,archive=module.panels(self.state,"<div>FIRST_RUN_CURVES</div>","","",root=self.root,destinations=destinations)
  self.assertIn("FIRST_RUN_CURVES",live);self.assertNotIn("<b>"+self.case.name+"</b>",archive)
  save(self.case/"completed.json",dict(status="target_reached",time_s=4.2))
  live,archive=module.panels(self.state,"<div>FINAL_RUN_CURVES</div>","","",root=self.root,destinations=destinations)
  self.assertNotIn("FINAL_RUN_CURVES",live);self.assertIn(self.case.name,archive)
  snapshot=(destinations[0]/"archive_runs"/(self.case.name+".html")).read_text(encoding="utf8")
  self.assertIn("FINAL_RUN_CURVES",snapshot)
 def test_next_case_live_excludes_previous_archive(self):
  destinations=[self.base/"published"];self.state.update(status="completed",computation_active=False)
  module.panels(self.state,"<div>OLD_CASE_SENTINEL_8888</div>","","",root=self.root,destinations=destinations)
  nextcase=self.w/"LOCAL_next_wave";nextcase.mkdir();new=dict(self.state,case=nextcase.name,directory=str(nextcase),status="running",computation_active=True)
  live,archive=module.panels(new,"<div>NEW_CASE_MATCHED_DATA</div>","","",root=self.root,destinations=destinations)
  self.assertIn("NEW_CASE_MATCHED_DATA",live);self.assertNotIn("OLD_CASE_SENTINEL_8888",live);self.assertIn(self.case.name,archive)
 def test_archive_does_not_poll_current_status(self):
  import wave_arrival_dashboard_panel as arrival
  self.state.update(status="completed",computation_active=False)
  body='<section>SAVED_ARRIVAL_NUMBERS</section>'+arrival.SCRIPT+'<script type="application/json" class="wcp-history-data">{"case":"saved","series":{}}</script>'
  destinations=[self.base/"published"];module.panels(self.state,body,"","",root=self.root,destinations=destinations)
  snapshot=(destinations[0]/"archive_runs"/(self.case.name+".html")).read_text(encoding="utf8")
  self.assertIn("SAVED_ARRIVAL_NUMBERS",snapshot);self.assertIn("wcp-history-data",snapshot);self.assertNotIn("/api/status",snapshot)
 def test_archive_is_closed(self):
  self.state.update(status="completed",computation_active=False)
  live,archive=module.panels(self.state,"<div>ARCHIVE_CURVES</div>","DIAGNOSTICS","FILES",root=self.root,destinations=[self.base/"published"])
  import re
  self.assertRegex(archive,r"<details\b");self.assertNotRegex(archive,r"<details\b[^>]*\bopen(?:\s|=|>)")
class Result(unittest.TextTestResult):
 def startTest(self,test):super().startTest(test);self.names.append(str(test))
 def __init__(self,*a,**k):super().__init__(*a,**k);self.names=[]
def main():
 global module
 OUT.mkdir(exist_ok=True)
 files=["live_analysis_panel.py","wave_cycle_dashboard_panel.py","build_manual_dashboard_copy.py"]
 before={n:digest(R/n) for n in files if (R/n).exists()}
 with contextlib.ExitStack() as stack:
  for obj,name in [(subprocess,"Popen"),(subprocess,"run"),(subprocess,"call"),(subprocess,"check_call"),(subprocess,"check_output")]:stack.enter_context(patch.object(obj,name,blocked))
  if hasattr(os,"startfile"):stack.enter_context(patch.object(os,"startfile",blocked))
  module=importlib.import_module("live_analysis_panel")
  with (OUT/"test_output.txt").open("w",encoding="utf8") as stream:
   result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(unittest.defaultTestLoader.loadTestsFromTestCase(LifecycleTests))
 after={n:digest(R/n) for n in before}
 report=dict(updated_at=datetime.datetime.now().astimezone().isoformat(),scope="Isolated temporary-state UI lifecycle and lineage contracts; external processes and os.startfile blocked. No HTTP actions or CFD.",tests_run=result.testsRun,failures=[dict(test=str(t),traceback=v) for t,v in result.failures],errors=[dict(test=str(t),traceback=v) for t,v in result.errors],passed=result.wasSuccessful() and before==after,source_sha256=before,sources_unchanged=before==after,test_names=result.names)
 save(OUT/"review.json",report);print(json.dumps({k:v for k,v in report.items() if k not in ("test_names","source_sha256","failures","errors")}));print("failures",len(result.failures),"errors",len(result.errors))
 if not result.wasSuccessful() or before!=after:raise SystemExit(1)
if __name__=="__main__":main()
