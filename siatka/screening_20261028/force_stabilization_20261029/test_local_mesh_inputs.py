"""Isolated mocked importer tests. No STAR or live registry/lock writes."""
import importlib.util,json,math,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
SPEC=importlib.util.spec_from_file_location("mesh_inputs_under_test",Path(__file__).with_name("local_mesh_inputs.py"))
mi=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(mi)
def native(cells=1200000):
 return dict(status="zero_flow_inspection_completed",flow_steps=0,initialized_or_cleared=False,
  physical_time_s=.123,physical_time_after_s=.123,cells=cells,
  quality=dict(NegativeVolumeCells=0,UnclosedCells=0,DegeneratedFeCells=0,min_cell_quality=.1,min_face_validity=1),
  boundaries=[],configuration_notes=[],profile=dict(dt_s=.0001,inner=10,order="SECOND_ORDER",continuum="water+air",vof_wave_model_available=True,calm_flat_reference_available=True,segregated_flow_vof_available=True,
   wave_active=False,current_m_s=[18,0,0],wind_m_s=[18,0,0],waterline_m=[0,0,2],vertical=[0,0,1],
   outlet_reversed_pressure="ENVIRONMENTAL",bottom_shear="SLIP",foil_shear="NO_SLIP",top_reversed_pressure="STATIC"))
def geometry(cells=1200000):
 return dict(passed=True,cells=cells,domain_x_m=[-35,45],domain_y_m=[.01,.03],domain_z_m=[-22,8],span_m=.02,
             mesh_fingerprint="geometry-hash",foil_geometry_fingerprint="foil-hash",foil_edges=1663)
class ImportTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix="ntnu_mesh_import_test_");self.root=Path(self.tmp.name)
  self.r=self.root/"R";self.w=self.root/"E";self.r.mkdir();self.w.mkdir()
  self.patches=[patch.object(mi,"R",self.r),patch.object(mi,"W",self.w),patch.object(mi,"D",self.r/"local_control"/"mesh_inputs")]
  for p in self.patches:p.start()
  self.source=self.root/"M11 prepared.sim";self.source.write_bytes(b"computed-case-test-only")
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.tmp.cleanup()
 def request(self):
  with patch.object(mi,"_spawn_inspection",return_value=types.SimpleNamespace(pid=1234)),patch.object(mi,"_alive",return_value=True):
   return mi.inspect_request(str(self.source))
 def ready_entry(self):
  value="a"*32;folder=self.w/("LOCAL_MESH_IMPORT_"+value);folder.mkdir()
  sim=folder/"input.sim";sim.write_bytes(b"original");mesh=folder/"mesh.CGNS";mesh.write_bytes(b"mesh")
  v=dict(id=value,status=mi.READY,ready=True,source_path=str(self.source),directory=str(folder),
   mesh_sim=str(sim),file_sha256=mi._digest(sim),mesh_cgns=str(mesh),mesh_cgns_sha256=mi._digest(mesh),
   mesh_fingerprint="geometry-hash",created_at="test",calm_accepted=False)
  mi._write(mi._entry_path(value),v);return v
 def test_module_import_no_registry_side_effects(self):
  self.assertFalse(mi.D.exists())
 def test_source_accepts_spaces_and_outer_quotes(self):
  self.assertEqual(mi._validate_source('"'+str(self.source)+'"'),self.source.resolve())
 def test_relative_path_rejected(self):
  with self.assertRaisesRegex(ValueError,"absolute"):mi.inspect_request("M11.sim")
 def test_non_sim_rejected(self):
  p=self.root/"mesh.CGNS";p.write_text("x")
  with self.assertRaisesRegex(ValueError,".sim"):mi.inspect_request(str(p))
 def test_missing_source_rejected(self):
  with self.assertRaisesRegex(ValueError,"does not exist"):mi.inspect_request(str(self.root/"missing.sim"))
 def test_empty_source_rejected(self):
  self.source.write_bytes(b"")
  with self.assertRaisesRegex(ValueError,"empty"):mi.inspect_request(str(self.source))
 def test_request_starts_only_mocked_cpu_inspection(self):
  q=self.request();self.assertEqual(q["pid"],1234);self.assertEqual(q["entry"]["flow_steps"],0)
  self.assertFalse(q["entry"]["calm_accepted"]);self.assertTrue(Path(q["entry"]["directory"]).is_dir())
 def test_repeated_active_path_returns_same_request(self):
  q=self.request()
  with patch.object(mi,"_alive",return_value=True),patch.object(mi,"_spawn_inspection",side_effect=AssertionError("duplicate")):
   again=mi.inspect_request(str(self.source))
  self.assertEqual(q["id"],again["id"])
 def test_selection_never_spawns(self):
  v=self.ready_entry()
  with patch.object(mi,"_spawn_inspection",side_effect=AssertionError("selection must not launch")):
   chosen=mi.set_selected(v["id"])
  self.assertFalse(chosen["selection_launches_calculation"]);self.assertEqual(mi.selected()["id"],v["id"])
 def test_changed_owned_sim_rejected(self):
  v=self.ready_entry();Path(v["mesh_sim"]).write_bytes(b"changed")
  with self.assertRaisesRegex(ValueError,"changed"):mi.set_selected(v["id"])
 def test_changed_cgns_rejected(self):
  v=self.ready_entry();Path(v["mesh_cgns"]).write_bytes(b"changed")
  with self.assertRaisesRegex(ValueError,"changed"):mi.set_selected(v["id"])
 def test_external_artifact_path_rejected_even_when_hash_matches(self):
  v=self.ready_entry();external=self.root/"foreign.sim";external.write_bytes(b"original")
  mi._update(v["id"],mesh_sim=str(external))
  with self.assertRaisesRegex(ValueError,"outside"):mi.set_selected(v["id"])
 def test_missing_calm_model_is_actionable(self):
  n=native();n["profile"]["calm_flat_reference_available"]=False
  self.assertEqual(mi._qualify(n,geometry())[0],"needs_configuration")
 def test_bc_changes_recorded_for_new_copy_without_rejecting_geometry(self):
  n=native();n["profile"].update(current_m_s=[10,0,0],bottom_shear="SYMMETRY",outlet_reversed_pressure="STATIC")
  self.assertTrue(mi._qualify(n,geometry())[1]);p=mi._settings_to_replace(n)
  self.assertEqual(p["differences"]["current_m_s"]["new_C01"],[18,0,0]);self.assertTrue(p["source_is_never_modified"])
 def test_unqualified_cannot_be_selected(self):
  v=self.ready_entry();mi._update(v["id"],status="needs_configuration",ready=False,reason="Fix timestep")
  with self.assertRaisesRegex(ValueError,"timestep"):mi.set_selected(v["id"])
 def test_identifier_path_traversal_rejected(self):
  with self.assertRaises(ValueError):mi.set_selected("../other")
 def test_supports_over_million_cells_and_non856_edges(self):
  status,ready,_=mi._qualify(native(),geometry())
  self.assertEqual(status,mi.READY);self.assertTrue(ready)
 def test_half_or_tenth_ms_read_without_changing_profile(self):
  n=native();n["profile"]["dt_s"]=.0005;self.assertTrue(mi._qualify(n,geometry())[1]);self.assertEqual(n["profile"]["dt_s"],.0005)
 def test_unsupported_timestep_actionable(self):
  n=native();n["profile"]["dt_s"]=.005;status,ready,why=mi._qualify(n,geometry())
  self.assertEqual(status,"needs_configuration");self.assertFalse(ready);self.assertIn("dt",why)
 def test_wrong_inner_rejected(self):
  n=native();n["profile"]["inner"]=20;self.assertFalse(mi._qualify(n,geometry())[1])
 def test_retained_wave_not_calm(self):
  n=native();n["profile"]["wave_active"]=True;status,ready,why=mi._qualify(n,geometry())
  self.assertEqual(status,mi.READY);self.assertTrue(ready)
  plan=mi._settings_to_replace(n);self.assertTrue(plan["retained_fields_not_accepted"]);self.assertFalse(plan["differences"]["wave_active"]["new_C01"])
 def test_missing_native_receipt_fails_closed(self):
  self.assertFalse(mi._qualify({},geometry())[1])
 def test_negative_volume_fails(self):
  n=native();n["quality"]["NegativeVolumeCells"]=1;self.assertEqual(mi._qualify(n,geometry())[0],"unsupported_geometry")
 def test_nonfinite_quality_fails(self):
  n=native();n["quality"]["min_face_validity"]=float("nan");self.assertFalse(mi._qualify(n,geometry())[1])
 def test_multispan_or_count_disagreement_fails(self):
  g=geometry();g["passed"]=False;g["errors"]=["Multiple span layers"];self.assertFalse(mi._qualify(native(),g)[1])
  self.assertFalse(mi._qualify(native(300),geometry(301))[1])
 def test_physical_time_cannot_advance(self):
  n=native();n["physical_time_after_s"]+=.001;self.assertFalse(mi._qualify(n,geometry())[1])
 def test_locks_are_exclusive_and_only_owned_are_released(self):
  value="b"*32
  with mi._locks(value):
   self.assertTrue((self.r/"queue.lock").exists());self.assertTrue((self.w/"preparation.lock").exists())
  self.assertFalse((self.r/"queue.lock").exists());self.assertFalse((self.w/"preparation.lock").exists())
  (self.w/"preparation.lock").write_text('{"pid":22}')
  with self.assertRaises(FileExistsError):
   with mi._locks(value):pass
  self.assertFalse((self.r/"queue.lock").exists());self.assertTrue((self.w/"preparation.lock").exists())
 def test_foreign_replacement_lock_is_preserved(self):
  with mi._locks("c"*32):(self.r/"queue.lock").write_text('{"owner_token":"someone-else"}')
  self.assertTrue((self.r/"queue.lock").exists())
 def test_public_status_does_not_launch_or_change_pause(self):
  (self.r/"local_control").mkdir();(self.r/"local_control"/"PAUSE").touch()
  with patch.object(mi,"_spawn_inspection",side_effect=AssertionError("status must not launch")):v=mi.public_status()
  self.assertTrue(v["flow_on_hold"]);self.assertTrue(v["zero_flow_inspection_allowed_during_flow_hold"])
 def test_dead_request_reported_interrupted_not_restarted(self):
  q=self.request()
  with patch.object(mi,"_alive",return_value=False):v=mi.list_entries()[0]
  self.assertEqual(v["status"],"interrupted");self.assertFalse(v["ready"])
 def test_mocked_full_import_preserves_source_and_records_nonsettled(self):
  q=self.request();value=q["id"];folder=Path(q["entry"]["directory"])
  (self.r/"InspectLocalMesh.java").write_text("zero-flow mock");before=self.source.read_bytes()
  fake=types.SimpleNamespace(free_memory=lambda:64*1024**3,redact=lambda s:s)
  def fake_star(out):
   mi._write(out/"inspection.json",native());(out/"mesh.CGNS").write_bytes(b"mock-export");(out/"inspected.sim").write_bytes(b"inspected");return 0
  def fake_audit(*args,**kwargs):
   mi._write(folder/"geometry_audit.json",geometry());return types.SimpleNamespace(returncode=0,stdout="mock",stderr="")
  with patch.dict(sys.modules,{"run_until_settled":fake}),patch.object(mi,"_check_receipt",return_value={}),patch.object(mi,"_block_reason",return_value=None),patch.object(mi,"_own_solver_pids",return_value=[]),patch.object(mi,"_run_star",side_effect=fake_star),patch.object(mi.subprocess,"run",side_effect=fake_audit):
   result=mi._inspect(value)
  self.assertTrue(result["ready"],result);self.assertEqual(self.source.read_bytes(),before)
  self.assertEqual(Path(result["mesh_sim"]).read_bytes(),before);self.assertEqual(result["cells"],1200000)
  self.assertFalse(result["calm_accepted"]);self.assertEqual(result["physical_time_s"],.123)
  self.assertFalse((self.r/"queue.lock").exists());self.assertFalse((self.w/"preparation.lock").exists())
 def test_completed_request_cannot_restart(self):
  v=self.ready_entry()
  with self.assertRaisesRegex(RuntimeError,"already used"):mi._inspect(v["id"])
if __name__=="__main__":unittest.main(verbosity=2)
