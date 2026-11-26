"""Isolated force-reference contract tests. No STAR and no live case writes."""
import importlib.util,copy,json,math,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location("tested_force_reference",Path(__file__).with_name("force_reference.py"))
fr=importlib.util.module_from_spec(spec);spec.loader.exec_module(fr)
def physics():
 return dict(native_getters_verified=True,rho_water_kg_m3=1000,rho_air_kg_m3=1.2,
 gravity_m_s2=[0,0,-9.81],lift_direction=[0,0,1],reference_density_kg_m3=1000,
 reference_speed_m_s=18,reference_area_m2=.0238,raw_reference_force_N=3855.6,
 pressure_reference_density_kg_m3=0,region_density_min_kg_m3=1.2,
 region_density_max_kg_m3=1000,foil_alpha_min=1,fully_submerged=True)
def ref():
 return dict(available=True,buoyancy_N=20,reference_force_N=4000,cl_offset=.005,provenance_file="TESTONLY")
class ForceReferenceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix="ntnu_force_reference_test_");self.root=Path(self.tmp.name)
  self.mesh=self.root/"mesh.CGNS";self.mesh.write_bytes(b"TEST ONLY mesh")
  self.audit=self.root/"initial_audit.json";fr._write(self.audit,dict(force_physics=physics()))
  self.case=self.root/"case";self.case.mkdir()
 def tearDown(self):self.tmp.cleanup()
 def build(self):
  geo=dict(verified=True,mesh_sha256=fr._hash(self.mesh),displaced_volume_m3=.0023)
  with patch.object(fr.subprocess,"run",return_value=types.SimpleNamespace(returncode=0,stdout=json.dumps(geo),stderr="")):
   return fr.build_manifest(self.case,self.mesh,self.audit,fr._hash(self.mesh))
 def test_native_physics_and_normalization(self):
  self.assertAlmostEqual(fr._physics(dict(force_physics=physics()))["reference_force_N"],3855.6)
 def test_native_density_differs_no_reinterpretation(self):
  p=physics();p["rho_water_kg_m3"]=1025
  with self.assertRaisesRegex(ValueError,"density"):fr._physics(p)
 def test_unverified_submergence_rejected(self):
  p=physics();p["foil_alpha_min"]=.9
  with self.assertRaisesRegex(ValueError,"immersion"):fr._physics(p)
 def test_nonvertical_gravity_rejected(self):
  p=physics();p["gravity_m_s2"]=[1,0,-9.81]
  with self.assertRaisesRegex(ValueError,"gravity"):fr._physics(p)
 def test_pressure_reference_density_requires_review(self):
  p=physics();p["pressure_reference_density_kg_m3"]=1000
  with self.assertRaisesRegex(ValueError,"reference density"):fr._physics(p)
 def test_missing_native_audit_not_guessed(self):
  with self.assertRaisesRegex(ValueError,"verified"):fr._physics({})
 def test_raw_normalization_mismatch_rejected(self):
  p=physics();p["reference_speed_m_s"]=20
  with self.assertRaisesRegex(ValueError,"3855.6"):fr._physics(p)
 def test_corrected_force_keeps_raw_and_input(self):
  row=dict(Fz_N=400,CL_total=.1,CD=.01);old=copy.deepcopy(row);v=fr.correct_row(row,ref())
  self.assertEqual(row,old);self.assertEqual(v["CL_total"],.1);self.assertEqual(v["rawCL_total"],.1)
  self.assertAlmostEqual(v["CL"],.095);self.assertEqual(v["CD"],.01)
 def test_coefficient_only_fallback(self):
  self.assertAlmostEqual(fr.correct_row(dict(CL_total=.1),ref())["CL"],.095)
 def test_corrected_row_idempotent(self):
  r=fr.correct_row(dict(CL_total=.1),ref());self.assertEqual(fr.correct_row(r,ref())["CL"],r["CL"])
 def test_nearzero_and_negative_lift_allowed(self):
  self.assertEqual(fr.correct_row(dict(CL_total=0),ref())["CL"],-.005)
 def test_native_slice_force_is_checked_against_raw(self):
  v=fr.correct_row(dict(Fz_slice_N=400,CL_total=.1),ref());self.assertAlmostEqual(v["CL"],.095)
  self.assertIsNone(fr.correct_row(dict(Fz_slice_N=400,CL_total=.2),ref())["CL"])
 def test_nonfinite_raw_not_hidden_by_valid_force(self):
  self.assertIsNone(fr.correct_row(dict(Fz_slice_N=400,CL_total=float("nan")),ref())["CL"])
 def test_source_mesh_wrong_file_rejected(self):
  v=self.build();other=self.root/"other.CGNS";other.write_bytes(b"OTHER")
  self.assertFalse(fr.reference_for_source(dict(v,mesh=str(other)))["available"])
  self.assertTrue(fr.reference_for_source(dict(v,mesh=str(self.mesh)))["available"])
 def test_force_and_raw_coefficient_disagree(self):
  self.assertIsNone(fr.correct_row(dict(CL_total=.2,Fz_N=400),ref())["CL"])
 def test_unavailable_no_raw_substitution(self):
  r=fr.correct_row(dict(CL_total=.2),dict(available=False));self.assertIsNone(r["CL"]);self.assertEqual(r["rawCL_total"],.2)
 def test_nonfinite_ref_or_row(self):
  r=ref();r["buoyancy_N"]=float("nan");self.assertIsNone(fr.correct_row(dict(CL_total=.2),r)["CL"])
  self.assertIsNone(fr.correct_row(dict(CL_total=float("nan")),ref())["CL"])
 def test_wrong_offset_rejected(self):
  r=ref();r["cl_offset"]=.006;self.assertIsNone(fr.correct_row(dict(CL_total=.1),r)["CL"])
 def test_build_manifest_file_only_mocked_and_hash_bound(self):
  v=self.build();self.assertTrue(v["available"]);self.assertAlmostEqual(v["buoyancy_N"],22.563)
  self.assertEqual(v["mesh_sha256"],fr._hash(self.mesh));self.assertTrue(Path(v["force_reference_file"]).is_file())
 def test_existing_manifest_never_overwritten(self):
  v=self.build();h=fr._hash(v["force_reference_file"]);again=self.build();self.assertTrue(again["available"])
  self.assertEqual(h,fr._hash(v["force_reference_file"]))
 def test_source_manifest_validation(self):
  v=self.build();source={k:v[k] for k in ("force_reference_file","force_reference_sha256")}
  self.assertTrue(fr.reference_for_source(source)["available"])
  source["force_reference_sha256"]="0"*64;self.assertFalse(fr.reference_for_source(source)["available"])
 def test_changed_bound_mesh_rejected(self):
  v=self.build();self.mesh.write_bytes(b"CHANGED");self.assertFalse(fr.reference_for_source(v)["available"])
 def test_changed_native_audit_rejected(self):
  v=self.build();self.audit.write_text("{}");self.assertFalse(fr.reference_for_source(v)["available"])
 def test_case_copy_requires_identity_binding(self):
  v=self.build();other=self.root/"flowcase";other.mkdir()
  (other/"force_reference.json").write_bytes(Path(v["force_reference_file"]).read_bytes())
  self.assertFalse(fr.correction_for_case(other)["available"])
  fr._write(other/"source_identity.json",dict(force_reference_sha256=v["force_reference_sha256"],force_reference_file=v["force_reference_file"]))
  self.assertTrue(fr.correction_for_case(other)["available"])
 def test_unknown_manual_mesh_unavailable(self):
  with patch.object(fr,"REVIEW",self.root/"absent.json"):self.assertFalse(fr.correction_for_case(self.case)["available"])
 def test_geometry_hash_mismatch_prevents_spawn(self):
  with patch.object(fr.subprocess,"run",side_effect=AssertionError("must not spawn")):
   self.assertFalse(fr.build_manifest(self.case,self.mesh,self.audit,"0"*64)["available"])
 def test_original_selected_vs_extended_mesh_hash_distinguished(self):
  v=self.build();self.assertTrue(fr.reference_for_source(v,dict(mesh_cgns_sha256="original-selected-domain"))["available"])
  self.assertFalse(fr.reference_for_source(v,dict(force_reference_mesh_sha256="wrong"))["available"])
if __name__=="__main__":unittest.main(verbosity=2)
